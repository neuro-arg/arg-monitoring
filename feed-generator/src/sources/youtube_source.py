"""
Represents a YouTube source. When the function is invoked, it hashes
the lowest quality video stream.
"""

import hashlib
import logging
from io import BytesIO
from typing import Optional

from utils import check_proxy_variables
from contextlib import redirect_stdout
from youtube_dl import YoutubeDL # type: ignore


class YoutubeSource:
    """
    Represents a YouTube source.
    """
    def __init__(self, url: str) -> None:
        self.url = url
        self.hash: Optional[str] = None
        self.options = {
            'proxy': check_proxy_variables()
        }

    @staticmethod
    def __calculate_hash(stream: BytesIO) -> str:
        sha = hashlib.sha256()
        for chunk in iter(lambda: stream.read(4096), b''):
            sha.update(chunk)
        return sha.hexdigest()

    @staticmethod
    def __get_lowest_video_data(video_id: str, options: dict) -> BytesIO:
        buffer = BytesIO()
        ctx = {
            'outtmpl': "-",
            'logtostderr': True,
            'format': 'worst',
            'ratelimit': '70K',
            **options
        }
        with redirect_stdout(buffer), YoutubeDL(ctx) as ytdl:  # type: ignore
            ytdl.download([video_id])

        buffer.seek(0)
        return buffer

    def get(self) -> Optional[str]:
        """
        Downloads the lowest quality Youtube video, and obtains a hash
        """
        if self.hash:
            return self.hash

        try:
            logging.info("Retrieving lowest quality resolution for %s",
                         self.url)
            stream = self.__get_lowest_video_data(self.url, self.options)
            self.hash = self.__calculate_hash(stream)
            return self.hash
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video for %s", self.url)
            return None
