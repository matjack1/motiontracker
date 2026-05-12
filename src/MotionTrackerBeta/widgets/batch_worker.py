"""Background thread for batch processing multiple videos."""

import os

from PyQt5.QtCore import QThread, pyqtSignal

from MotionTrackerBeta.batch import process_single_video


class BatchThread(QThread):
    """Processes multiple videos: track, differentiate, export CSV."""

    progressChanged = pyqtSignal(int)
    videoStarted = pyqtSignal(str, int, int)
    videoFinished = pyqtSignal(str, bool, str, str)
    success = pyqtSignal()
    error_occured = pyqtSignal(str)

    def __init__(self, videos, tracker_type, size_tracking, fps_override,
                 diff_parameters, unit):
        super().__init__()
        self.videos = videos
        self.tracker_type = tracker_type
        self.size_tracking = size_tracking
        self.fps_override = fps_override
        self.diff_parameters = diff_parameters
        self.unit = unit
        self.is_running = True
        self.results = []

    def cancel(self):
        self.is_running = False

    def run(self):
        for i, video_path in enumerate(self.videos):
            if not self.is_running:
                return

            name = os.path.basename(video_path)
            self.videoStarted.emit(name, i + 1, len(self.videos))

            try:
                ok, csv_path, error = process_single_video(
                    video_path, self.tracker_type, self.size_tracking,
                    self.fps_override, self.diff_parameters, self.unit,
                )
            except Exception as e:
                ok, csv_path, error = False, None, str(e)

            self.results.append((video_path, ok, csv_path, error))
            self.videoFinished.emit(name, ok, csv_path or "", error or "")

            progress = int((i + 1) / len(self.videos) * 100)
            self.progressChanged.emit(progress)

        if self.is_running:
            self.success.emit()
