"""
This script analyzes the frames of a collection of YouTube videos.

It loads all the images from the source folder into a small vector
database, which is then used every frame to calculate SSIM between
each image and a particular square.

After this script is done, it will plot the SSIM scores for each
video.
"""

import os
import re
import time
import logging
from collections import namedtuple
from io import BytesIO
from multiprocessing import Pool
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image

from utils import (calculate_ssim, create_process_for_720p_video_for_youtube,
                   nparray_crop_frame, nparray_segment_into_squares,
                   ppm_header_parser, calculate_rgb_diff,
                   WHOSE_STREAM_SQUARE_NUMBER)

logging.basicConfig(level=logging.DEBUG, filename='analyze.log')

# Tuples
SourceImageTuple = namedtuple('SourceImageTuple',
                              ['array', 'square_number'])

# Constants
IMAGES: list[SourceImageTuple] = []
IMAGES_FILENAME_PATTERN = r'square_(\d+)_(\d+).png'
DEPTH = 3  # hardcoded for speed
SQUARE_SIZE = 20
DETECTOR_THRESHOLD = 0.9
GRACE_DETECTOR_PERIOD = 15  # number of frames off detection before quitting
TRAINING_CLIPS_LIST = input("Training clips list: ")
SRC_DIRECTORY = input('Source Directory: ')
DETECTION_SQUARE = input('Path to detection square: ')

# Preloaders
if not os.path.exists(SRC_DIRECTORY):
    raise FileNotFoundError(f"The directory {SRC_DIRECTORY} does not exist.")

if not os.path.exists(DETECTION_SQUARE):
    raise FileNotFoundError(f"The file {DETECTION_SQUARE} does not exist.")

if not os.path.exists(TRAINING_CLIPS_LIST):
    raise FileNotFoundError(f"The file {TRAINING_CLIPS_LIST} does not exist.")

with open(TRAINING_CLIPS_LIST, encoding='utf8') as file:
    YOUTUBE_VIDEOS = file.read().splitlines()

for file in sorted(os.listdir(SRC_DIRECTORY)):
    image = Image.open(os.path.join(SRC_DIRECTORY, file))
    matches = re.match(IMAGES_FILENAME_PATTERN, file)

    if not matches:
        print(f'The file {file} does not match the pattern. Skipping.')
        continue

    square_idx, sequence = matches.groups()
    IMAGES.append(SourceImageTuple(np.array(image), int(square_idx)))

# Functions
def process_squares_with_target_image(
        params: tuple[np.ndarray, SourceImageTuple]) -> float:
    """
    This function is designed to be run with multiprocessing.

    Args:
        params (tuple[np.ndarray, SourceImageTuple]): A tuple
                                                      containing the
                                                      squares and the
                                                      target image.

    Returns:
        float: An SSIM score
    """
    squares, target = params
    return calculate_ssim(squares[target.square_number], target.array)

def process_squares_with_target_images(params: tuple[np.ndarray, list[SourceImageTuple]]) -> list[float]:
    arr, tuples = params
    return list(process_squares_with_target_image((arr, tuple)) for tuple in tuples)


def do_one_video(link: str) -> list[float]:
    ds = np.array(Image.open(DETECTION_SQUARE))
    curr_dir = os.getcwd()
    grace = 0
    start_time = time.time()

    # DEBUG: Get elapsed time to calculate speed
    if logging.root.isEnabledFor(logging.DEBUG):
        interval_elapsed = time.time()
        framecount = 0

    with TemporaryDirectory() as tempdir:
        # chdir guard for the detection square
        os.chdir(tempdir)
        ssim_scores = [-1.0] * len(IMAGES)
        with create_process_for_720p_video_for_youtube(link) as process:
            assert process is not None

            while process.poll() is None:
                image_buffer = BytesIO()
                try:
                    (width, height, _) = ppm_header_parser(process, process.stdout, image_buffer)
                except StopIteration:
                    break

                image_buffer.write(process.stdout.read(width * height * DEPTH))
                image_buffer.seek(0)

                # TODO: it's probably possible to directly convert from the buffer stream to numpy
                image = Image.open(image_buffer)
                image_array = np.array(image)

                square = image_array[:SQUARE_SIZE,
                                     (WHOSE_STREAM_SQUARE_NUMBER - 1) * SQUARE_SIZE
                                     :WHOSE_STREAM_SQUARE_NUMBER * SQUARE_SIZE]
                ds_diff = calculate_rgb_diff(square, ds)
                if ds_diff < DETECTOR_THRESHOLD:
                    logging.debug("Link %s: Detection square not found, GRACE: %d, Diff: %d", link, grace, ds_diff)
                    grace += 1

                    if grace >= GRACE_DETECTOR_PERIOD:
                        logging.debug('Link %s: Detection square not found, quitting', link)
                        break
                else:
                    grace = 0

                image_array = nparray_crop_frame(image_array, height, width)
                segments = nparray_segment_into_squares(image_array, SQUARE_SIZE)

                ssim_results = map(process_squares_with_target_image,
                                   ((segments, tuple) for tuple in IMAGES))
                ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

                # DEBUG: Calculate speed
                if logging.root.isEnabledFor(logging.DEBUG):
                    framecount += 1
                    if time.time() - interval_elapsed >= 5:
                        logging.debug('Link %s: Speed for this process at %d fps',
                                      link,
                                      float(framecount) / (time.time() - interval_elapsed))
                        interval_elapsed = time.time()
                        framecount = 0

        elapsed = time.time() - start_time
        logging.info('Link %s: finished after %s seconds', link, elapsed)
        os.chdir(curr_dir)
        return ssim_scores


# Main
with Pool() as pool:
    logging.info('The script will be running on %d processes', pool._processes)
    logging.info('This will stress your PC!')
    video_ssim_scores = np.array(pool.map(do_one_video, YOUTUBE_VIDEOS))

mean = video_ssim_scores.mean(axis=0)
mins = video_ssim_scores.min(axis=0)
results = np.array(list(zip(mean, mins)))
np.savez('results.npz', thresholds=results,
         raw_results=video_ssim_scores)
print('Results:')
print(results)
print('Means:')
print(mean)
print('Mins:')
print(mins)
