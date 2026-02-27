"""Video I/O abstraction for MotionTracker.

Provides a factory function that returns cv2.VideoCapture for standard
video files and DicomCapture for DICOM files (.dcm, .dicom).
"""

import os

import cv2
import numpy as np

DICOM_EXTENSIONS = {".dcm", ".dicom"}


def open_video(path):
    """Open a video file, returning a cv2.VideoCapture-compatible object.

    Returns DicomCapture for DICOM files, cv2.VideoCapture otherwise.
    """
    _, ext = os.path.splitext(path)
    if ext.lower() in DICOM_EXTENSIONS:
        return DicomCapture(path)
    return cv2.VideoCapture(path)


class DicomCapture:
    """cv2.VideoCapture-compatible wrapper for DICOM multi-frame files.

    Reads all frames into memory on open. Supports the subset of the
    VideoCapture API used by MotionTracker: isOpened, get, set, read,
    retrieve, release.
    """

    def __init__(self, path):
        self._frames = None  # numpy array [N, H, W, 3] BGR uint8
        self._fps = 30.0
        self._pos = 0  # next frame to read
        self._last_frame = None  # last frame returned by read()
        self._opened = False

        try:
            import pydicom
        except ImportError:
            return

        try:
            ds = pydicom.dcmread(path)
        except Exception:
            return

        try:
            pixel_array = ds.pixel_array
        except Exception:
            return

        # Normalise shape to [N, H, W, channels]
        if pixel_array.ndim == 2:
            # Single frame grayscale [H, W] -> [1, H, W]
            pixel_array = pixel_array[np.newaxis, ...]

        if pixel_array.ndim == 3 and pixel_array.shape[-1] not in (3, 4):
            # [N, H, W] grayscale -> [N, H, W, 3] BGR
            pixel_array = np.stack(
                [pixel_array, pixel_array, pixel_array], axis=-1
            )
        elif pixel_array.ndim == 4 and pixel_array.shape[-1] == 3:
            # [N, H, W, 3] RGB -> BGR
            pixel_array = pixel_array[..., ::-1].copy()
        elif pixel_array.ndim == 4 and pixel_array.shape[-1] == 4:
            # [N, H, W, 4] RGBA -> BGR (drop alpha)
            pixel_array = pixel_array[..., 2::-1].copy()

        # Normalise to uint8
        if pixel_array.dtype != np.uint8:
            arr = pixel_array.astype(np.float64)
            mn, mx = arr.min(), arr.max()
            if mx > mn:
                arr = (arr - mn) / (mx - mn) * 255.0
            pixel_array = arr.astype(np.uint8)

        self._frames = pixel_array
        self._opened = True

        # Extract FPS from DICOM tags
        # CineRate (0018,0040) = frames per second
        # FrameTime (0018,1063) = milliseconds per frame
        cine_rate = getattr(ds, "CineRate", None)
        frame_time = getattr(ds, "FrameTime", None)

        if cine_rate is not None:
            try:
                self._fps = float(cine_rate)
            except (TypeError, ValueError):
                pass
        elif frame_time is not None:
            try:
                ft = float(frame_time)
                if ft > 0:
                    self._fps = 1000.0 / ft
            except (TypeError, ValueError):
                pass

    def isOpened(self):
        return self._opened

    def get(self, prop_id):
        if not self._opened:
            return 0.0
        if prop_id == cv2.CAP_PROP_FPS:
            return self._fps
        if prop_id == cv2.CAP_PROP_FRAME_COUNT:
            return float(len(self._frames))
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self._frames.shape[2])
        if prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self._frames.shape[1])
        if prop_id == cv2.CAP_PROP_POS_FRAMES:
            return float(self._pos)
        return 0.0

    def set(self, prop_id, value):
        if prop_id == cv2.CAP_PROP_POS_FRAMES:
            self._pos = int(value)
            return True
        return False

    def read(self):
        if not self._opened or self._pos < 0 or self._pos >= len(self._frames):
            self._last_frame = None
            return False, None
        frame = self._frames[self._pos].copy()
        self._last_frame = frame
        self._pos += 1
        return True, frame

    def retrieve(self):
        if self._last_frame is not None:
            return True, self._last_frame.copy()
        return False, None

    def release(self):
        self._frames = None
        self._last_frame = None
        self._opened = False
