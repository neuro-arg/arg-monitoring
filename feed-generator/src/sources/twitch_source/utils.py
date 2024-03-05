"""
Utility functions
"""

import subprocess
import logging
from io import BytesIO
from typing import Literal

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

CROP_RATIO_X = 0.453125
CROP_OFFSET_RATIO_X = 0
CROP_RATIO_Y = 0.9027777777777778
CROP_OFFSET_RATIO_Y = 0.09722222222222222

EXPECTED_WIDTH = 1280
EXPECTED_HEIGHT = 720

CROPPED_WIDTH = int(EXPECTED_WIDTH * CROP_RATIO_X -
                    CROP_OFFSET_RATIO_X * EXPECTED_WIDTH)
CROPPED_HEIGHT = int(EXPECTED_HEIGHT * CROP_RATIO_Y -
                     CROP_OFFSET_RATIO_Y * EXPECTED_HEIGHT)

DETECTOR_THRESHOLD = 0.9


def nparray_crop_frame(image_array: np.ndarray, real_height, real_width):
    return image_array[int(
        CROP_OFFSET_RATIO_Y * real_height):int(CROP_RATIO_Y * real_height),
                       int(CROP_OFFSET_RATIO_X * real_width):
                       int(CROP_RATIO_X * real_width)]


def nparray_segment_into_squares(image_array: np.ndarray, square_size: int):
    height, width, depth = image_array.shape[0], image_array.shape[1], \
        image_array.shape[2]
    return image_array.reshape(
        (height // square_size, square_size,
         width // square_size, square_size, depth)).swapaxes(
             1, 2).reshape(-1, square_size, square_size, depth)


def nparray_squares_into_frame(image_array: np.ndarray, square_size: int,
                               original_height: int, original_width: int,
                               depth: int):
    return image_array.reshape(
        29, 29, square_size, square_size, depth).swapaxes(
            1, 2).reshape(
                original_height, original_width, depth)


def resize_image(image_array: np.ndarray, new_height: int, new_width: int):
    return cv2.resize(image_array, (new_width, new_height),
                      interpolation=cv2.INTER_AREA)


def create_process_for_720p_video_for_youtube(
        youtube_url: str) -> subprocess.Popen:
    command = f"youtube-dl -F '{youtube_url}' | grep '720p'"
    with subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE) as process:
        output, _ = process.communicate()
        output = output.decode('utf-8')

    final_code = 0

    if "720p60" not in output:
        final_code = output.split('\n', max_split=1)[0] \
                           .split(' ', max_split=1)[0]
    else:
        final_code = [
            segment for segment in output.split('\n')
            if "720p60" in segment][0].split(' ')[0]

    command = (f"youtube-dl -f {final_code} -o - '{youtube_url}'"
               " | ffmpeg -i - -c:v ppm -f image2pipe -")
    return subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)


def ppm_header_parser(
        process: subprocess.Popen,
        stream: BytesIO, buffer: BytesIO
) -> tuple[int, int, int]:
    header = next(process.stdout)  # skips the P6 header
    width_height_raw = next(stream)
    color_val_raw = next(stream)

    buffer.write(header)
    buffer.write(width_height_raw)
    buffer.write(color_val_raw)

    width, height = map(int, width_height_raw.split())
    color_val = int(color_val_raw)
    return width, height, color_val


def calculate_ssim(target: np.ndarray, reference: np.ndarray) -> float:
    return ssim(target, reference, multichannel=True, channel_axis=2)


def whose_stream(target: np.ndarray,
                 neuro_detector_square: str,
                 evil_detector_square: str,
                 square_size: int) -> Literal['neuro', 'evil', 'dunno']:
    """
    Determines based on the first frame whose stream is being watched

    Args:
        target (np.ndarray): The target image
        neuro_detector_square (np.ndarray): The neuro detector
        evil_detector_square (np.ndarray): The evil detector
        square_size (int): The size of the squares

    Returns:
        Literal['neuro', 'evil', 'dunno']: The result
    """
    neuro_ssim = calculate_ssim(target[:square_size, :square_size],
                                neuro_detector_square)
    evil_ssim = calculate_ssim(target[:square_size, :square_size],
                               evil_detector_square)

    logging.info(f'Neuro SSIM: {neuro_ssim}')
    logging.info(f'Evil SSIM: {evil_ssim}')

    if neuro_ssim > evil_ssim and neuro_ssim > DETECTOR_THRESHOLD:
        return 'neuro'

    if evil_ssim > neuro_ssim and evil_ssim > DETECTOR_THRESHOLD:
        return 'evil'

    return 'dunno'
