"""
Pulls metadata from YouTube.

All images will be encoded into base64
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

import youtube_dl  # type: ignore
from dataclasses_json import dataclass_json
from pytube import YouTube  # type: ignore
from utils import download_encode_and_hash


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
    subtitles: Optional[str]


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

    @staticmethod
    def __read_file_then_delete(filename: str) -> str:
        assert os.path.exists(filename)
        contents = ''
        with open(filename, 'r', encoding='utf-8') as f:
            contents = f.read()
        os.remove(filename)
        return contents

    def __get_subtitles(self) -> str:
        """
        Gets the subtitles via youtube_dl. Because of how youtube_dl
        works, we can't stream it directly to an in-memory
        object. Instead, we'll download the file, read from it, and
        delete it from existence

        NOTE: From experimenting, if the video has real subtitles,
        then that will be prioiritized over automatically generated
        ones
        """
        file_uuid = str(uuid4())
        opts = {
            'skip_download': True,
            'writesubtitles': True,
            'subtitleslangs': ['en'],
            'writeautomaticsub': True,
            'outtmpl': f'/tmp/{file_uuid}',
            'quiet': True
        }

        with youtube_dl.YoutubeDL(opts) as ydl:
            ydl.download([self.url])

        filename = f'/tmp/{file_uuid}.en.vtt'
        if os.path.exists(filename):
            return self.__read_file_then_delete(filename)
        return ''


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
            subtitles = self.__get_subtitles()
            self.solution = VideoInformation(
                yt.title,
                yt.length,
                self.__bug_workaround_get_description(yt),
                download_encode_and_hash(yt.thumbnail_url),
                yt.keywords,
                subtitles)
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video information for %s",
                              self.url)
            return None