"""
Utility functions for the application
"""

import hashlib
import logging

import requests


def download_encode_and_hash(url: str) -> str:
    """
    Downloads whatever URL is being pointed to, and hashes it
    """
    logging.info('Hashing %s', url)
    response = requests.get(url, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Could not download {url}")
    sha = hashlib.sha256()
    sha.update(response.content)
    return sha.hexdigest()
