#![feature(iter_array_chunks)]
use log::info;
use pleep_audio::ConvertingAudioIterator;
use pleep_build::{cli::SpectrogramSettings, generate_log_spectrogram};
use serde::Deserialize;
use std::{
    collections::HashMap, env, fs::File, io::{Read, Write}, process::{ChildStdout, Command, Stdio}, sync::{atomic::{AtomicPtr, AtomicUsize}, Arc}
};
use symphonia::core::io::{MediaSourceStream, MediaSourceStreamOptions, ReadOnlySource};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt, Empty},
    runtime::Handle,
    sync::broadcast::{channel, Receiver},
    task::{block_in_place, spawn_blocking},
};

// NOTE: amazing hard coded constants
const LOOKUP_FILE: &str = "out.bin";
const DEFAULT_MAX_DISTANCE: f32 = 0.95;
const N_RESULTS: usize = 2;
const SAMPLE_RATE: usize = 44100; // useful to determine time passed
const CHUNKING_NUMBER: usize = 4410; // ideally chunking number should be a perfect multiple of SAMPLE_RATE
const AUDIO_CHANNELS: usize = 2;
const SIZE_OF_SAMPLE: usize = 2; // 2 bytes per sample, because we are fixing it to s16le
const AUDIO_THRESHOLD: f32 = 0.99;

pub fn panic_if_no_streamlink() {
    match Command::new("streamlink").arg("--version").output() {
        Ok(_) => {
            info!("Found streamlink, continuing...")
        }
        Err(_) => {
            panic!("Streamlink not found. Please install streamlink with pip install streamlink")
        }
    }
}

async fn process_stdout(stdout: &mut tokio::process::ChildStdout) -> Option<Vec<u8>> {
    let mut output = Vec::new();
    // let mut buffer = [0; CHUNKING_NUMBER];

    let res = stdout.read_to_end(&mut output).await;
    Some(output)

    // if let Err(_) = stdout.read(&mut buffer).await {
    //     None
    // } else {
    //     println!("huge huh moment");
    //     output.extend(buffer);
    //     Some(output)
    // }
}

struct CountingReadWrapper<R: Read> {
    inner: R,
    count: Arc<AtomicUsize>,
}

impl<R: Read> CountingReadWrapper<R> {
    fn new(inner: R) -> Self {
        Self {
            inner,
            count: Arc::new(AtomicUsize::new(0)),
        }
    }
}

impl<R: Read> Read for CountingReadWrapper<R> {
    fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize> {
        let value = self.count.load(std::sync::atomic::Ordering::Relaxed);
        let result = self.inner.read(buf);

        if let Ok(bytes_read) = result {
            self.count
                .store(value + bytes_read, std::sync::atomic::Ordering::Relaxed);
        }
        result
    }
}

