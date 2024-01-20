"""
Represents a YouTube source. When the function is invoked, it hashes
the lowest quality video stream.
"""

import hashlib
import logging
from io import BytesIO
from typing import Optional

from pytube import YouTube  # type: ignore


class YoutubeSource:
    """
    Represents a YouTube source.
    """
    def __init__(self, url: str) -> None:
        self.url = url
        self.hash: Optional[str] = None

    @staticmethod
    def __calculate_hash(stream: BytesIO) -> str:
        sha = hashlib.sha256()
        for chunk in iter(lambda: stream.read(4096), b''):
            sha.update(chunk)
        return sha.hexdigest()

    def get(self) -> Optional[str]:
        """
        Downloads the lowest quality Youtube video, and obtains a hash
        """
        if self.hash:
            return self.hash

        try:
            logging.info("Retrieving lowest quality resolution for %s",
                         self.url)
            stream = BytesIO()
            yt = YouTube(self.url)
            yt.streams.get_lowest_resolution().stream_to_buffer(stream)
            stream.seek(0)
            self.hash = self.__calculate_hash(stream)
            return self.hash
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video for %s", self.url)
            return None
