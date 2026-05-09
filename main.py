"""Program entry point.

The GUI code lives in gui.py. This file stays tiny so it is obvious where the
program starts when someone opens the project.
"""

from gui import MemoryAllocationApp


def main() -> None:
    """Start the memory allocation simulator."""

    MemoryAllocationApp().run()


if __name__ == "__main__":
    main()