#[tokio::main]
async fn main() {
    env_logger::init();

    panic_if_no_streamlink();

    // streamlink
    let mut streamlink_partial = Command::new("streamlink");
    streamlink_partial.arg(format!("https://twitch.tv/vedal987"));

    if let Ok(val) = env::var("TWITCH_OAUTH") {
        streamlink_partial.arg(format!("--twitch-api-header=Authorization=OAuth {val}"));
    }

    // .arg(format!("https://twitch.tv/video/2194199626"))
    // .arg(format!("https://twitch.tv/video/2190838273"))
    let streamlink = streamlink_partial
        .arg("best")
        .arg("--twitch-disable-ads")
        .arg("--twitch-low-latency")
        // .arg("--hls-start-offset")
        // .arg("06:30")
        .arg("-Q")
        .arg("-O")
        .stdout(Stdio::piped())
        .spawn()
        .expect("can launch streamlink");

    // let mut streamlink = Command::new("ffmpeg")
    //     .arg("-i")
    //     .arg("output_replaced.mp4")
    //     .arg("-c:v")
    //     .arg("copy")
    //     .arg("-c:a")
    //     .arg("copy")
    //     .arg("-f")
    //     .arg("mpegts")
    //     .arg("-")
    //     .stdout(Stdio::piped())
    //     .spawn()
    //     .expect("can launch ffmpeg");

    // ffmpeg (audio)
    let mut ffmpeg = Command::new("ffmpeg")
        .arg("-hide_banner")
        .arg("-loglevel")
        .arg("quiet")
        .arg("-i")
        .arg("-")
        .arg("-ac")
        .arg(format!("{AUDIO_CHANNELS}"))
        .arg("-ar")
        .arg(format!("{SAMPLE_RATE}"))
        .arg("-f")
        .arg("s16le")
        .arg("-f")
        .arg("wav")
        .arg("-")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("can launch ffmpeg");

    // ffmpeg (video -> python -> ...) <--
    let mut video = Command::new("python3")
        .arg("vedal987_scrutinize.py")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .expect("can launch python");

    let mut ffmpeg_stdin = ffmpeg.stdin.unwrap();
    let mut ffmpeg_stdout = ffmpeg.stdout.unwrap();
    let mut video_stdout = video.stdout.unwrap();
    let mut video_stdin = video.stdin.unwrap();

    let (tx, rx) = channel(1);
    let mut surely_stoppable_rx = rx.resubscribe();

    // threading to send streamlink to both processes
    let surely_stoppable = tokio::spawn(async move {
        let chunk_iter = streamlink
            .stdout
            .unwrap()
            .bytes()
            .filter_map(|b| b.ok())
            .array_chunks::<CHUNKING_NUMBER>();

        for chunk in chunk_iter {
            let _ = ffmpeg_stdin.write(&chunk);
            let _ = video_stdin.write(&chunk);
            if let Ok(_) = surely_stoppable_rx.try_recv() {
                break;
            }
        }
    });

    let audio_handler = async move {
        let countable_stdout = CountingReadWrapper::new(ffmpeg_stdout);
        process_audio_with_stdout(countable_stdout, rx).await
    };

    let scrutinize_handler = async move {
        let result = spawn_blocking(move || {
            let mut buf = String::new();
            let _ = video_stdout.read_to_string(&mut buf);
            let _ = tx.send(());
            buf
        })
        .await;
        result.unwrap()
    };

    let (scrutinize_result_raw, audio_result, _) = tokio::join!(scrutinize_handler, audio_handler, surely_stoppable);
    let scrutinize_result: Vec<ScrutinizeResult> = serde_json::de::from_str(&scrutinize_result_raw).unwrap();
    scrutinize_result.iter().for_each(|result| {
        let filename = format!("{}.txt", result.streamer);
        let content = format!("{}\n{}", result.result, audio_result);
        let mut file = File::create(filename).unwrap();
        let _ = file.write_all(content.as_bytes());
    });
}

async fn process_audio_with_stdout(
    readable: CountingReadWrapper<ChildStdout>,
    mut kill_signal: Receiver<()>,
) -> String {
    let atomic_count = readable.count.clone();
    let media_source = ReadOnlySource::new(readable);
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
        );

        if let Ok(_) = kill_signal.try_recv() {
            break;
        }
    }

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
        let title = &file.segments[*song_index].title;
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

    let total: f32 = output.matches.iter().map(|item| item.scaled_prob).sum();
    let time = atomic_count.load(std::sync::atomic::Ordering::Relaxed) as f64
        / (SAMPLE_RATE * AUDIO_CHANNELS * SIZE_OF_SAMPLE) as f64;
    // let avg_score = total as f64 / time;
    let threshold_passed = total >= AUDIO_THRESHOLD;

    info!("Time: {}", time);
    info!("Total Probability: {}", total);
    // info!("Avg Score: {}", avg_score);

    // serde_json::to_string(
    //     &output
    //         .matches
    //         .iter()
    //         .map(|item| MatchLessInfo::from(item))
    //         .collect::<Vec<_>>(),
    // )
    // .unwrap()
    format!("{threshold_passed}")
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

#[derive(Debug, serde::Deserialize)]
struct ScrutinizeResult {
    streamer: String,
    result: String
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

fn magnitude_sq(l1: &[f32]) -> f32 {
    l1.iter().map(|v| v.powi(2)).sum()
}

fn distance_cosine(l1: &[f32], l2: &[f32]) -> f32 {
    let numer: f32 = l1.iter().zip(l2).map(|(l, r)| l * r).sum();
    let denom = magnitude_sq(l1) * magnitude_sq(l2);

    let result = numer / denom.sqrt();

    result.is_finite().then_some(result).unwrap_or(-1.0)
}
