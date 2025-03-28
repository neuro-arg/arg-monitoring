"""
Driver script for all verifications
"""

import datetime
import json
import logging
import os
import pickle
import time
from typing import Any, Callable, Optional
from uuid import uuid4

from feedgen.feed import FeedGenerator

from arg_state import ArgState
from metadata.feeds import FeedGetter
from metadata.soundcloud_metadata import (SoundCloudUserGetter,
                                          SoundCloudUserInformation)
from metadata.youtube_metadata import VideoInformation, VideoInformationGetter
from metadata.ytc_metadata import ChannelInformation, ChannelInformationGetter
from sources.twitch_source import TwitchSource
from sources.youtube_source import YoutubeSource

logging.basicConfig(
    level=logging.INFO,
    format="[%(filename)s:%(lineno)s - %(funcName)s()] %(message)s")

RETRY_NO = 5
RETRY_INTERVAL = 30
DELAY_INTERVAL = 5

NUMBERS_1_URL = "https://www.youtube.com/watch?v=wc-QCoMm4J8"
NUMBERS_2_URL = "https://www.youtube.com/watch?v=giJI-TDbO5k"
STUDY_URL = "https://www.youtube.com/watch?v=zMlH7RH6psw"
PSV_URL = "https://www.youtube.com/watch?v=ymYFqNUt05g"
FILTERED_URL = "https://www.youtube.com/watch?v=4j5oDzRiXUA"
HELLO_WORLD_URL = "https://www.youtube.com/watch?v=OiKrYrbs3Qs"
MEANING_OF_LIFE_URL = "https://www.youtube.com/watch?v=IRzyqcKljxw"
CANDLES_URL = "https://www.youtube.com/watch?v=x4l5ckrtbAc"
NUMBERS_3_URL = "https://www.youtube.com/watch?v=aX4v5XUQtnw"
SOUNDCLOUD_URL = "https://soundcloud.com/572943"

YOUTUBE_FEED_URL = \
    "https://www.youtube.com/feeds/videos.xml?channel_id=UCqOK_pl0LS0e8Lp7HMRDZsw"
SOUNDCLOUD_FEED_URL = "https://feeds.soundcloud.com/users/soundcloud:users:1258077262/sounds.rss"

YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@_neurosama"


def get_video_info_and_content(url) -> tuple[VideoInformation, str]:
    """
    Gets video information and content
    """
    info = while_none_retry_max(VideoInformationGetter(url).get)
    source = while_none_retry_max(YoutubeSource(url).get)
    time.sleep(DELAY_INTERVAL)

    return info, source


def while_none_retry_max(fn: Callable[[], Any | None]) -> Any:
    """
    While x is None, retries for a maximum of retry_no.

    Args:
        fn: The function to call

    Returns:
        The value of x
    """

    for i in range(RETRY_NO):
        x = fn()
        if x is not None:
            return x

        logging.info("Operation failed, retrying %d/%d", (i + 1), RETRY_NO)
        time.sleep(RETRY_INTERVAL)

    raise RuntimeError("Operation failed after all retires")


youtube_feed_getter = FeedGetter(
    YOUTUBE_FEED_URL,
    ['{http://search.yahoo.com/mrss/}community'])

soundcloud_feed_getter = FeedGetter(
    SOUNDCLOUD_FEED_URL, []
)

current_state = ArgState(
    *get_video_info_and_content(NUMBERS_1_URL),
    *get_video_info_and_content(STUDY_URL),
    *get_video_info_and_content(NUMBERS_2_URL),
    *get_video_info_and_content(PSV_URL),
    *get_video_info_and_content(FILTERED_URL),
    *get_video_info_and_content(HELLO_WORLD_URL),
    *get_video_info_and_content(MEANING_OF_LIFE_URL),
    *get_video_info_and_content(CANDLES_URL),
    *get_video_info_and_content(NUMBERS_3_URL),
    while_none_retry_max(SoundCloudUserGetter(SOUNDCLOUD_URL).get),
    while_none_retry_max(youtube_feed_getter.get),
    while_none_retry_max(soundcloud_feed_getter.get),
    while_none_retry_max(TwitchSource('neuro').get),
    while_none_retry_max(TwitchSource('evil').get),
    while_none_retry_max(ChannelInformationGetter(YOUTUBE_CHANNEL_URL).get),
)

cached_state: Optional[ArgState] = None

feed_log: list[str] = []

if not os.path.exists('cache.json'):
    with open('cache.json', 'w', encoding='ascii') as f:
        f.write(current_state.to_json())
        cached_state = current_state
        feed_log.append('Initial. Cached is same as current')
else:
    with open('cache.json', 'r', encoding='ascii') as f:
        cached_state = ArgState.from_json(f.read(), infer_missing=True)
        for (u, v) in zip(current_state.to_dict().items(),
                          cached_state.to_dict().items()):
            # compare string-wise to bypass any reference comparison
            if u[1] != v[1]:
                logging.error("Value %s does not match", u[1])
                logging.error("Current: %s", u)
                logging.error("Expected: %s", v)
                feed_log.append(f'Key {u[0]} does not match')

    with open('cache.json', 'w', encoding='ascii') as f:
        f.write(current_state.to_json())

# only update the atom feed if there are any changes
# still create the atom.xml file though, so we don't break workflow
if not os.path.exists('atom.pickle'):
    fg = FeedGenerator()

    fg.id('ARG feed')
    fg.title('ARG feed')
    fg.author({'name': 'clueless author'})
else:
    with open('atom.pickle', 'rb') as f:  # type: ignore
        fg = pickle.load(f)  # type: ignore

if len(feed_log) > 0:
    fe = fg.add_entry()
    fe.id(str(uuid4()))
    fe.title('ARG feed update - Difference Detected')
    fe.content(
        f'{str(feed_log)}\n'
        f'Full JSON:\n{current_state.to_json()}\n\n'
        f'Cached JSON:\n{cached_state.to_json()}')

fg.atom_file('atom.xml')

with open('atom.pickle', 'wb') as f:  # type: ignore
    pickle.dump(fg, f)  # type: ignore

youtube_feed_getter.save('youtubefeed.xml')
soundcloud_feed_getter.save('soundcloudfeed.xml')
