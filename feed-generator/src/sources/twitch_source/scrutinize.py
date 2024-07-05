"""
This script provides functions to scrutinizes the frames of any
arbitrary process (as long as it outputs PPM files)

It loads all the images from the source folder into a small vector
database, which is then used every frame to calculate SSIM between
each image and a particular square.

It then compares it to a pre-computed thresholds file, and outputs
those those squares that are above the threshold.
"""

import logging
import os
import re
import subprocess
import time
from collections import namedtuple
from io import BytesIO
from typing import cast

import numpy as np
from PIL import Image

from utils import (DETECTOR_THRESHOLD, EXPECTED_HEIGHT, EXPECTED_WIDTH,
                   WHOSE_STREAM_SQUARE_NUMBER, calculate_rgb_diff,
                   calculate_ssim, create_process_for_720p_video_for_youtube,
                   nparray_crop_frame, nparray_segment_into_squares,
                   ppm_header_parser, whose_stream,
                   extract_dynamic_detector_square)

# Tuples
# TODO: put into utilities
SourceImageTuple = namedtuple('SourceImageTuple',
                              ['array', 'square_number'])
DEPTH = 3  # hardcoded for speed
SQUARE_SIZE = 20
IMAGES_FILENAME_PATTERN = r'square_(\d+)_(\d+).png'


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


def load_images_from_directory(dirname: str) -> list[SourceImageTuple]:
    """
    Load images from a directory.

    Args:
        dirname (str): The directory name

    Returns:
        list[SourceImageTuple]: A list of SourceImageTuples
    """
    images = []
    for file in sorted(os.listdir(dirname)):
        image = Image.open(os.path.join(dirname, file))
        matches = re.match(IMAGES_FILENAME_PATTERN, file)

        if not matches:
            print(f'The file {file} does not match the pattern. Skipping.')
            continue

        square_idx, _sequence = matches.groups()
        images.append(SourceImageTuple(np.array(image), int(square_idx)))

    return images


def load_thresholds(filename: str) -> np.ndarray:
    """
    Load thresholds from a file. Not expecting the thresholds file to
    be too large to fit in memory.

    Args:
        filename (str): The filename

    Returns:
        np.ndarray: A numpy array
    """
    thresholds_handle = np.load(filename, mmap_mode='r')
    thresholds = thresholds_handle['thresholds']
    thresholds_handle.close()
    return thresholds


def read_one_frame(
        process: subprocess.Popen,
) -> tuple[np.array, int, int]:
    """
    Reads one frame from a process.

    Args:
        process (subprocess.Popen): The process

    Returns:
        tuple[nd.array, int, int]: A tuple containing the image array,
                                   the width, and the height

    Throws:
        StopIteration: If the process has no more frames
    """
    image_buffer = BytesIO()
    (width, height, _) = ppm_header_parser(
        process, cast(BytesIO,
                      process.stdout), image_buffer)

    image_buffer.write(process.stdout.read(width * height * DEPTH))
    image_buffer.seek(0)
    image = Image.open(image_buffer)
    image.resize((EXPECTED_WIDTH, EXPECTED_HEIGHT))
    image_array = np.array(image)
    return (image_array, width, height)


