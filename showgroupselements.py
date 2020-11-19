from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow


class Window(QMainWindow):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        uic.loadUi("C:/Python Projects/Pdf reader/Groups_elements.ui", self)
        self.backButton.clicked.connect(self.back_to_manager)

    def back_to_manager(self):
        self.parent.show()
        self.hide()
