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

    @staticmethod
    def __bug_workaround_get_description(yt: YouTube) -> str:
        """
        Problem with pytube. This should get the description properly
        https://github.com/pytube/pytube/issues/1626
        """
        for n in range(6):
            try:
                description = yt.initial_data["engagementPanels"][n]["engagementPanelSectionListRenderer"]["content"]["structuredDescriptionContentRenderer"]["items"][1]["expandableVideoDescriptionBodyRenderer"]["attributedDescriptionBodyText"]["content"]  # pylint: disable=line-too-long # noqa: E501
                return description
            except:  # pylint: disable=bare-except # noqa: E722
                continue
        return yt.description

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
                self.__bug_workaround_get_description(yt),
                download_encode_and_hash(yt.thumbnail_url),
                yt.keywords)
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video information for %s",
                              self.url)
            return None
