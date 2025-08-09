"""
Utility functions for the application
"""

import hashlib
import logging
import os
from typing import Optional

import requests


def download(url: str) -> bytes:
    """
    Downloads the URL and get bytes
    """
    logging.info('Downloading %s', url)
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Could not download {url}")
    return response.content


def download_encode_and_hash(url: str) -> str:
    """
    Downloads whatever URL is being pointed to, and hashes it
    """
    data = download(url)
    sha = hashlib.sha256()
    sha.update(data)
    return sha.hexdigest()


def check_proxy_variables() -> Optional[str]:
    """
    Checks whether the proxy incantation exists
    """
    result = os.getenv('PROXY_INCANTATION')
    if result:
        logging.info('Will be using proxy')
    return result
