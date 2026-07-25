import sys
import threading

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from desktop.window import MainWindow


def start_gui():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("Jarvis")
        app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()

    return app, window
