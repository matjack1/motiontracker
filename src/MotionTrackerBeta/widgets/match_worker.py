"""Background thread for matching tracking regions across videos."""

import os

from PyQt5.QtCore import QThread, pyqtSignal

from MotionTrackerBeta.match import match_video


class MatchThread(QThread):
    """Matches regions from a reference frame to multiple target videos."""

    progressChanged = pyqtSignal(int)
    videoStarted = pyqtSignal(str)
    videoFinished = pyqtSignal(str, list)
    success = pyqtSignal(list)
    error_occured = pyqtSignal(str)

    def __init__(self, ref_frame, ref_settings, targets, method, threshold,
                 target_frame_num, overwrite):
        super().__init__()
        self.ref_frame = ref_frame
        self.ref_settings = ref_settings
        self.objects = ref_settings.get("objects", [])
        self.targets = targets
        self.method = method
        self.threshold = threshold
        self.target_frame_num = target_frame_num
        self.overwrite = overwrite
        self.is_running = True

    def cancel(self):
        self.is_running = False

    def run(self):
        all_results = []
        for i, target_path in enumerate(self.targets):
            if not self.is_running:
                return

            name = os.path.basename(target_path)
            self.videoStarted.emit(name)

            if not self.overwrite and os.path.isfile(target_path + ".motiontracker.json"):
                self.videoFinished.emit(name, [])
                all_results.append((target_path, []))
                progress = int((i + 1) / len(self.targets) * 100)
                self.progressChanged.emit(progress)
                continue

            try:
                results = match_video(
                    self.ref_frame, target_path, self.objects,
                    self.method, self.threshold, self.target_frame_num,
                )
            except Exception as e:
                self.error_occured.emit(f"Error matching {name}: {e}")
                return

            self.videoFinished.emit(name, results)
            all_results.append((target_path, results))

            progress = int((i + 1) / len(self.targets) * 100)
            self.progressChanged.emit(progress)

        if self.is_running:
            self.success.emit(all_results)
