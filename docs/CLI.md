# Command-Line Interface Reference

MotionTracker provides a CLI for launching the GUI, batch processing videos, and matching tracking regions across videos.

```
motiontracker <command> [options]
```

---

## Commands

| Command | Description |
|---------|-------------|
| `gui`   | Launch the graphical interface (default if no command given) |
| `batch` | Process multiple videos headlessly |
| `match` | Match tracking regions from a reference video to others |

---

## `motiontracker gui`

Launches the graphical user interface. This is the default when no command is specified.

```
motiontracker
motiontracker gui
```

---

## `motiontracker batch`

Process multiple videos from the command line using saved `.motiontracker.json` settings files. Each video must have a corresponding settings file (created via GUI or the `match` command).

```
motiontracker batch <videos...> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `videos` | One or more video files or directories to process. Directories are scanned for video files that have matching `.motiontracker.json` settings. |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--tracker` | `CSRT` | Tracking algorithm. Choices: `CSRT`, `BOOSTING`, `MIL`, `KCF`, `TLD`, `MEDIANFLOW`, `MOSSE` |
| `--size-tracking` | off | Enable size change tracking (forces CSRT) |
| `--fps` | auto | Override video FPS (default: read from video metadata) |
| `--diff-algo` | `Savitzky-Golay Filter` | Differentiation algorithm name |
| `--diff-params` | none | Comma-separated algorithm parameters (e.g., `3,15,15`) |
| `--diff-options` | none | JSON string of algorithm options dict |
| `--optimize` | off | Use optimization-based differentiation |
| `--unit` | `pix` | Output unit: `pix`, `mm`, or `m`. `mm`/`m` require a ruler in settings. |

### Output

For each processed video, a CSV file is created alongside the video (e.g., `video.csv`) containing:
- Time (s)
- Per-object: X/Y position, velocity, and acceleration

### Examples

```bash
# Process all videos in a directory
motiontracker batch ./experiment/

# Process specific videos with KCF tracker
motiontracker batch video1.mp4 video2.mp4 --tracker KCF

# Process with custom differentiation
motiontracker batch ./videos/ --diff-algo "Savitzky-Golay Filter" --diff-params "3,15,15"

# Process with optimization and metric units
motiontracker batch ./videos/ --optimize --unit mm
```

### Settings File Format

Each video requires a `.motiontracker.json` file (e.g., `video.mp4.motiontracker.json`) with the following structure:

```json
{
  "version": 1,
  "objects": [
    {
      "name": "Object 1",
      "point": [x, y],
      "rectangle": [x, y, width, height],
      "rectangle_visible": true
    }
  ],
  "ruler": {
    "x0": 0, "y0": 0,
    "x1": 100, "y1": 0,
    "mm": 50.0
  },
  "section": {
    "start": 1,
    "stop": 500
  },
  "roi": [x0, y0, x1, y1]
}
```

Settings files can be created via the GUI (Save Settings button) or generated automatically with `motiontracker match`.

---

## `motiontracker match`

Find tracking regions from a reference video in other videos using computer vision matching. Generates `.motiontracker.json` settings files for the target videos so they can be processed with `motiontracker batch`.

```
motiontracker match <reference> [targets...] [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `reference` | Reference video that has an existing `.motiontracker.json` settings file |
| `targets` | Target video files or directories (default: all videos in the same directory as reference) |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--frame` | `0` | Frame number to extract templates from in the reference video |
| `--target-frame` | `0` | Frame number to search in target videos |
| `--method` | `auto` | Matching method: `template`, `feature`, or `auto` |
| `--threshold` | `0.7` | Minimum confidence (0-1) to accept a match |
| `--dry-run` | off | Show match results without writing settings files |
| `--overwrite` | off | Overwrite existing settings files (default: skip videos that already have one) |

### Matching Methods

| Method | Description |
|--------|-------------|
| `template` | OpenCV template matching (`TM_CCOEFF_NORMED`). Fast and effective when videos have similar framing. |
| `feature` | ORB feature detection with brute-force matching and RANSAC homography. More robust to rotation and scale changes. |
| `auto` | Tries template matching first; falls back to feature matching if confidence is below threshold. |

### Output

For each target video, a `.motiontracker.json` file is generated containing:
- Matched object positions (adjusted rectangles and points)
- Ruler, section, and ROI copied from the reference settings

### Examples

```bash
# Match regions to all videos in the same folder
motiontracker match reference.mp4

# Preview matches without writing files
motiontracker match reference.mp4 --dry-run

# Match to specific target videos
motiontracker match reference.mp4 video2.mp4 video3.mp4

# Match to videos in another directory
motiontracker match reference.mp4 ./other_experiments/

# Use feature matching with lower threshold
motiontracker match reference.mp4 --method feature --threshold 0.5

# Use a specific frame from reference and targets
motiontracker match reference.mp4 --frame 100 --target-frame 50

# Overwrite existing settings
motiontracker match reference.mp4 --overwrite
```

---

## Typical Workflow

```bash
# 1. Open a video in the GUI, set tracking points/regions and ruler
motiontracker gui

# 2. Save settings (GUI: File > Save Settings)
#    Creates: reference.mp4.motiontracker.json

# 3. Auto-match regions to all other videos in the folder
motiontracker match reference.mp4

# 4. Batch process all matched videos
motiontracker batch ./experiment/

# 5. Results: CSV files alongside each video
```

---

## Supported Video Formats

`.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.dcm`, `.dicom`
