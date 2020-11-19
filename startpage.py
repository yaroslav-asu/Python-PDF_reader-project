import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QApplication, QPushButton, QFileDialog
import pdfbrowser
import filesmanager

sys._excepthook = sys.excepthook


class MainWindow(QMainWindow):
    SelectFileButton: QPushButton
    OpenNewFileButton: QPushButton
    uploaded_files_page: QMainWindow
    open_pdf_browser: QMainWindow

    def __init__(self):
        super().__init__()
        uic.loadUi("C:/Python Projects/Pdf reader/startpage.ui", self)
        self.SelectFileButton.clicked.connect(self.SelectFile)
        self.OpenNewFileButton.clicked.connect(self.OpenNewFile)

    def SelectFile(self):
        self.uploaded_files_page = filesmanager.PdfFilesManager()
        self.uploaded_files_page.show()
        self.close()

    def OpenNewFile(self):
        link_to_file = QFileDialog.getOpenFileName(self, 'Open file', '', 'Файл Pdf (*pdf)')[0]
        self.open_pdf_browser = pdfbrowser.PdfBrowser(link_to_file)
        self.open_pdf_browser.show()
        self.close()


def my_exception_hook(exctype, value, traceback):
    print(exctype, value, traceback)
    sys._excepthook(exctype, value, traceback)
    sys.exit(1)


if __name__ == '__main__':
    sys.argv.append('--remote-debugging-port=5008')
    sys.excepthook = my_exception_hook
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())