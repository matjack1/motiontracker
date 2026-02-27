"""Region matching module for MotionTracker.

Finds tracking regions from a reference video in other videos using
template matching (with optional ORB feature matching fallback).
"""

import json
import os
import sys

import cv2
import numpy as np

from MotionTrackerBeta.batch import VIDEO_EXTENSIONS, find_videos
from MotionTrackerBeta.video_io import open_video


def read_frame(video_path, frame_num):
    """Read a specific frame from a video file. Returns BGR image or None."""
    cap = open_video(video_path)
    if not cap.isOpened():
        return None
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def extract_template(frame, rectangle):
    """Extract image patch from frame using (x, y, w, h) rectangle."""
    x, y, w, h = [int(v) for v in rectangle]
    return frame[y:y+h, x:x+w].copy()


def template_match(template, target_frame):
    """Find best template match location.

    Returns (x, y, confidence) where (x, y) is the top-left corner.
    """
    result = cv2.matchTemplate(target_frame, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    return max_loc[0], max_loc[1], max_val


def feature_match(ref_patch, target_frame, rectangle):
    """ORB feature matching fallback.

    Returns (x, y, confidence) or None if not enough matches.
    """
    orb = cv2.ORB_create(nfeatures=500)

    kp1, des1 = orb.detectAndCompute(ref_patch, None)
    kp2, des2 = orb.detectAndCompute(target_frame, None)

    if des1 is None or des2 is None or len(kp1) < 4 or len(kp2) < 4:
        return None

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(des1, des2, k=2)

    # Lowe's ratio test
    good = []
    for m_n in matches:
        if len(m_n) == 2:
            m, n = m_n
            if m.distance < 0.75 * n.distance:
                good.append(m)

    if len(good) < 4:
        return None

    src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
    if H is None:
        return None

    inliers = mask.ravel().sum()
    confidence = inliers / len(good)

    # Transform the top-left corner of the patch (0,0) to target frame coords
    x, y, w, h = [int(v) for v in rectangle]
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    transformed = cv2.perspectiveTransform(corners, H)
    new_x = int(transformed[0][0][0])
    new_y = int(transformed[0][0][1])

    return new_x, new_y, confidence


def match_object(ref_frame, target_frame, obj_dict, method="auto", threshold=0.7):
    """Match a single object from reference to target frame.

    Returns (updated_obj_dict, confidence, method_used) or (None, 0, None) on failure.
    """
    rect = obj_dict.get("rectangle")
    if not rect:
        return None, 0.0, None

    template = extract_template(ref_frame, rect)
    if template.size == 0:
        return None, 0.0, None

    x, y, w, h = [int(v) for v in rect]
    best_x, best_y, confidence, used_method = None, None, 0.0, None

    if method in ("template", "auto"):
        tx, ty, tconf = template_match(template, target_frame)
        if tconf >= threshold:
            best_x, best_y, confidence, used_method = tx, ty, tconf, "template"

    if used_method is None and method in ("feature", "auto"):
        result = feature_match(template, target_frame, rect)
        if result is not None:
            fx, fy, fconf = result
            if fconf >= threshold:
                best_x, best_y, confidence, used_method = fx, fy, fconf, "feature"

    if used_method is None:
        # Return the best template score even if below threshold for reporting
        if method != "feature":
            tx, ty, tconf = template_match(template, target_frame)
            return None, tconf, "template (below threshold)"
        return None, 0.0, None

    new_obj = dict(obj_dict)
    new_obj["rectangle"] = [best_x, best_y, w, h]

    # Preserve point offset relative to rectangle
    if obj_dict.get("point"):
        px, py = obj_dict["point"]
        offset_x = px - x
        offset_y = py - y
        new_obj["point"] = [best_x + offset_x, best_y + offset_y]

    return new_obj, confidence, used_method


def match_video(ref_frame, target_video_path, objects, method, threshold,
                target_frame_num):
    """Match all objects from reference into a target video.

    Returns list of (obj_name, matched_obj_dict_or_None, confidence, method_used).
    """
    target_frame = read_frame(target_video_path, target_frame_num)
    if target_frame is None:
        return [(o["name"], None, 0.0, "cannot read video") for o in objects]

    results = []
    for obj in objects:
        matched, conf, method_used = match_object(
            ref_frame, target_frame, obj, method, threshold
        )
        results.append((obj["name"], matched, conf, method_used))
    return results


def generate_settings(ref_settings, matched_objects, target_path):
    """Write .motiontracker.json for a target video."""
    data = {"version": 1, "objects": matched_objects}

    # Copy ruler, section, roi from reference
    for key in ("ruler", "section", "roi"):
        if key in ref_settings:
            data[key] = ref_settings[key]

    settings_path = target_path + ".motiontracker.json"
    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
    return settings_path


def run_match(args):
    """Entry point for the match CLI command."""
    ref_path = os.path.abspath(args.reference)
    if not os.path.isfile(ref_path):
        print(f"Reference video not found: {ref_path}", file=sys.stderr)
        sys.exit(1)

    settings_path = ref_path + ".motiontracker.json"
    if not os.path.isfile(settings_path):
        print(f"No settings file for reference video: {settings_path}",
              file=sys.stderr)
        sys.exit(1)

    with open(settings_path) as f:
        ref_settings = json.load(f)

    objects = ref_settings.get("objects", [])
    if not objects:
        print("No objects defined in reference settings.", file=sys.stderr)
        sys.exit(1)

    # Read reference frame
    ref_frame = read_frame(ref_path, args.frame)
    if ref_frame is None:
        print(f"Cannot read frame {args.frame} from {ref_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve target videos
    if args.targets:
        targets = find_videos(args.targets)
    else:
        targets = find_videos([os.path.dirname(ref_path)])

    # Exclude the reference video itself
    targets = [t for t in targets if os.path.abspath(t) != ref_path]

    if not targets:
        print("No target videos found.", file=sys.stderr)
        sys.exit(1)

    # Skip videos that already have settings (unless --overwrite)
    if not args.overwrite:
        before = len(targets)
        targets = [t for t in targets
                   if not os.path.isfile(t + ".motiontracker.json")]
        skipped = before - len(targets)
        if skipped:
            print(f"Skipping {skipped} video(s) with existing settings "
                  f"(use --overwrite to replace)")
        if not targets:
            print("No videos to process.")
            sys.exit(0)

    print("MotionTracker Region Matching")
    print("==============================")
    print(f"Reference: {os.path.basename(ref_path)} (frame {args.frame})")
    print(f"Objects:   {', '.join(o['name'] for o in objects)}")
    print(f"Method:    {args.method} (threshold: {args.threshold})")
    print(f"Targets:   {len(targets)} video(s)")
    if args.dry_run:
        print("Mode:      DRY RUN (no files written)")
    print()

    all_results = []
    for i, target in enumerate(targets, 1):
        name = os.path.basename(target)
        print(f"[{i}/{len(targets)}] {name}")

        results = match_video(
            ref_frame, target, objects, args.method, args.threshold,
            args.target_frame,
        )

        matched_objects = []
        all_ok = True
        for obj_name, matched, conf, method_used in results:
            status = f"  {obj_name}: "
            if matched:
                rx, ry = matched["rectangle"][:2]
                status += f"matched at ({rx}, {ry}) conf={conf:.3f} [{method_used}]"
                matched_objects.append(matched)
            else:
                status += f"NO MATCH conf={conf:.3f}"
                if method_used:
                    status += f" [{method_used}]"
                all_ok = False
            print(status)

        if matched_objects and not args.dry_run:
            sp = generate_settings(ref_settings, matched_objects, target)
            print(f"  -> wrote {os.path.basename(sp)}")

        all_results.append((target, all_ok, results))
        print()

    # Summary
    full_match = sum(1 for _, ok, _ in all_results if ok)
    partial = sum(1 for _, ok, r in all_results
                  if not ok and any(m is not None for _, m, _, _ in r))
    failed = sum(1 for _, ok, r in all_results
                 if not ok and all(m is None for _, m, _, _ in r))

    print(f"Summary: {full_match} fully matched, {partial} partial, "
          f"{failed} failed (out of {len(all_results)})")

    sys.exit(0 if failed == 0 else 1)
