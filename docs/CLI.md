# Command-Line Interface Reference

MotionTracker provides a CLI for launching the GUI and batch processing videos.

```
motiontracker <command> [options]
```

---

## Commands

| Command | Description |
|---------|-------------|
| `gui`   | Launch the graphical interface (default if no command given) |
| `batch` | Process multiple videos headlessly |

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

Settings files can be created via the GUI (Save Settings button).

---

## Typical Workflow

```bash
# 1. Open a video in the GUI, set tracking points/regions and ruler
motiontracker gui

# 2. Save settings (GUI: File > Save Settings)
#    Creates: reference.mp4.motiontracker.json

# 3. Batch process videos
motiontracker batch ./experiment/

# 4. Results: CSV files alongside each video
```

---

## Supported Video Formats

`.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.flv`, `.webm`, `.dcm`, `.dicom`
