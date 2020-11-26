import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QFileDialog
import pdfbrowser
import filesmanager


class MainWindow(QMainWindow):
    SelectFileButton: QPushButton
    OpenNewFileButton: QPushButton
    uploaded_files_page: QMainWindow
    open_pdf_browser: QMainWindow

    def __init__(self):
        super().__init__()
        uic.loadUi("startpage.ui", self)
        self.SelectFileButton.clicked.connect(self.select_file)
        self.OpenNewFileButton.clicked.connect(self.open_new_file)

    def select_file(self):
        self.uploaded_files_page = filesmanager.PdfFilesManager()
        self.uploaded_files_page.show()
        self.close()

    def open_new_file(self):
        link_to_file = QFileDialog.getOpenFileName(self, 'Open file', '', 'Файл Pdf (*pdf)')[0]
        self.open_pdf_browser = pdfbrowser.PdfBrowser(link_to_file)
        self.open_pdf_browser.show()
        self.close()


if __name__ == '__main__':
    sys.argv.append('--remote-debugging-port=5008')
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
