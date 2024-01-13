"""
Pulls metadata from YouTube.

All images will be encoded into base64
"""

import base64
import logging
from dataclasses import dataclass
from typing import Optional
from utils import download_encode_and_hash

import requests
from dataclasses_json import dataclass_json
from pytube import YouTube  # type: ignore


@dataclass_json
@dataclass
class VideoInformation:
    """
    Represents the information of a YouTube video
    """
    title: str
    length: int
    description: str
    thumbnail: str
    keywords: list[str]


class VideoInformationGetter:
    """
    Gets video information from YouTube
    """
    def __init__(self, url: str) -> None:
        self.url = url
        self.solution: Optional[VideoInformation] = None

    def get(self) -> Optional[VideoInformation]:
        """
        Returns a VideoInformation object if the video exists,
        otherwise returns None

        This returning None should immediately ring alarm bells
        """
        if self.solution:
            return self.solution

        try:
            logging.info("Getting video information for %s", self.url)
            yt = YouTube(self.url)
            self.solution = VideoInformation(
                yt.title,
                yt.length,
                yt.description,
                download_encode_and_hash(yt.thumbnail_url),
                yt.keywords)
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video information for %s",
                              self.url)
            return None