def scrutinize_with_images_and_thresholds(  # pylint: disable=too-many-locals
        process: subprocess.Popen,
        images: list[SourceImageTuple],
        thresholds: np.ndarray,
        detector_square: np.ndarray,
) -> list[bool]:
    """
    Scrutinize the frames of a process. The process must output images
    in PPM file format within stdout.

    Args:
        process (subprocess.Popen): The process
        images (list[SourceImageTuple]): The images
        thresholds (np.ndarray): The thresholds
        np.ndarray: The detector square. If this square is no longer
                    detected, the function will stop

    Returns:
        list[bool]: A list of booleans. If true, it means that the
                    square has been found in the stream
                    somewhere. False otherwise
    """
    assert process.stdout is not None

    start_time = time.time()
    ssim_scores = [-1.0] * len(images)
    ssim_mismatch_time = None  # This is init once for optimization purposes
    while process.poll() is None:
        if time.time() - start_time > 1800:
            logging.warning('Monitoring timeout. Might want to alert the dev.')
            break

        try:
            (image_array, width, height) = read_one_frame(process)
        except StopIteration:
            break

        if calculate_ssim(
                extract_dynamic_detector_square(image_array, SQUARE_SIZE),
                detector_square) < DETECTOR_THRESHOLD:
            if ssim_mismatch_time is None:
                ssim_mismatch_time = time.time()
                logging.info('Detector square not found! Grace period started.')
            elif time.time() - ssim_mismatch_time > 5:
                logging.info('Detector square not found after 5 seconds.')
                break
        elif ssim_mismatch_time is not None:
            logging.info('Detector square recovered after lost for %d seconds',
                         time.time() - ssim_mismatch_time)
            ssim_mismatch_time = None

        image_array = nparray_crop_frame(image_array, height, width)
        segments = nparray_segment_into_squares(image_array, SQUARE_SIZE)

        ssim_results = map(process_squares_with_target_image,
                           ((segments, tuple) for tuple in images))
        ssim_scores = [max(x, y) for x, y in zip(ssim_scores, ssim_results)]

    results = []
    logging.info('SSIM scores: %s', [float(score) for score in ssim_scores])
    for idx, score in enumerate(ssim_scores):
        mean, mini = thresholds[idx]
        results.append(bool(score + (mean - mini) >= mean))
    return results


if __name__ == '__main__':
    IMAGES: list[SourceImageTuple] = []
    THRESHOLDS: np.ndarray
    SRC_DIRECTORY_NEURO = input('Neuro Source Directory: ')
    SRC_DIRECTORY_EVIL = input('Evil Source Directory: ')
    THRESHOLDS_FILE_NEURO = input('Thresholds File (Neuro): ')
    THRESHOLDS_FILE_EVIL = input('Thresholds File (Evil): ')
    LINK = input('YouTube Link: ')

    # Preloaders
    if not os.path.exists(SRC_DIRECTORY_NEURO):
        raise FileNotFoundError(
            f"The directory {SRC_DIRECTORY_NEURO} does not exist.")

    if not os.path.exists(SRC_DIRECTORY_EVIL):
        raise FileNotFoundError(
            f"The directory {SRC_DIRECTORY_EVIL} does not exist.")

    if not os.path.exists(THRESHOLDS_FILE_NEURO):
        raise FileNotFoundError(
            f"The file {THRESHOLDS_FILE_NEURO} does not exist.")

    if not os.path.exists(THRESHOLDS_FILE_EVIL):
        raise FileNotFoundError(
            f"The file {THRESHOLDS_FILE_EVIL} does not exist.")

    tutel_ds = np.array(Image.open('detectors/tutel_detector.png'))
    neuro_ds = np.array(Image.open('detectors/neuro_detector.png'))
    evil_ds = np.array(Image.open('detectors/evil_detector.png'))

    with create_process_for_720p_video_for_youtube(LINK) as PROCESS:
        assert PROCESS is not None

        FIRST_FRAME = read_one_frame(PROCESS)[0]
        DETECTED_STREAMER = whose_stream(FIRST_FRAME,
                                         tutel_ds,
                                         neuro_ds,
                                         evil_ds,
                                         SQUARE_SIZE)

        print(f'This is {DETECTED_STREAMER}\'s stream')
        assert DETECTED_STREAMER not in ('dunno', 'tutel')

        IMAGES = load_images_from_directory(SRC_DIRECTORY_NEURO if
                                            DETECTED_STREAMER == 'neuro'
                                            else SRC_DIRECTORY_EVIL)
        THRESHOLDS = load_thresholds(THRESHOLDS_FILE_NEURO if
                                     DETECTED_STREAMER == 'neuro'
                                     else THRESHOLDS_FILE_EVIL)

        assert len(IMAGES) == len(THRESHOLDS)

        RESULTS = scrutinize_with_images_and_thresholds(
            PROCESS, IMAGES, THRESHOLDS,
            extract_dynamic_detector_square(FIRST_FRAME, SQUARE_SIZE)
        )
        print(RESULTS)
