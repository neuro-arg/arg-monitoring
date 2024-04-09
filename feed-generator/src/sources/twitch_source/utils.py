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

WHOSE_STREAM_SQUARE_NUMBER = 34
DETECTOR_THRESHOLD = 0.9


def nparray_crop_frame(image_array: np.ndarray,
                       real_height: float,
                       real_width: float) -> np.ndarray:
    """
    Crops the frame

    Args:
        image_array (np.ndarray): The image
        real_height (float): The real height
        real_width (float): The real width

    Returns:
        np.ndarray: The cropped image
    """
    return image_array[int(
        CROP_OFFSET_RATIO_Y * real_height):int(CROP_RATIO_Y * real_height),
                       int(CROP_OFFSET_RATIO_X * real_width):
                       int(CROP_RATIO_X * real_width)]


def nparray_segment_into_squares(image_array: np.ndarray,
                                 square_size: int) -> np.ndarray:
    """
    Segments the image into squares

    Args:
        image_array (np.ndarray): The image
        square_size (int): The size of the squares

    Returns:
        np.ndarray: The segmented image
    """
    height, width, depth = image_array.shape[0], image_array.shape[1], \
        image_array.shape[2]
    return image_array.reshape(
        (height // square_size, square_size,
         width // square_size, square_size, depth)).swapaxes(
             1, 2).reshape(-1, square_size, square_size, depth)


def nparray_squares_into_frame(image_array: np.ndarray, square_size: int,
                               original_height: int, original_width: int,
                               depth: int) -> np.ndarray:
    """
    Converts the squares back into an image

    Args:
        image_array (np.ndarray): The image
        square_size (int): The size of the squares
        original_height (int): The original height
        original_width (int): The original width
        depth (int): The depth

    Returns:
        np.ndarray: The image
    """
    return image_array.reshape(
        29, 29, square_size, square_size, depth).swapaxes(
            1, 2).reshape(
                original_height, original_width, depth)


def resize_image(image_array: np.ndarray, new_height: int,
                 new_width: int) -> np.ndarray:
    """
    Resizes an image

    Args:
        image_array (np.ndarray): The image
        new_height (int): The new height
        new_width (int): The new width

    Returns:
        np.ndarray: The resized image
    """
    # pylint: disable=no-member
    return cv2.resize(image_array, (new_width, new_height),
                      interpolation=cv2.INTER_AREA)


def create_process_for_720p_video_for_youtube(
        youtube_url: str) -> subprocess.Popen:
    """
    Creates a process for youtube-dl

    Args:
        youtube_url (str): The URL of the video

    Returns:
        subprocess.Popen: The process
    """
    command = f"youtube-dl -F '{youtube_url}' | grep '720p'"
    with subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE) as process:
        output = process.communicate()[0].decode('utf-8')

    final_code = '0'

    if "720p60" not in output:
        final_code = output.split('\n', maxsplit=1)[0] \
                           .split(' ', maxsplit=1)[0]
    else:
        final_code = [
            segment for segment in output.split('\n')
            if "720p60" in segment][0].split(' ')[0]

    command = (f"youtube-dl -f {final_code} -o - '{youtube_url}'"
               " | ffmpeg"
               " -i - -c:v ppm -f image2pipe -")
    return subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)


def create_process_for_ffmpeg_video(path: str) -> subprocess.Popen:
    """
    Creates a process for ffmpeg

    Args:
        path (str): The path to the video

    Returns:
        subprocess.Popen: The process
    """
    command = (f"ffmpeg"
               f" -i {path} -vf scale=1280:720 -c:v ppm -f image2pipe -")
    return subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,)


def ppm_header_parser(
        process: subprocess.Popen,
        stream: BytesIO, buffer: BytesIO
) -> tuple[int, int, int]:
    """
    Parses the PPM header

    Args:
        process (subprocess.Popen): The process
        stream (BytesIO): The stream
        buffer (BytesIO): The buffer

    Returns:
        tuple[int, int, int]: The width, height, and color value
    """
    # skips the P6 header
    header = next(process.stdout)  # type: ignore[arg-type]
    width_height_raw = next(stream)
    color_val_raw = next(stream)

    buffer.write(header)
    buffer.write(width_height_raw)
    buffer.write(color_val_raw)

    width, height = map(int, width_height_raw.split())
    color_val = int(color_val_raw)
    return width, height, color_val


def calculate_ssim(target: np.ndarray, reference: np.ndarray) -> float:
    """
    Calculates the difference using SSIM

    Args:
        target (np.ndarray): The target image
        reference (np.ndarray): The reference image

    Returns:
        float: The difference
    """
    return ssim(target, reference, multichannel=True, channel_axis=2)


def calculate_rgb_diff(target: np.ndarray, reference: np.ndarray) -> float:
    """
    Calcualtes the difference using RGB pixel values

    Args:
        target (np.ndarray): The target image
        reference (np.ndarray): The reference image

    Returns:
        float: The difference
    """
    percent = (255 - np.mean(np.abs(target - reference))) / 255.0
    normalized = percent * 2.0 - 1.0
    return 1 / (1 + np.exp(-normalized / 0.1))


def whose_stream(target: np.ndarray,
                 neuro_detector_square: np.ndarray,
                 evil_detector_square: np.ndarray,
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
    square = target[:square_size, (WHOSE_STREAM_SQUARE_NUMBER - 1)
                    * square_size:
                    WHOSE_STREAM_SQUARE_NUMBER * square_size]
    neuro_diff = calculate_rgb_diff(square, neuro_detector_square)
    evil_diff = calculate_rgb_diff(square, evil_detector_square)

    logging.info('Neuro diff: %s', neuro_diff)
    logging.info('Evil diff: %s', evil_diff)

    if neuro_diff > evil_diff and neuro_diff > DETECTOR_THRESHOLD:
        return 'neuro'

    if evil_diff > neuro_diff and evil_diff > DETECTOR_THRESHOLD:
        return 'evil'

    return 'dunno'
