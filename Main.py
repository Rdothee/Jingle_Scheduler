"""
Main.py  —  Application entry point.

Launches the CustomTkinter GUI. The headless scheduler logic is now
fully contained in the backend package and orchestrated by ui/app.py.
"""

import sys
import os

# Ensure the project root is on the path when launched from any cwd
sys.path.insert(0, os.path.dirname(__file__))

from ui.app import App


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
