import base64
import sqlite3
import filesmanager
from functools import partial
from datetime import datetime

from PyQt5 import QtWebEngineWidgets, QtWidgets, uic
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow, QPushButton, QMessageBox
from PyQt5.QtWidgets import QGridLayout


class PdfBrowser(QMainWindow):
    gridLayout: QGridLayout
    pushButton: QPushButton
    # var:int

    def __init__(self, link_to_file, start_page=1, file_manager=None):
        super().__init__()
        self.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        self.cursor = self.connection.cursor()

        self.file_manager = file_manager
        uic.loadUi("C:/Python Projects/Pdf reader/browser.ui", self)
        self.browser = QtWebEngineWidgets.QWebEngineView(self)
        self.gridLayout.addWidget(self.browser)

        self.move(250, 50)

        # Variables
        self.PagesAmount = -1
        self.PageNumber = start_page
        self.Zoom = 1
        if isinstance(link_to_file, tuple):
            self.file_name = link_to_file[0].split('/')[-1]
            link_to_file = link_to_file[0]
        else:
            self.file_name = link_to_file.split('/')[-1]

        self.StopAllTrigger = False
        # ----------

        # Buttons
        self.ZoomPlusButton.clicked.connect(self.ZoomPlus)
        self.ZoomMinusButton.clicked.connect(self.ZoomMinus)
        self.ZoomCoofLineEdit.editingFinished.connect(self.ZoomChange)
        self.ZoomCoofLineEdit.setText('1')

        self.PageUpButton.clicked.connect(self.PageUp)
        self.PageDownButton.clicked.connect(self.PageDown)
        self.PageNumberLineEdit.editingFinished.connect(self.PageChange)
        self.PageNumberLineEdit.setText('1')

        self.SwitchBookmarkButton.clicked.connect(self.SwitchBookmarkButtonAction)
        self.OpenFileManagerButton.clicked.connect(self.OpenFileManager)
        # ----------

        sqlite_insert_query = f"""select id from FileData where file_name = '{self.file_name}' 
        and path = '{link_to_file}'"""
        self.cursor.execute(sqlite_insert_query)
        self.connection.commit()
        self.current_file_data_id_exist = self.cursor.fetchone()

        if self.current_file_data_id_exist:
            self.current_file_data_id = self.current_file_data_id_exist[0]
        else:
            sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
            data_tuple = (
                self.file_name, link_to_file)
            self.cursor.execute(sqlite_insert_query, data_tuple)

            sqlite_insert_query = """Select max(id) from FileData"""
            self.cursor.execute(sqlite_insert_query)
            self.connection.commit()
            self.current_file_data_id = self.cursor.fetchone()[0]
        if self.file_name.split('.')[1] == 'pdf':
            sqlite_insert_query = f"""INSERT INTO Main (file_name, date) VALUES (?,  ?)"""
            data_tuple = (
                self.current_file_data_id,
                datetime.today().strftime('%H:%M:%S %d.%m.%Y'))
            self.cursor.execute(sqlite_insert_query, data_tuple)

        """select  max(Main.id), FileData.file_name from """
        sqlite_insert_query = f"""Select max(Main.id), Main.last_page from Main inner join 
FileData on 
FileData.id = Main.file_name
        where FileData.file_name = '{self.file_name}' and FileData.path = '{link_to_file}' and 
Main.last_page 
is not 
null and Main.last_page is not ''"""
        self.cursor.execute(sqlite_insert_query)
        sqlite_last_page_answer = self.cursor.fetchone()

        if start_page == 1:
            if sqlite_last_page_answer != (None, None) and sqlite_last_page_answer[1] != 1:
                reply = QMessageBox.question(self, 'Оповещение',
                                             "Хотите продолжить с последней открытой страницы?",
                                             QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.PageNumber = sqlite_last_page_answer[1]

        # ----------

        if link_to_file:
            with open(link_to_file, 'rb') as file:
                self.base64data = base64.b64encode(file.read()).decode('utf-8')
                self.browser.loadFinished.connect(self.LoadPdfWithJS)
        else:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Не указан путь к файлу!')
        self.browser.load(QUrl('C:/Python Projects/Pdf reader/main.html'))

        self.SwitchBookmarkButtonSetText()
        self.PageNumberLineEdit.setText(str(self.PageNumber))

    def LoadPdfWithJS(self):
        self.browser.page().runJavaScript(f'let myJsVar = atob("{self.base64data}")')
        self.browser.page().runJavaScript(f'pageNumber = {self.PageNumber}')
        self.browser.page().runJavaScript('showPage()')
        self.browser.page().runJavaScript(
            'pdfjsLib.getDocument({data: myJsVar}).promise.then(function \
            (doc) {window.numPages '
            '= doc.numPages})')

    def AddBookmark(self):
        sqlite_action = """Insert into Bookmarks (file_name, page) values (?, ?)"""
        data_tuple = (self.current_file_data_id, self.PageNumber)
        self.cursor.execute(sqlite_action, data_tuple)
        self.connection.commit()

    def DelBookmark(self):
        sqlite_action = f"""delete from Bookmarks where page = {self.PageNumber}"""
        self.cursor.execute(sqlite_action)
        self.connection.commit()

    def IsBookmarkOnPage(self, PageNumber):

        self.bookmarks = list(self.cursor.execute(
            f"""select page from Bookmarks inner join FileData on FileData.id 
= Bookmarks.file_name

 where FileData.file_name = '{self.file_name}'"""))
        if (PageNumber,) in self.bookmarks:
            return True
        else:
            return False

    def SwitchBookmarkButtonSetText(self):
        if self.IsBookmarkOnPage(self.PageNumber):
            self.SwitchBookmarkButton.setText('Удалить закладку')
        else:
            self.SwitchBookmarkButton.setText('Добавить закладку')

    def SwitchBookmarkButtonAction(self):
        if self.IsBookmarkOnPage(self.PageNumber):
            self.SwitchBookmarkButtonSetText()
            self.DelBookmark()
        else:
            self.SwitchBookmarkButtonSetText()
            self.AddBookmark()
        self.SwitchBookmarkButtonSetText()

    def PageUp(self):
        self.PageUpButton.setEnabled(False)
        self.PageNewNumber = self.PageNumber - 1
        self.browser.page().runJavaScript(
            'window.numPages', self.PageChange)
        self.browser.page().runJavaScript(
            '', partial(self.ButtonsColdown, self.PageUpButton))

    def PageDown(self):
        self.PageDownButton.setEnabled(False)
        self.PageNewNumber = self.PageNumber + 1
        self.browser.page().runJavaScript(
            'window.numPages', self.PageChange)
        self.browser.page().runJavaScript(
            '', partial(self.ButtonsColdown, self.PageDownButton))

    def PageChange(self, PagesAmount=None):
        if self.StopAllTrigger:
            return
        if self.PagesAmount == -1 and PagesAmount == None:
            self.browser.page().runJavaScript(
                'window.numPages', self.PageChange)
        elif self.PagesAmount == -1:
            self.PagesAmount = PagesAmount

        if PagesAmount == None:
            # parse page number
            self.parse_page_number()

        if 0 < self.PageNewNumber <= self.PagesAmount and self.PageNewNumber != self.PageNumber:
            self.PageNumber = self.PageNewNumber
            self.PageNumberLineEdit.setText(str(self.PageNumber))
            self.browser.page().runJavaScript(
                f'pageNumber = {self.PageNumber}')
            self.browser.page().runJavaScript(
                f'showPage()')
        self.SwitchBookmarkButtonSetText()

    def parse_page_number(self):
        """
        считывает номер страницы из поля ввода

        вызывается при ... что тут происходит
        """
        PageNumberInTextLine = self.PageNumberLineEdit.text()
        if PageNumberInTextLine.isdigit():
            if int(PageNumberInTextLine) != self.PageNumber and \
                self.PagesAmount >= int(PageNumberInTextLine) > 0:
                self.PageNewNumber = int(self.PageNumberLineEdit.text())
            else:
                self.PageNumberLineEdit.setText(str(self.PageNumber))
                self.PageNewNumber = self.PageNumber
        else:
            self.PageNewNumber = self.PageNumber
            self.PageNumberLineEdit.setText(str(self.PageNumber))

    def ZoomChange(self, CurrentZoom=None):
        if CurrentZoom == None:
            if self.ZoomCoofLineEdit.text().replace('.', '', 1).isdigit():
                CurrentZoom = float(self.ZoomCoofLineEdit.text())
            else:
                self.ZoomTextLineSetText(self.Zoom)
                return

        if 0 < CurrentZoom <= 5 and CurrentZoom != self.Zoom:
            self.Zoom = CurrentZoom
            self.ZoomTextLineSetText(CurrentZoom)
            self.browser.page().runJavaScript(
                f'scale = {self.Zoom}')
            self.browser.page().runJavaScript(
                f'showPage()')

    def ZoomTextLineSetText(self, CurrentZoom):
        if str(CurrentZoom).replace('.', '', 1).isdigit():
            if float(CurrentZoom).is_integer():
                self.ZoomCoofLineEdit.setText(str(int(CurrentZoom)))
            else:
                self.ZoomCoofLineEdit.setText(str(CurrentZoom))
        else:
            self.ZoomCoofLineEdit.setText(str(self.Zoom))

    def ZoomPlus(self):
        self.ZoomPlusButton.setEnabled(False)
        ZoomNew = self.Zoom + 0.5
        self.ZoomChange(ZoomNew)
        self.browser.page().runJavaScript(
            '', partial(self.ButtonsColdown, self.ZoomPlusButton))

    def ZoomMinus(self):
        self.ZoomMinusButton.setEnabled(False)
        ZoomNew = self.Zoom - 0.5
        self.ZoomChange(ZoomNew)
        self.browser.page().runJavaScript(
            '', partial(self.ButtonsColdown, self.ZoomMinusButton))

    def ButtonsColdown(self, *args):
        args[0].setEnabled(True)

    def OpenFileManager(self):
        reply = QMessageBox.question(self, 'Оповещение',
                                     "Текущая страница просмотра закроется! \n Вы точно хотите "
                                     "продолжить? ",
                                     QMessageBox.Yes,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            print(self.file_manager)
            if self.file_manager:
                self.file_manager.show()
            else:
                self.a = filesmanager.PdfFilesManager()
                self.a.show()

    def closeEvent(self, event):
        sqlite_action = f"""update Main set last_page = {self.PageNumber} \
        where id = last_insert_rowid();"""
        self.StopAllTrigger = True
        self.cursor.execute(sqlite_action)
        self.connection.commit()
        # self.connection.close()
        event.accept()