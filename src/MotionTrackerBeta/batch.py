"""Batch processing module for MotionTracker.

Processes multiple videos from the command line using per-video
.motiontracker.json settings and shared tracking/processing parameters.
"""

import glob
import json
import os
import sys

import cv2
import numpy as np
import pandas as pd

from MotionTrackerBeta.classes.classes import Motion, Ruler
from MotionTrackerBeta.widgets.trackers import TrackingThreadV2
from MotionTrackerBeta.widgets.process import PostProcesserThread

from MotionTrackerBeta.video_io import open_video

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".dcm", ".dicom"}


def find_videos(video_args):
    """Expand directories and globs into a list of video file paths."""
    result = []
    for arg in video_args:
        path = os.path.abspath(arg)
        if os.path.isdir(path):
            for f in sorted(os.listdir(path)):
                _, ext = os.path.splitext(f)
                if ext.lower() in VIDEO_EXTENSIONS:
                    result.append(os.path.join(path, f))
        elif os.path.isfile(path):
            result.append(path)
        else:
            for match in sorted(glob.glob(arg)):
                if os.path.isfile(match):
                    result.append(os.path.abspath(match))
    return result


def resolve_videos(video_args):
    """Find video files that have .motiontracker.json settings."""
    return [v for v in find_videos(video_args)
            if os.path.isfile(v + ".motiontracker.json")]


def build_diff_parameters(args):
    """Convert CLI args into the parameters tuple for PostProcesserThread.

    Returns a tuple like (optimize_bool, algo_name, params, options_dict).
    """
    algo_name = args.diff_algo
    optimize = args.optimize

    if algo_name in {"First Order Finite Difference", "Second Order Finite Difference"}:
        return (False, algo_name, None)

    if optimize:
        cutoff = float(args.diff_params) if args.diff_params else 1.0
        return (True, algo_name, cutoff)

    params_list = None
    if args.diff_params:
        params_list = []
        for p in args.diff_params.split(","):
            p = p.strip()
            try:
                params_list.append(int(p))
            except ValueError:
                params_list.append(float(p))

    options = {}
    if args.diff_options:
        options = json.loads(args.diff_options)

    if params_list is not None:
        return (False, algo_name, params_list, options)
    return (False, algo_name, None)


