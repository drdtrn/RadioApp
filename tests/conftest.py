import os

# The GUI tests run headless; this must be set before pytest-qt creates the
# QApplication.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
