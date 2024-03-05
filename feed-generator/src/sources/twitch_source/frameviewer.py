"""
This file runs the same preprocessing as the inference script. It
allows users to visually see the squares that can be used for
inference.

Each frame is overlayed with a mask to determine the square number. A
user can then use the frame number and square number to generate a
suitable square used by the tool.
"""

import os

import cv2
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import numpy as np
from PIL import Image

from utils import (CROPPED_HEIGHT, CROPPED_WIDTH, EXPECTED_HEIGHT,
                   EXPECTED_WIDTH, nparray_crop_frame,
                   nparray_segment_into_squares, resize_image)

SCALE = 5
SCALED_WIDTH = EXPECTED_WIDTH * SCALE
SCALED_HEIGHT = EXPECTED_HEIGHT * SCALE


class FrameNavigator:
    def __init__(self, video_path: str, output_dir: str) -> None:
        self.cap = cv2.VideoCapture(video_path)
        self.out_dir = output_dir
        self.frame_idx = 0

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self._create_mask()

        self.fig = plt.figure()
        self.button_next = widgets.Button(plt.axes([0.8, 0.025, 0.1, 0.075]),
                                          'Next')
        self.button_prev = widgets.Button(plt.axes([0.7, 0.025, 0.1, 0.075]),
                                          'Previous')
        self.button_save = widgets.Button(plt.axes([0.6, 0.025, 0.1, 0.075]),
                                          'Save')
        self.button_skip = widgets.Button(plt.axes([0.4, 0.025, 0.1, 0.075]),
                                          'Skip')
        self.square_input_box = widgets.TextBox(plt.axes([0.1, 0.025, 0.1, 0.075]),
                                                'Square #')
        self.frame_input_box = widgets.TextBox(plt.axes([0.3, 0.025, 0.1, 0.075]),
                                               'Frame #')
        self.button_skip.on_clicked(self._skip_frame)
        self.button_next.on_clicked(self._next_frame)
        self.button_prev.on_clicked(self._prev_frame)
        self.button_save.on_clicked(self._save)

        self.ax = plt.axes()
        self.ax.axis('off')
        self.original_img = None
        self.display_img = None

    def _save(self, event):
        if self.square_input_box.text and self.display_img:
            square_idx = int(self.square_input_box.text)
            frame = cv2.cvtColor(self.original_img, cv2.COLOR_BGR2RGB)
            frame = resize_image(frame, EXPECTED_HEIGHT, EXPECTED_WIDTH)
            frame = nparray_crop_frame(frame, EXPECTED_HEIGHT, EXPECTED_WIDTH)
            segments = nparray_segment_into_squares(frame, 20)

            file_idx = 0
            while os.path.exists(os.path.join(
                    self.out_dir, f'square_{square_idx}_{file_idx}.png')):
                file_idx += 1
            Image.fromarray(segments[square_idx]).save(
                os.path.join(self.out_dir,
                             f'square_{square_idx}_{file_idx}.png'))

    def _create_mask(self):
        self.mask = np.full((CROPPED_HEIGHT * SCALE, CROPPED_WIDTH * SCALE, 3),
                            255,
                            dtype=np.uint8)
        self.mask[20 * SCALE - 2::20 * SCALE, :] = 0
        self.mask[:, 20 * SCALE - 2::20 * SCALE] = 0

        self.mask = cv2.cvtColor(self.mask, cv2.COLOR_RGB2BGR)
        num_cells_vert = CROPPED_HEIGHT // 20
        num_cells_horiz = CROPPED_WIDTH // 20

        for i in range(num_cells_vert):
            for j in range(num_cells_horiz):
                cv2.putText(self.mask, str(i * num_cells_horiz + j),
                            (j * 20 * SCALE + 10, i * 20 * SCALE + 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    def run(self):
        self._update_frame()
        plt.show()

    def _skip_frame(self, event):
        try:
            self.frame_idx = int(self.frame_input_box.text)
            if self.frame_idx < 0:
                raise ValueError
        except ValueError:
            print('Not a valid frame number.')
            return

        self._update_frame()

    def _next_frame(self, event):
        self.frame_idx += 1
        self._update_frame()

    def _prev_frame(self, event):
        if self.frame_idx > 0:
            self.frame_idx -= 1
        self._update_frame()

    def _update_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_idx)
        ret, frame = self.cap.read()
        if not ret:
            print('Cannot read the frame.')
            return

        self.original_img = frame
        frame = resize_image(frame, SCALED_HEIGHT, SCALED_WIDTH)
        frame = nparray_crop_frame(frame, SCALED_HEIGHT, SCALED_WIDTH)

        alpha = 0.4
        overlay_frame = cv2.addWeighted(frame, 1-alpha, self.mask, alpha, 0)
        overlay_frame = cv2.cvtColor(overlay_frame, cv2.COLOR_BGR2RGB)

        plt.title(f'Frame Index: {self.frame_idx}')

        if self.display_img is None:
            self.display_img = self.ax.imshow(overlay_frame, aspect='auto')
            self.fig.canvas.draw()
        else:
            self.display_img.set_array(overlay_frame)
            self.fig.canvas.blit(self.display_img.clipbox)

if __name__ == '__main__':
    video_path_src = input("File Path: ")
    if not os.path.exists(video_path_src):
        print("File does not exist")
        exit(1)

    out_dir = input('Output Directory: ')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    FrameNavigator(video_path_src, out_dir).run()
