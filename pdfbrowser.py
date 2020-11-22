import fitz
import base64
import sqlite3
import filesmanager
from functools import partial
from datetime import datetime
from inspect import getsourcefile
from os.path import abspath

from PyQt5 import QtWebEngineWidgets, QtWidgets, uic
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow, QPushButton, QMessageBox
from PyQt5.QtWidgets import QGridLayout


def get_pages(link):
    doc = fitz.open(link)
    pages_amount = doc.pageCount
    return pages_amount


def buttons_cooldown(*args):
    args[0].setEnabled(True)


class PdfBrowser(QMainWindow):
    gridLayout: QGridLayout
    pushButton: QPushButton
    # current_file_data_id_exist: list
    current_file_data_id: int
    base64data: base64
    bookmarks: list

    # var:int

    def __init__(self, link_to_file, start_page=1, file_manager=None):
        super().__init__()
        uic.loadUi("browser.ui", self)

        self.start_page = start_page

        self.pages_amount = get_pages(link_to_file)
        self.page_number = start_page
        self.page_new_number = start_page
        self.zoom = 1

        self.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        self.cursor = self.connection.cursor()

        self.file_manager = file_manager
        self.browser = QtWebEngineWidgets.QWebEngineView(self)
        self.StopAllTrigger = False

        # ----------

        self.gridLayout.addWidget(self.browser)

        self.move(250, 50)
        self.setup_widgets()

        if isinstance(link_to_file, tuple):
            self.file_name = link_to_file[0].split('/')[-1]
            self.link_to_file = link_to_file[0]
        else:
            self.file_name = link_to_file.split('/')[-1]
            self.link_to_file = link_to_file

        # self.get_current_file_id()

        self.put_start_data_in_bd()

        self.set_start_page()

        self.open_pdf_file()

        self.switch_bookmark_button_set_text()
        self.PageNumberLineEdit.setText(str(self.page_number))

    def setup_widgets(self):
        """
        Функция задает действия для кнопок, заполняет тексты полей и т.п
        """
        self.ZoomPlusButton.clicked.connect(self.zoom_plus)
        self.ZoomMinusButton.clicked.connect(self.zoom_minus)
        self.ZoomCoofLineEdit.editingFinished.connect(self.zoom_change)
        self.ZoomCoofLineEdit.setText('1')

        self.PageUpButton.clicked.connect(self.page_up)
        self.PageDownButton.clicked.connect(self.page_down)
        self.PageNumberLineEdit.editingFinished.connect(self.parse_page_number)
        self.PageNumberLineEdit.setText('1')

        self.SwitchBookmarkButton.clicked.connect(self.switch_bookmark_button_action)
        self.OpenFileManagerButton.clicked.connect(self.open_file_manager)

    def current_file_data_id_exist(self):
        """Возвращает итерируемый объект с id файла, если он ранее был загружен или же пустой
        итерируемый объект, елси раньше его не загружали"""
        sqlite_insert_query = f"""select id from FileData where file_name = '{self.file_name}' 
                and path = '{self.link_to_file}'"""
        self.cursor.execute(sqlite_insert_query)
        self.connection.commit()
        return self.cursor.fetchone()

    def set_start_page(self):
        sqlite_insert_query = f"""Select max(Main.id), Main.last_page from Main inner join 
        FileData on FileData.id = Main.file_name where FileData.file_name = '{self.file_name}' and 
        FileData.path = '{self.link_to_file}' and Main.last_page is not null and Main.last_page is 
not ''"""
        self.cursor.execute(sqlite_insert_query)
        sqlite_last_page_answer = self.cursor.fetchone()

        if self.start_page == 1:
            if sqlite_last_page_answer != (None, None) and sqlite_last_page_answer[1] != 1:
                reply = QMessageBox.question(self, 'Оповещение',
                                             "Хотите продолжить с последней открытой страницы?",
                                             QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.page_number = sqlite_last_page_answer[1]

    def open_pdf_file(self):
        if self.link_to_file:
            with open(self.link_to_file, 'rb') as file:
                self.base64data = base64.b64encode(file.read()).decode('utf-8')
                self.browser.loadFinished.connect(self.load_pdf_with_js)
        else:
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Не указан путь к файлу!')

        link_to_html = '/'.join(abspath(getsourcefile(lambda: 0)).split('\\')[:-1] + ['main.html'])
        self.browser.load(QUrl(link_to_html))

    def put_start_data_in_bd(self):
        if self.current_file_data_id_exist():
            self.current_file_data_id = self.current_file_data_id_exist()[0]
        else:
            sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
            data_tuple = (
                self.file_name, self.link_to_file)
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

    def load_pdf_with_js(self):
        self.browser.page().runJavaScript(f'let myJsVar = atob("{self.base64data}")')
        self.browser.page().runJavaScript(f'pageNumber = {self.page_number}')
        self.browser.page().runJavaScript('showPage()')
        self.browser.page().runJavaScript(
            'pdfjsLib.getDocument({data: myJsVar}).promise.then(function \
            (doc) {window.numPages '
            '= doc.numPages})')

    def add_bookmark(self):
        sqlite_action = """Insert into Bookmarks (file_name, page) values (?, ?)"""
        data_tuple = (self.current_file_data_id, self.page_number)
        self.cursor.execute(sqlite_action, data_tuple)
        self.connection.commit()

    def del_bookmark(self):
        sqlite_action = f"""delete from Bookmarks where page = {self.page_number}"""
        self.cursor.execute(sqlite_action)
        self.connection.commit()

    def is_bookmark_on_page(self, page_number):

        self.bookmarks = list(self.cursor.execute(
            f"""select page from Bookmarks inner join FileData on FileData.id 
= Bookmarks.file_name

 where FileData.file_name = '{self.file_name}'"""))
        if (page_number,) in self.bookmarks:
            return True
        else:
            return False

    def switch_bookmark_button_set_text(self):
        if self.is_bookmark_on_page(self.page_number):
            self.SwitchBookmarkButton.setText('Удалить закладку')
        else:
            self.SwitchBookmarkButton.setText('Добавить закладку')

    def switch_bookmark_button_action(self):
        if self.is_bookmark_on_page(self.page_number):
            self.switch_bookmark_button_set_text()
            self.del_bookmark()
        else:
            self.switch_bookmark_button_set_text()
            self.add_bookmark()
        self.switch_bookmark_button_set_text()

    def page_up(self):
        self.PageUpButton.setEnabled(False)
        self.page_new_number = self.page_number - 1
        self.page_change(self.page_new_number)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.PageUpButton))

    def page_down(self):
        self.PageDownButton.setEnabled(False)
        self.page_new_number = self.page_number + 1
        self.page_change(self.page_new_number)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.PageDownButton))

    def page_change(self, new_page_number):
        if self.StopAllTrigger:
            return
        if 0 < new_page_number <= self.pages_amount and new_page_number != self.page_number:
            self.page_number = new_page_number
            self.PageNumberLineEdit.setText(str(self.page_number))
            self.browser.page().runJavaScript(
                f'pageNumber = {self.page_number}')
            self.browser.page().runJavaScript(
                f'showPage()')
        self.switch_bookmark_button_set_text()

    def parse_page_number(self):
        """
        считывает номер страницы из поля ввода

        вызывается при ... что тут происходит
        """
        page_number_in_text_line = self.PageNumberLineEdit.text()
        if page_number_in_text_line.isdigit():
            page_number_in_text_line = int(page_number_in_text_line)
            if page_number_in_text_line != self.page_number and \
                self.pages_amount >= page_number_in_text_line > 0:
                self.page_change(page_number_in_text_line)
            else:
                self.PageNumberLineEdit.setText(str(self.page_number))
                self.page_change(self.page_number)
        else:
            self.page_change(self.page_number)
            self.PageNumberLineEdit.setText(str(self.page_number))

    def zoom_change(self, current_zoom=None):
        if not current_zoom:
            if self.ZoomCoofLineEdit.text().replace('.', '', 1).isdigit():
                current_zoom = float(self.ZoomCoofLineEdit.text())
            else:
                self.zoom_text_line_set_text(self.zoom)
                return

        if 0 < current_zoom <= 5 and current_zoom != self.zoom:
            self.zoom = current_zoom
            self.zoom_text_line_set_text(current_zoom)
            self.browser.page().runJavaScript(
                f'scale = {self.zoom}')
            self.browser.page().runJavaScript(
                f'showPage()')

    def zoom_text_line_set_text(self, current_zoom):
        if str(current_zoom).replace('.', '', 1).isdigit():
            if float(current_zoom).is_integer():
                self.ZoomCoofLineEdit.setText(str(int(current_zoom)))
            else:
                self.ZoomCoofLineEdit.setText(str(current_zoom))
        else:
            self.ZoomCoofLineEdit.setText(str(self.zoom))

    def zoom_plus(self):
        self.ZoomPlusButton.setEnabled(False)
        zoom_new = self.zoom + 0.5
        self.zoom_change(zoom_new)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.ZoomPlusButton))

    def zoom_minus(self):
        self.ZoomMinusButton.setEnabled(False)
        zoom_new = self.zoom - 0.5
        self.zoom_change(zoom_new)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.ZoomMinusButton))

    def open_file_manager(self):
        reply = QMessageBox.question(self, 'Оповещение',
                                     "Текущая страница просмотра закроется! \n Вы точно хотите "
                                     "продолжить? ",
                                     QMessageBox.Yes,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            if self.file_manager:
                self.file_manager.show()
            else:
                filesmanager.PdfFilesManager().show()

    def closeEvent(self, event):
        sqlite_action = f"""update Main set last_page = {self.page_number} \
        where id = last_insert_rowid();"""
        self.StopAllTrigger = True
        self.cursor.execute(sqlite_action)
        self.connection.commit()
        self.connection.close()
        event.accept()
