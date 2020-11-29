import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication
import filesmanager


class MainWindow(QMainWindow):
    file_manager: QMainWindow

    def __init__(self):
        super().__init__()
        uic.loadUi("uis/startpage.ui", self)
        self.SelectFileButton.clicked.connect(self.open_file_manager)

    def open_file_manager(self):
        self.file_manager = filesmanager.PdfFilesManager()
        self.file_manager.show()
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
