"""
Specialized script to run scrutinize functions on vedal987's stream.

This is meant to be called from a GitHub workflow.
"""

import json
import logging
import subprocess
import sys
import os

import numpy as np
from PIL import Image

from scrutinize import (load_images_from_directory, load_thresholds,
                        read_one_frame, scrutinize_with_images_and_thresholds,
                        extract_dynamic_detector_square)
from utils import whose_stream

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# pylint: disable=invalid-name
# This entire script is like a main script, ignore capitalization rules

# Constants
if 'TWITCH_OAUTH' not in os.environ:
    logger.warning('No Twitch OAuth token, might lose some video data!')

twitch_oauth = os.environ.get('TWITCH_OAUTH', None)
twitch_username = 'vedal987'
neuro_folder = './neuro'
evil_folder = './evil'
tutel_detector = np.array(Image.open('./detectors/tutel_detector.png'))
neuro_detector = np.array(Image.open('./detectors/neuro_detector.png'))
evil_detector = np.array(Image.open('./detectors/evil_detector.png'))
neuro_thresholds = './neuro.npz'
evil_thresholds = './evil.npz'
square_size = 20
depth = 3

# NOTE: FPS is forcefully tuned down to 30. Not sure if this affects accuracy
# but it improves inference performance
oauth_flag = ' ' if twitch_oauth is None \
    else f' "--twitch-api-header=Authorization=OAuth {twitch_oauth}" '
command = ('streamlink --twitch-disable-ads --twitch-low-latency'
           + ' --hls-live-restart'  # start from the beginning
           + oauth_flag
           + f'https://www.twitch.tv/{twitch_username} best -O | '
           'ffmpeg -i - -vf "scale=1280:720,fps=30" -c:v ppm -f image2pipe -')
detected_streamers = None

if __name__ != '__main__':
    raise ImportError('This script is meant to be run as a main script.')

while detected_streamers is None or len(detected_streamers) > 0:
    with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE) \
         as process:
        first_frame = read_one_frame(process)[0]
        if detected_streamers is None:
            detected_streamers = [whose_stream(first_frame,
                                               tutel_detector,
                                               neuro_detector,
                                               evil_detector,
                                               square_size)]

        threshold_file = (neuro_thresholds if detected_streamers[0] == 'neuro'
                          else evil_thresholds)
        images_folder = (neuro_folder if detected_streamers[0] == 'neuro'
                         else evil_folder)

        logger.info('Detected streamer: %s', detected_streamers[0])

        if detected_streamers[0] == 'tutel':
            logger.info(
                'Tutel is streaming, no clue expected. Have a good stream!')
            break

        if detected_streamers[0] == 'dunno':
            logger.warning('Could not determine the streamer, panic mode.')
            logger.warning(
                'Panic mode will produce results for both streamers')
            detected_streamers = ['neuro', 'evil']

        logging.info('Now processing for %s', detected_streamers[0])
        images = load_images_from_directory(images_folder)
        thresholds = load_thresholds(threshold_file)
        detector_square = extract_dynamic_detector_square(first_frame,
                                                          square_size)

        if len(images) != len(thresholds):
            logger.fatal('Mismatch between images and thresholds')
            sys.exit(1)

        results = scrutinize_with_images_and_thresholds(
            process, images, thresholds, detector_square)

        with open(f'{detected_streamers[0]}.json', 'w',
                  encoding='utf8') as file:
            json.dump(results, file)

        detected_streamers.pop(0)
