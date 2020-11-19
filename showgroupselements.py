import base64
import sys
import traceback

sys._excepthook = sys.excepthook

from PyQt5 import QtWebEngineWidgets, QtWidgets, uic, QtGui
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow, QApplication, QSizePolicy, QPushButton, QFileDialog
from PyQt5.QtWidgets import QGridLayout

import pdfbrowser
import filesmanager


class Window(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        uic.loadUi("C:/Python Projects/Pdf reader/Groups_elements.ui", self)
        self.backButton.clicked.connect(self.back_to_manager)

    def back_to_manager(self):
        self.parent.show()
        self.hide()