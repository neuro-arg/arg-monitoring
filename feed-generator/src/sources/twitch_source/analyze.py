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
from collections import namedtuple
from io import BytesIO
# NOTE: Artifacts from parallelization attempts
# from concurrent.futures import ThreadPoolExecutor
# from multiprocessing import Pool
from typing import Callable

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

from utils import (calculate_ssim, create_process_for_720p_video_for_youtube,
                   nparray_crop_frame, nparray_segment_into_squares,
                   ppm_header_parser)

# Tuples
SourceImageTuple = namedtuple('SourceImageTuple',
                              ['array', 'square_number'])

# Constants
# YOUTUBE_VIDEOS: list[str] = [
#     'https://www.youtube.com/watch?v=-hq32Cs6pGo',
#     'https://www.youtube.com/watch?v=jmYBl0ID-fQ',
# ]
YOUTUBE_VIDEOS: list[str] = [
    'https://www.youtube.com/watch?v=IDqL1SUGXNk',
]
IMAGES: list[SourceImageTuple] = []
IMAGES_FILENAME_PATTERN = r'square_(\d+)_(\d+).png'
DEPTH = 3  # hardcoded for speed
SQUARE_SIZE = 20
DETECTOR_THRESHOLD = 0.9
SRC_DIRECTORY = input('Source Directory: ')
DETECTION_SQUARE = input('Path to detection square: ')

# Preloaders
if not os.path.exists(SRC_DIRECTORY):
    raise FileNotFoundError(f"The directory {SRC_DIRECTORY} does not exist.")

if not os.path.exists(DETECTION_SQUARE):
    raise FileNotFoundError(f"The file {DETECTION_SQUARE} does not exist.")

for file in sorted(os.listdir(SRC_DIRECTORY)):
    image = Image.open(os.path.join(SRC_DIRECTORY, file))
    matches = re.match(IMAGES_FILENAME_PATTERN, file)

    if not matches:
        print(f'The file {file} does not match the pattern. Skipping.')
        continue

    square_idx, sequence = matches.groups()
    IMAGES.append(SourceImageTuple(np.array(image), int(square_idx)))

# Functions
def process_squares_with_target_image(params: tuple[np.ndarray, SourceImageTuple]) -> float:
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

# Main
video_ssim_scores = []
ds = np.array(Image.open(DETECTION_SQUARE))
for link in YOUTUBE_VIDEOS:
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

            if calculate_ssim(image_array[:SQUARE_SIZE, :SQUARE_SIZE],
                              ds) < DETECTOR_THRESHOLD:
                break

            image_array = nparray_crop_frame(image_array, height, width)
            segments = nparray_segment_into_squares(image_array, SQUARE_SIZE)

            ssim_results = map(process_squares_with_target_image,
                               ((segments, tuple) for tuple in IMAGES))
            ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

            # NOTE: These were attempts at parallelization, but all of them were
            # slower than sequential execution

            # with ThreadPoolExecutor() as executor:
            #     ssim_results = list(
            #         item for l1 in executor.map(
            #             process_squares_with_target_images,
            #             ((segments, IMAGES[idx:idx + 4])
            #              for idx in range(0, len(IMAGES), 4)))
            #         for item in l1)
            #     ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

            # with ThreadPoolExecutor() as executor:
            #     ssim_results = list(executor.map(process_squares_with_target_image,
            #                                      ((segments, tuple) for tuple in IMAGES)))
            #     ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

            # with Pool() as pool:
            #     ssim_results = pool.map(process_squares_with_target_image,
            #                             ((segments, tuple) for tuple in IMAGES))
            #     ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

    video_ssim_scores.append(ssim_scores)

mean = np.array(video_ssim_scores).mean(axis=0)
mins = np.array(video_ssim_scores).min(axis=0)
results = np.array(list(zip(mean, mins)))
np.savez('results.npz', thresholds=results)
print('Means:')
print(mean)
print('Mins:')
print(mins)
