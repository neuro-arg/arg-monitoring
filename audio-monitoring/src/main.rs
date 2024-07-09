use log::{info, warn};
use pleep_audio::ConvertingAudioIterator;
use pleep_build::{cli::SpectrogramSettings, file::File, generate_log_spectrogram};
use std::{collections::HashMap, io};
use symphonia::core::io::{MediaSourceStream, MediaSourceStreamOptions, ReadOnlySource};
use tokio::sync::mpsc::channel;

// NOTE: amazing hard coded constants
const LOOKUP_FILE: &str = "out.bin";
const DEFAULT_MAX_DISTANCE: f32 = 0.95;
const N_RESULTS: usize = 2;

fn ctrl_c_handler(best_matches: &Vec<(usize, f32)>, file: &File) {
    let mut out_counter = HashMap::new();

    for (best_index, value) in best_matches {
        if !out_counter.contains_key(&best_index) {
            out_counter.insert(best_index, 0.0);
        }

        let hm_value = out_counter.get_mut(&best_index).unwrap();

        *hm_value += (DEFAULT_MAX_DISTANCE - value).max(0.0);
    }

    let mut best = out_counter.into_iter().collect::<Vec<_>>();

    best.sort_by(|(_, left), (_, right)| {
        left.partial_cmp(right)
            .unwrap_or(std::cmp::Ordering::Greater)
    });
    best.reverse();

    let mut output = CommandOutput {
        matches: Vec::with_capacity(N_RESULTS),
    };

    let best = best.iter().take(N_RESULTS).collect::<Vec<_>>();
    let softmaxed = scale_results(&best.iter().map(|(_, v)| *v).collect::<Vec<_>>());

    for (index, ((song_index, score), scaled_prob)) in
        best.into_iter().zip(softmaxed.into_iter()).enumerate()
    {
        let title = &file.segments[**song_index].title;
        output.matches.push(Match {
            title: title.to_owned(),
            score: *score,
            scaled_prob,
        });
        info!(
            "{: >4}: {} [score={score}] [scaled_prob={scaled_prob}]",
            index + 1,
            title,
        );
    }

    let json = serde_json::to_string(
        &output
            .matches
            .iter()
            .map(|item| MatchLessInfo::from(item))
            .collect::<Vec<_>>(),
    )
    .unwrap();
    print!("{json}");
}

#[tokio::main]
async fn main() {
    env_logger::init();

    let (tx, mut rx) = channel(1);

    tokio::spawn(async move {
        let _ = tokio::signal::ctrl_c().await;
        let _ = tx.send(());
        info!("Received kill, please be patient");
    });

    let media_source = ReadOnlySource::new(io::stdin());
    let media_source_stream =
        MediaSourceStream::new(Box::new(media_source), MediaSourceStreamOptions::default());

    let mut reader = std::io::BufReader::new(std::fs::File::open(LOOKUP_FILE).unwrap());
    let file = pleep_build::file::File::read_from(&mut reader).unwrap();

    let audio_source = pleep_audio::AudioSource::new(media_source_stream);
    let audio = ConvertingAudioIterator::new(audio_source).expect("can load audio source");

    let resampled = pleep_audio::ResamplingChunksIterator::new_from_audio_iterator(
        audio,
        pleep_audio::ResampleSettings {
            target_sample_rate: file.build_settings.resample_rate as usize,
            sub_chunks: 1,
            chunk_size: 2 << 14,
        },
    )
    .expect("creates a resampler")
    .flatten();

    let log_spectrogram = generate_log_spectrogram(
        resampled,
        &SpectrogramSettings {
            fft_size: file.build_settings.fft_size as usize,
            fft_overlap: file.build_settings.fft_overlap as usize,
        }
        .into(),
        &pleep_build::LogSpectrogramSettings {
            height: file.build_settings.spectrogram_height as usize,
            frequency_cutoff: file.build_settings.spectrogram_max_frequency as usize,
            input_sample_rate: file.build_settings.resample_rate as usize,
        },
    );

    let mut best_matches = Vec::new();

    for sample in log_spectrogram {
        // TODO: not sure if I even need a channel here to be honest, but yolo for now
        // also i will not hear any complains about this being omega scuffed
        if let Err(tokio::sync::mpsc::error::TryRecvError::Empty) = rx.try_recv() {
            // intentional no-op
        } else {
            info!("now handling sigkill, please remain patient");
            ctrl_c_handler(&best_matches, &file);
            break;
        };

        let mut segment_matches = Vec::with_capacity(file.segments.len());

        for (segment_index, segment) in file.segments.iter().enumerate() {
            let closest = segment
                .vectors
                .iter()
                .map(|vector| 1.0 - distance_cosine(&sample, vector))
                .min_by(|l, r| l.partial_cmp(r).unwrap_or(std::cmp::Ordering::Greater))
                .unwrap_or(f32::INFINITY);

            segment_matches.push((segment_index, closest));
        }

        best_matches.push(
            segment_matches
                .into_iter()
                .min_by(|(_, left), (_, right)| {
                    left.partial_cmp(right)
                        .unwrap_or(std::cmp::Ordering::Greater)
                })
                .unwrap(),
        )
    }

    unreachable!("this program should never be able to quit gracefully");
    // ctrl_c_handler(&best_matches, &file);
}

#[derive(Debug, Clone, serde::Serialize)]
struct CommandOutput {
    matches: Vec<Match>,
}

#[derive(Debug, Clone, serde::Serialize)]
struct Match {
    title: String,
    score: f32,
    scaled_prob: f32,
}

#[derive(Debug, Clone, serde::Serialize)]
struct MatchLessInfo {
    title: String,
    score: f32,
}

impl From<&Match> for MatchLessInfo {
    fn from(value: &Match) -> Self {
        MatchLessInfo {
            title: value
                .title
                .rsplit(r"/")
                .next()
                .expect("did bred change something")
                .to_owned(),
            score: value.score,
        }
    }
}

fn scale_results(values: &[f32]) -> Vec<f32> {
    let sum: f32 = values.into_iter().sum();

    values.into_iter().map(|v| *v / sum).collect()
}

fn distance_sq(l1: &[f32], l2: &[f32]) -> f32 {
    l1.into_iter().zip(l2).map(|(l, r)| (l - r).powi(2)).sum()
}

fn distance_cosine(l1: &[f32], l2: &[f32]) -> f32 {
    let numer: f32 = l1.into_iter().zip(l2.into_iter()).map(|(l, r)| l * r).sum();
    let mag = distance_sq(l1, l2);

    numer / mag.sqrt()
}
