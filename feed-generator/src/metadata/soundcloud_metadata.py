"""
Pulls metadata from SoundCloud.

I don't particularly want to use an API, so we're using beautifulsoup
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

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
            response = requests.get(self.url, timeout=60)
            soup = BeautifulSoup(response.content, "html.parser")

            matches = [
                str(s) for s in soup.find_all('script') if "/572943" in str(s)]
            if len(matches) == 0:
                raise RuntimeError("no matches found")

            target_json = matches[0][32:-10]
            obj = json.loads(target_json)
            interesting_data = obj[5]
            self.solution = SoundCloudUserInformation(
                interesting_data["data"]["full_name"],
                download_encode_and_hash(
                    interesting_data["data"]["visuals"]["visuals"][0]
                    ["visual_url"]),
                int(interesting_data["data"]["track_count"]),
                int(interesting_data["data"]["followings_count"]),
                len(interesting_data["data"]["visuals"]["visuals"]),
                download_encode_and_hash(
                    interesting_data["data"]["avatar_url"])
            )
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get user information for %s",
                              self.url)
            return None