def process_single_video(video_path, tracker_type, size_tracking, fps_override,
                         diff_parameters, unit):
    """Process one video: track, differentiate, export CSV.

    Returns (success, csv_path, error_message).
    """
    settings_path = video_path + ".motiontracker.json"
    if not os.path.isfile(settings_path):
        return False, None, f"Settings file not found: {settings_path}"

    try:
        with open(settings_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return False, None, f"Cannot read settings: {e}"

    # Parse objects
    objects = [Motion.from_dict(d) for d in data.get("objects", [])]
    if not objects:
        return False, None, "No objects defined in settings"

    # Parse ruler
    ruler = Ruler()
    ruler_data = data.get("ruler")
    if ruler_data:
        ruler.load_from_dict(ruler_data)

    # Open video
    camera = open_video(video_path)
    if not camera.isOpened():
        return False, None, f"Cannot open video: {video_path}"

    num_frames = int(camera.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = camera.get(cv2.CAP_PROP_FPS)

    if fps_override:
        fps = fps_override
    elif video_fps > 0:
        fps = int(video_fps)
    else:
        camera.release()
        return False, None, "Cannot detect FPS; use --fps to specify"

    section = data.get("section", {})
    section_start = section.get("start", 1)
    section_stop = section.get("stop", num_frames)

    roi_rect = tuple(data["roi"]) if data.get("roi") else None

    # --- Tracking ---
    timestamp = []
    tracking_errors = []

    tracker_thread = TrackingThreadV2(
        objects, camera, section_start, section_stop,
        tracker_type, size_tracking, fps, timestamp, roi_rect,
    )
    tracker_thread.error_occured.connect(lambda msg: tracking_errors.append(msg))
    tracker_thread.run()

    camera.release()

    if tracking_errors:
        return False, None, f"Tracking failed: {tracking_errors[0]}"
    if not tracker_thread.is_running:
        return False, None, "Tracking failed"

    # --- Post-processing ---
    if len(timestamp) < 2:
        return False, None, "Not enough frames tracked"

    dt = timestamp[1] - timestamp[0]
    pp_errors = []

    pp_thread = PostProcesserThread(True, objects, dt, diff_parameters)
    pp_thread.error_occured.connect(lambda msg: pp_errors.append(msg))
    pp_thread.run()

    if pp_errors:
        return False, None, f"Processing failed: {pp_errors[0]}"

    # --- Export CSV ---
    cols = ["Time (s)"]
    data_arrays = [np.array(timestamp)]
    unit_suffix = unit

    for obj in objects:
        if obj.position is None:
            continue

        pos_x = obj.position[:, 0].copy()
        pos_y = -obj.position[:, 1].copy()
        vel_x = obj.velocity[:, 0].copy()
        vel_y = -obj.velocity[:, 1].copy()
        acc_x = obj.acceleration[:, 0].copy()
        acc_y = -obj.acceleration[:, 1].copy()

        if unit == "mm" and ruler.mm_per_pix is not None:
            pos_x *= ruler.mm_per_pix
            pos_y *= ruler.mm_per_pix
            vel_x *= ruler.mm_per_pix
            vel_y *= ruler.mm_per_pix
            acc_x *= ruler.mm_per_pix
            acc_y *= ruler.mm_per_pix
        elif unit == "m" and ruler.mm_per_pix is not None:
            factor = ruler.mm_per_pix / 1000
            pos_x *= factor
            pos_y *= factor
            vel_x *= factor
            vel_y *= factor
            acc_x *= factor
            acc_y *= factor
        elif unit in ("mm", "m") and ruler.mm_per_pix is None:
            unit_suffix = "pix"

        cols.extend([
            f"{obj.name} X pos ({unit_suffix})",
            f"{obj.name} Y pos ({unit_suffix})",
            f"{obj.name} X vel ({unit_suffix}/s)",
            f"{obj.name} Y vel ({unit_suffix}/s)",
            f"{obj.name} X acc ({unit_suffix}/s^2)",
            f"{obj.name} Y acc ({unit_suffix}/s^2)",
        ])
        data_arrays.extend([pos_x, pos_y, vel_x, vel_y, acc_x, acc_y])

    all_data = np.column_stack(data_arrays)
    df = pd.DataFrame(all_data, columns=cols)

    base, _ = os.path.splitext(video_path)
    csv_path = base + ".csv"
    df.to_csv(csv_path, index=False)

    return True, csv_path, None


def run_batch(args):
    """Entry point for batch CLI mode."""
    videos = resolve_videos(args.videos)
    if not videos:
        print("No video files found.", file=sys.stderr)
        sys.exit(1)

    # QCoreApplication required for QThread.__init__
    from PyQt5.QtCore import QCoreApplication
    app = QCoreApplication(sys.argv)  # noqa: F841

    diff_parameters = build_diff_parameters(args)

    print("MotionTracker Batch Mode")
    print("========================")
    print(f"Processing {len(videos)} video(s) with {args.tracker} tracker")
    diff_display = diff_parameters[2] if len(diff_parameters) > 2 else ""
    print(f"Differentiation: {args.diff_algo} {diff_display}")
    print()

    results = []
    for i, video_path in enumerate(videos, 1):
        name = os.path.basename(video_path)
        print(f"[{i}/{len(videos)}] {name} ... ", end="", flush=True)
        print("tracking ... ", end="", flush=True)

        success, csv_path, error = process_single_video(
            video_path, args.tracker, args.size_tracking,
            args.fps, diff_parameters, args.unit,
        )

        if success:
            print(f"processing ... OK -> {os.path.basename(csv_path)}")
        else:
            print(f"FAILED: {error}")

        results.append((video_path, success, csv_path, error))

    ok = sum(1 for _, s, _, _ in results if s)
    fail = len(results) - ok
    print(f"\nSummary: {ok}/{len(results)} succeeded, {fail} failed")
    if fail:
        print("Failed:")
        for path, success, _, error in results:
            if not success:
                print(f"  - {os.path.basename(path)}: {error}")

    sys.exit(0 if fail == 0 else 1)
