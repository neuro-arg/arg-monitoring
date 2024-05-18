"""
Pulls metadata from YouTube a YouTube channel.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

import requests
from bs4 import BeautifulSoup
from dataclasses_json import dataclass_json
from utils import download_encode_and_hash


@dataclass_json
@dataclass
class ChannelInformation:
    """
    Represents a YouTube channel
    """
    name: str
    description: str
    tags: str
    profile_pic_hash: str
    profile_banner_hash: Optional[str]


class ChannelInformationGetter:
    """
    Gets YouTube channel information
    """
    # Sometimes YouTube prefers to /not/ return certain information.
    # We try at least this number of times before giving up
    RETRY_COUNT = 5

    def __init__(self, url: str) -> None:
        self.url = url
        self.solution: Optional[ChannelInformation] = None

    @staticmethod
    def _fail_key_error_silently(func: Callable[[], Any]) -> Optional[Any]:
        try:
            return func()
        except KeyError:
            return None

    @staticmethod
    def _parse_from_dict(data: Any) -> ChannelInformation:
        def banner_url_eval():
            if 'c4TabbedHeaderRenderer' in data['header']:
                logging.info('Using c4TabbedHeaderRenderer to get banner...')
                return (data['header']['c4TabbedHeaderRenderer']
                        ['banner']['thumbnails'][0]['url'])

            logging.info('Using pageHeaderRenderer to get banner...')
            return (data['header']['pageHeaderRenderer']['content']
                    ['pageHeaderViewModel']['banner']
                    ['imageBannerViewModel']['image']['sources'][0]['url'])

        return ChannelInformation(
            name=data['metadata']['channelMetadataRenderer']['title'],
            description=data['metadata']['channelMetadataRenderer']
            ['description'],
            tags=data['metadata']['channelMetadataRenderer']['keywords'],
            profile_pic_hash=download_encode_and_hash(
                data['metadata']['channelMetadataRenderer']['avatar']
                ['thumbnails'][0]['url']),
            profile_banner_hash=ChannelInformationGetter
            ._fail_key_error_silently(
                func=lambda: download_encode_and_hash(banner_url_eval()))
        )

    def _get_and_parse(self) -> Optional[ChannelInformation]:
        response = requests.get(self.url, timeout=5)
        parsed = BeautifulSoup(response.text, 'html.parser')
        scripts = parsed.find_all('script')

        for script in scripts:
            texted = script.get_text().strip()
            if 'var ytInitialData' not in texted[:17]:
                continue

            stripped = re.sub(r'var ytInitialData = ', '', texted, 1)[:-1]
            data = json.loads(stripped)
            retry_count = 0
            while retry_count < self.RETRY_COUNT:
                try:
                    return self._parse_from_dict(data)
                except KeyError as e:
                    logging.warning(
                        'Cannot get a key to create ChannelInformation. '
                        'Retrying: %d/%d',
                        retry_count, self.RETRY_COUNT, exc_info=e)
                    retry_count += 1
                    time.sleep(1)
                    continue

        return None

    def get(self) -> Optional[ChannelInformation]:
        """
        Gets channel information
        """
        if self.solution:
            return self.solution

        return self._get_and_parse()
