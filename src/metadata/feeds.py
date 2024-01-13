"""
Checks if an atom feed has updated.

Feeds usually only update when a new video/song is uploaded, or some
video metadata (like timestamps or something) are changed, so it is
usually safe to just hash the entire file.
"""

import hashlib
import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests


class FeedGetter:
    """
    Gets a feed, and removes any matching tags
    """
    def __init__(self, url: str, tags_to_remove: list[str]) -> None:
        self.url = url
        self.solution: Optional[str] = None
        self.tags_to_remove = tags_to_remove

    @staticmethod
    def __download_guard(url: str) -> str:
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Could not feed from {url}")
        return response.text

    def __interpret_and_remove_tags(self, feed: str) -> str:
        tree = ET.fromstring(feed)

        for tag in self.tags_to_remove:
            for parent in tree.findall(f'.//{tag}/..'):
                child = parent.find('.//' + tag)
                if child is None:
                    continue
                parent.remove(child)

        return ET.tostring(tree, encoding='unicode')

    def get(self) -> Optional[str]:
        """
        Returns the hash of the feed content
        """
        if self.solution:
            return self.solution

        try:
            feed = self.__interpret_and_remove_tags(
                self.__download_guard(self.url)
            )
            sha = hashlib.sha256()
            sha.update(feed.encode('utf-8'))
            self.solution = sha.hexdigest()
            return self.solution
        except:  # pylint: disable=bare-except # noqa: E722
            logging.exception("Could not get feed for %s",
                              self.url)
