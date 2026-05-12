# Copyright 2022 Kristof Floch

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import os
import argparse

# Ensure local source code is used instead of installed package
_src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)


def MotionTracker():
    from PyQt5.QtWidgets import QApplication, QSplashScreen
    from MotionTrackerBeta.widgets.gui import VideoWidget
    from PyQt5.QtGui import QPixmap

    # create app
    App = QApplication(sys.argv)

    # splash screen for loading
    splash = QSplashScreen(QPixmap(os.path.dirname(__file__)+"/images/logo.svg"))
    splash.show()
    App.processEvents()

    # open application
    root = VideoWidget()
    root.show()

    # close splash
    splash.finish(root)
    sys.exit(App.exec())


def main():
    parser = argparse.ArgumentParser(
        prog="motiontracker",
        description="MotionTracker - Motion tracking and analysis",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("gui", help="Launch the GUI (default)")

    batch_parser = subparsers.add_parser("batch", help="Batch process videos")
    batch_parser.add_argument(
        "videos", nargs="+",
        help="Video files or directories to process",
    )
    batch_parser.add_argument(
        "--tracker", default="CSRT",
        choices=["CSRT", "BOOSTING", "MIL", "KCF", "TLD", "MEDIANFLOW", "MOSSE"],
        help="Tracking algorithm (default: CSRT)",
    )
    batch_parser.add_argument(
        "--size-tracking", action="store_true",
        help="Enable size change tracking",
    )
    batch_parser.add_argument(
        "--fps", type=int, default=None,
        help="Override video FPS (default: use video's FPS)",
    )
    batch_parser.add_argument(
        "--diff-algo", default="First Order Finite Difference",
        help="Differentiation algorithm name (default: 'First Order Finite Difference')",
    )
    batch_parser.add_argument(
        "--diff-params", default=None,
        help="Comma-separated algorithm parameters (e.g., '3,15,15')",
    )
    batch_parser.add_argument(
        "--diff-options", default=None,
        help="JSON string of algorithm options dict",
    )
    batch_parser.add_argument(
        "--optimize", action="store_true",
        help="Use optimization-based differentiation",
    )
    batch_parser.add_argument(
        "--unit", default="pix", choices=["pix", "mm", "m"],
        help="Output unit (default: pix). mm/m require ruler in settings.",
    )

    args = parser.parse_args()

    if args.command == "batch":
        from MotionTrackerBeta.batch import run_batch
        run_batch(args)
    else:
        MotionTracker()


# run the application
if __name__ == "__main__":
    main()
