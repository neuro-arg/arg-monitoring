use serde::{Serialize, Deserialize};
use std::collections::HashMap;

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
struct VideoInformation {
    title: Option<String>,
    length: Option<u64>,
    description: Option<String>,
    thumbnail: Option<String>,
    keywords: Option<Vec<String>>,
    subtitles: Option<String>,
}

#[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
struct SoundCloudUserInformation {
    full_name: Option<String>,
    banner: Option<String>,
    n_tracks: Option<u64>,
    n_following: Option<u64>,
    n_visuals: Option<u64>,
}

macro_rules! structure_reflection {
    ($(#[$($attr:meta),*]),*
     struct $name:ident { $($fname:ident : $ftype:ty),* }) => {
        $(#[$($attr),*]),* pub struct $name {
            $($fname : $ftype),*
        }

        pub fn get_match_tuples<'a>(
            lhs: &'a $name, rhs: &'a $name
        ) -> HashMap<String, bool> {
            HashMap::from([$((stringify!($fname).to_string(), lhs.$fname == rhs.$fname)),*])
        }
    };
}

structure_reflection! {
    #[derive(Serialize, Deserialize, Debug, PartialEq, Eq)]
    struct ArgState {
        numbers_1_video_info: Option<VideoInformation>,
        numbers_1_video_hash: Option<String>,
        study_video_info: Option<VideoInformation>,
        study_video_hash: Option<String>,
        numbers_2_video_info: Option<VideoInformation>,
        numbers_2_video_hash: Option<String>,
        psv_video_info: Option<VideoInformation>,
        psv_video_hash: Option<String>,
        filtered_video_info: Option<VideoInformation>,
        filtered_video_hash: Option<String>,
        hello_world_video_info: Option<VideoInformation>,
        hello_world_video_hash: Option<String>,
        meaning_of_life_video_info: Option<VideoInformation>,
        meaning_of_life_video_hash: Option<String>,
        soundcloud_user_info: Option<SoundCloudUserInformation>,

        youtube_feed_hash: Option<String>,
        soundcloud_feed_hash: Option<String>
    }
}
