"""
Pulls metadata from YouTube.

All images will be encoded into base64
"""

import logging
import os
import base64
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

import yt_dlp
from dataclasses_json import dataclass_json
from utils import download_encode_and_hash, check_proxy_variables, download


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


@dataclass
class VideoInformationWithThumbnail:
    """
    VideoInformation but with thumbnail data
    """

    info: VideoInformation
    thumbnail_raw: str


class VideoInformationGetter:
    """
    Gets video information from YouTube
    """

    def __init__(self, url: str) -> None:
        self.url = url
        self.solution: Optional[VideoInformation] = None
        self.options = {"proxy": check_proxy_variables()}

    @staticmethod
    def __read_file_then_delete(filename: str) -> str:
        assert os.path.exists(filename)
        contents = ""
        with open(filename, "r", encoding="utf-8") as f:
            contents = f.read()
        os.remove(filename)
        return contents

    @staticmethod
    def __to_base64_url(data: bytes) -> str:
        data_as_base64 = base64.b64encode(data).decode()
        return f"data:image/jpeg;base64,{data_as_base64}"

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
            "skip_download": True,
            "writesubtitles": True,
            "subtitleslangs": ["en"],
            "writeautomaticsub": True,
            "outtmpl": f"/tmp/{file_uuid}",
            "quiet": True,
            **self.options,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([self.url])

        filename = f"/tmp/{file_uuid}.en.vtt"
        if os.path.exists(filename):
            return self.__read_file_then_delete(filename)
        return ""

    def get(self) -> Optional[VideoInformationWithThumbnail]:
        """
        Returns a VideoInformation object if the video exists,
        otherwise returns None

        This returning None should immediately ring alarm bells
        """
        if self.solution:
            return self.solution

        try:
            logging.info("Getting video information for %s", self.url)
            with yt_dlp.YoutubeDL(self.options) as ydl:
                info = ydl.sanitize_info(ydl.extract_info(self.url, download=False))

                self.solution = VideoInformationWithThumbnail(
                    VideoInformation(
                        info["title"],
                        info["duration"],
                        info["description"],
                        download_encode_and_hash(info["thumbnail"]),
                        info["tags"],
                        self.__get_subtitles(),
                    ),
                    self.__to_base64_url(download(info["thumbnail"])),
                )
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get video information for %s", self.url)
            return None
