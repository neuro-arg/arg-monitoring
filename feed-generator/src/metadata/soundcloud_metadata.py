"""
Pulls metadata from SoundCloud.

I don't particularly want to use an API, so we're using beautifulsoup
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional
import urllib.parse

import requests
from bs4 import BeautifulSoup
from dataclasses_json import dataclass_json
from utils import download_encode_and_hash


@dataclass_json
@dataclass
class SoundCloudUserInformation:
    """
    Contains SoundCloud user information
    """

    full_name: str
    banner: str
    n_tracks: int
    n_following: int
    n_visuals: int
    avatar: Optional[str]


class SoundCloudUserGetter:
    """
    Gets SoundCloud user information
    """

    RESOLVE_URL = "https://api-v2.soundcloud.com/resolve?url=%s&client_id=IvZsSdfTxP6ovYz9Nn4XGqmQVKs1vzbB"
    USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

    def __init__(self, url: str) -> None:
        self.url = url
        self.solution: Optional[SoundCloudUserInformation] = None

    def get(self) -> Optional[SoundCloudUserInformation]:
        """
        Gets user metadata by scraping soundcloud
        """
        if self.solution:
            return self.solution

        try:
            logging.info("Getting user information for %s", self.url)
            base64_url = urllib.parse.quote(self.url)
            complete_url = self.RESOLVE_URL % base64_url
            logging.info("Querying %s", complete_url)
            response = requests.get(
                complete_url, headers={"User-Agent": self.USER_AGENT}, timeout=60
            )
            logging.info("Headers sent: %s", response.headers)
            logging.info("Received status code %d", response.status_code)

            interesting_data = json.loads(response.content)
            self.solution = SoundCloudUserInformation(
                interesting_data["full_name"],
                download_encode_and_hash(
                    interesting_data["visuals"]["visuals"][0]["visual_url"]
                ),
                int(interesting_data["track_count"]),
                int(interesting_data["followings_count"]),
                len(interesting_data["visuals"]["visuals"]),
                download_encode_and_hash(interesting_data["avatar_url"]),
            )
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get user information for %s", self.url)
            return None
