"""
Represents the Twitch source.
"""

import logging
from typing import Optional

import requests


# pylint: disable=too-few-public-methods
class TwitchSource:
    """
    Represents a Twitch source. Here, we for the existence of certain
    squares.
    """
    def __init__(self, who: str) -> None:
        self.who = who
        self.result: Optional[str] = None

    def get(self) -> Optional[str]:
        """
        Downloads information from the published JSON object ({who}.json).
        """
        if self.result:
            return self.result

        try:
            logging.info("Retrieving information for %s", self.who)
            response = requests.get(
                "https://raw.githubusercontent.com/neuro-arg/"
                f"arg-monitoring/publish/{self.who}.txt", timeout=5)

            if response.status_code == 404:
                logging.info(
                    "Could not get information for %s, it does not exist",
                    self.who)
                self.result = ''
            else:
                self.result = response.content.decode('utf-8')

            return self.result
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get information for %s", self.who)
            return None
