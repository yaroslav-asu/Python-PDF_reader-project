import fitz
import base64
import sqlite3
import filesmanager
from sql_requests import SqliteRequest
from functools import partial
from inspect import getsourcefile
from os.path import abspath

from PyQt5 import QtWebEngineWidgets, uic
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QMainWindow, QPushButton, QMessageBox
from PyQt5.QtWidgets import QGridLayout


def get_pages_amount(link):
    doc = fitz.open(link)
    pages_amount = doc.pageCount
    return pages_amount


def buttons_cooldown(*args):
    args[0].setEnabled(True)


class PdfBrowser(QMainWindow):
    current_file_data_id_exist: list
    gridLayout: QGridLayout
    pushButton: QPushButton
    current_file_data_id: int
    base64data: base64
    bookmarks: list

    def __init__(self, link_to_file, start_page=1, file_manager=None):
        super().__init__()

        # variables
        self.start_page = start_page
        self.file_manager = file_manager
        self.pages_amount = get_pages_amount(link_to_file)

        uic.loadUi("uis/browser.ui", self)
        self.page_number = start_page
        self.page_new_number = start_page
        self.zoom = 1

        self.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        self.cursor = self.connection.cursor()

        self.browser = QtWebEngineWidgets.QWebEngineView(self)
        self.StopAllTrigger = False
        # ----------

        self.gridLayout.addWidget(self.browser)

        self.move(250, 50)
        self.setup_widgets()

        # задание ссылки на файл
        if isinstance(link_to_file, tuple):
            self.file_name = link_to_file[0].split('/')[-1]
            self.link_to_file = link_to_file[0]
        else:
            self.file_name = link_to_file.split('/')[-1]
            self.link_to_file = link_to_file

        self.get_current_file_id()
        SqliteRequest().put_time_data_in_bd(self.file_name, self.current_file_data_id)
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

    def set_start_page(self):
        """Получает данные из БД, выводит окно с вопросом о продолжении с последней начатой
        страницы, по получении положительного ответа записывает в стартовую страницу на которой
        в последний раз остановился пользователь"""
        sqlite_last_page_answer = SqliteRequest().get_start_page(self.file_name, self.link_to_file)

        if self.start_page == 1 and sqlite_last_page_answer:
            if sqlite_last_page_answer != (None, None) and sqlite_last_page_answer[1] != 1:
                reply = QMessageBox.question(self, 'Оповещение',
                                             "Хотите продолжить с последней открытой страницы?",
                                             QMessageBox.Yes,
                                             QMessageBox.No)
                if reply == QMessageBox.Yes:
                    self.page_number = sqlite_last_page_answer[1]

    def open_pdf_file(self):
        """Перерабатывает файл в base64 и загружает его через load_pdf_with_js.
           Так же подгружает html файл в js"""
        if self.link_to_file:
            with open(self.link_to_file, 'rb') as file:
                self.base64data = base64.b64encode(file.read()).decode('utf-8')
                self.browser.loadFinished.connect(self.load_pdf_with_js)
        else:
            QMessageBox.critical(self, "Ошибка ", f'Файл по этому пути не может быть получен',
                                 QMessageBox.Ok)
            return

        link_to_html = '/'.join(abspath(getsourcefile(lambda: 0)).split('\\')[:-1] + ['main.html'])
        self.browser.load(QUrl(link_to_html))

    def load_pdf_with_js(self):
        """
        Передает все нужные данные в js и загружает файл
        """
        self.browser.page().runJavaScript(f'let myJsVar = atob("{self.base64data}")')
        self.browser.page().runJavaScript(f'pageNumber = {self.page_number}')
        self.browser.page().runJavaScript('showPage()')
        self.browser.page().runJavaScript(
            'pdfjsLib.getDocument({data: myJsVar}).promise.then(function \
            (doc) {window.numPages '
            '= doc.numPages})')

    def get_current_file_id(self):
        """
        Если файл раньше уже загружался через программу, получает id файла из БД и записывает в
        переменную,
        иначе загружает в БД имя и путь файла и так же записывает id в переменную
        """
        self.current_file_data_id_exist = SqliteRequest().get_current_file_data(self.file_name,
                                                                                self.link_to_file)

        if self.current_file_data_id_exist:
            self.current_file_data_id = self.current_file_data_id_exist[0]
        else:
            SqliteRequest().insert_file_name_path_into_db(self.file_name, self.link_to_file)

            self.current_file_data_id = SqliteRequest().get_current_file_data_id()

    def switch_bookmark_button_action(self):
        """
        Переключает текст кнопки, так же выполняет разные действия,
        если на странице существует или не существует страница
        Если существует: закладка удаляется
        Если нет: создается
        """
        self.switch_bookmark_button_set_text()
        if SqliteRequest().is_bookmark_on_page(self.page_number, self.file_name):
            SqliteRequest().del_bookmark(self.page_number)
        else:
            SqliteRequest().add_bookmark(self.current_file_data_id, self.page_number)
        self.switch_bookmark_button_set_text()

    def switch_bookmark_button_set_text(self):
        """
        Изменяет текст кнопки в зависимости от того, существует ли
        закладка на данной странице или нет
        """
        if SqliteRequest().is_bookmark_on_page(self.page_number, self.file_name):
            self.SwitchBookmarkButton.setText('Удалить закладку')
        else:
            self.SwitchBookmarkButton.setText('Добавить закладку')

    def page_up(self):
        """
        Поднимает страницу на одну
        Так же выключает кнопку на время загрузки новой страницы и включает после
        """
        self.PageUpButton.setEnabled(False)
        self.page_new_number = self.page_number - 1
        self.page_change(self.page_new_number)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.PageUpButton))
        # Коллбэк позволяет выполнить функцию после загрузки страницы

    def page_down(self):
        """
        Опускает страницу на одну
        Так же выключает кнопку на время загрузки новой страницы и включает после
        """
        self.PageDownButton.setEnabled(False)
        self.page_new_number = self.page_number + 1
        self.page_change(self.page_new_number)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.PageDownButton))
        # Коллбэк позволяет выполнить функцию после загрузки страницы

    def page_change(self, new_page_number):
        """
        Изменяет текущую страницу на переданную, при выполнении всех условий
        :param new_page_number:  новая страница
        """
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
        Получает номер страницы из поля ввода
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

    def zoom_change(self, new_zoom=None):
        """
        Изменяет текущий zoom на переданный, при условии, что он подходит
        при вызове в конце редактирования поля zoom, new_zoom = None
        :param new_zoom: новый zoom
        """
        if not new_zoom:
            if self.ZoomCoofLineEdit.text().replace('.', '', 1).isdigit():
                new_zoom = float(self.ZoomCoofLineEdit.text())
            else:
                self.zoom_text_line_set_text(self.zoom)
                return

        if 0 < new_zoom <= 6 and new_zoom != self.zoom:
            self.zoom = new_zoom
            self.zoom_text_line_set_text(new_zoom)
            self.browser.page().runJavaScript(
                f'scale = {self.zoom}')
            self.browser.page().runJavaScript(
                f'showPage()')

    def zoom_text_line_set_text(self, current_zoom):
        """
        Задает текст для поля ввода zoom при его изменении, либо
        :param current_zoom: текущий зум
        """
        if str(current_zoom).replace('.', '', 1).isdigit():
            if float(current_zoom).is_integer():
                self.ZoomCoofLineEdit.setText(str(int(current_zoom)))
            else:
                self.ZoomCoofLineEdit.setText(str(current_zoom))
        else:
            self.ZoomCoofLineEdit.setText(str(self.zoom))

    def zoom_plus(self):
        """
        Увеличивает zoom на 0.5
        Так же выключает кнопку на время применения zoom'a и включает после
        """
        self.ZoomPlusButton.setEnabled(False)
        zoom_new = self.zoom + 0.5
        self.zoom_change(zoom_new)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.ZoomPlusButton))
        # Коллбэк позволяет выполнить функцию после загрузки применения zoom'a

    def zoom_minus(self):
        """
        Уменьшает zoom на 0.5
        Так же выключает кнопку на время применения zoom'a и включает после
        """
        self.ZoomMinusButton.setEnabled(False)
        zoom_new = self.zoom - 0.5
        self.zoom_change(zoom_new)
        self.browser.page().runJavaScript(
            '', partial(buttons_cooldown, self.ZoomMinusButton))
        # Коллбэк позволяет выполнить функцию после загрузки применения zoom'a

    def open_file_manager(self):
        """
        Оповещает о закрытии окна, после отображает менеджер
        """
        reply = QMessageBox.question(self, 'Оповещение',
                                     "Текущая окно просмотра закроется! \n Вы точно хотите "
                                     "продолжить? ",
                                     QMessageBox.Yes,
                                     QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            if self.file_manager:
                filesmanager.update_layouts(self.file_manager, [self.file_manager.BookmarksHLayout])
                self.file_manager.show()
            else:
                filesmanager.PdfFilesManager().show()

    def closeEvent(self, event):
        """
        Выполняет все что нужно выполнить до закрытия окна
        :param event: Событие закрытия окна
        """
        SqliteRequest().set_last_opened_page_to_file(self.page_number)
        self.StopAllTrigger = True
        self.connection.commit()
        self.connection.close()
        event.accept()
