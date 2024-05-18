"""
Interface declaring the ARG state
"""

from dataclasses import dataclass
from dataclasses_json import dataclass_json, DataClassJsonMixin
from metadata.youtube_metadata import VideoInformation
from metadata.soundcloud_metadata import SoundCloudUserInformation
from metadata.ytc_metadata import ChannelInformation


@dataclass_json
@dataclass
class ArgState(DataClassJsonMixin):
    """
    The serializable ARG state. If the hash of this changes from the
    cache, it means _something_ has changed.

    (Note: I'm individually defining the fields so that in the event
    something changed, we can just print the key that is different)

    (Also note: The mixin is for my LSP to remain happy)
    """
    numbers_1_video_info: VideoInformation
    numbers_1_video_hash: str
    study_video_info: VideoInformation
    study_video_hash: str
    numbers_2_video_info: VideoInformation
    numbers_2_video_hash: str
    psv_video_info: VideoInformation
    psv_video_hash: str
    filtered_video_info: VideoInformation
    filtered_video_hash: str
    hello_world_video_info: VideoInformation
    hello_world_video_hash: str
    meaning_of_life_video_info: VideoInformation
    meaning_of_life_video_hash: str
    soundcloud_user_info: SoundCloudUserInformation

    youtube_feed_hash: str
    soundcloud_feed_hash: str

    neuro_twitch_identifiers: str
    evil_twitch_identifiers: str

    youtube_channel_info: ChannelInformation
