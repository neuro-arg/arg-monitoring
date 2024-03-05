"""
Standalone script to listen to a Twitch stream starting and run GitHub
actions.
"""

import asyncio
import configparser
import logging
import os
import sys

from typing import Optional

from twitchAPI.twitch import Twitch
from twitchAPI.eventsub.webhook import EventSubWebhook
from twitchAPI.object.eventsub import StreamOnlineEvent
from github import Github, Auth

logging.basicConfig(level=logging.INFO)

g: Optional[Github] = None


async def on_online(_event: StreamOnlineEvent) -> None:
    """
    Callback for an online stream.

    Args:
        _event (StreamOnlineEvent): The event
    """
    assert g

    logging.info('Monitored stream online! Triggering workflow...')
    g.get_repo(
        'neuro-arg/arg-monitoring'
    ).get_workflow(
        'twitch-stream-trigger.yml'
    ).create_dispatch(ref='main')
    logging.info('Workflow triggered!')


async def hook(webhook_url: str, client_id: str,
               client_secret: str, user_id: str) -> None:
    """
    Listen to a Twitch stream starting and run GitHub actions.

    Args:
        webhook_url (str): The webhook URL
        client_id (str): The client ID
        client_secret (str): The client secret
        user_id (str): The user ID to monitor
    """
    twitch = await Twitch(client_id, client_secret)
    eventsub = EventSubWebhook(webhook_url, 8080, twitch)
    await eventsub.unsubscribe_all()
    eventsub.start()
    await eventsub.listen_stream_online(user_id, on_online)

    logging.info('Started listening...')
    try:
        input('Press Enter to shut down...')
    finally:
        await eventsub.stop()
        await twitch.close()
    logging.info('Stopped listening...')


if __name__ == '__main__':
    if not os.path.exists('secrets.ini'):
        config = configparser.ConfigParser()
        config['options'] = {
            'twitch_client_id': '',
            'twitch_client_secret': '',
            'webhook_url': '',
            'user_id': '',
            'github_token': '',
        }

        with open('secrets.ini', 'w', encoding='ascii') as configfile:
            config.write(configfile)
        print('Please fill in the secrets.ini file. (Generated)')
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read('secrets.ini')

    try:
        _client_id = config['options']['twitch_client_id']
        _client_secret = config['options']['twitch_client_secret']
        _webhook_url = config['options']['webhook_url']
        _user_id = config['options']['user_id']
        _github_token = config['options']['github_token']
    except KeyError:
        print('Please fill in the secrets.ini file.')
        sys.exit(1)

    github = Github(auth=Auth.Token(_github_token))
    asyncio.run(hook(_webhook_url, _client_id, _client_secret, _user_id))
