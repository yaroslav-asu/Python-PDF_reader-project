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
        # variables
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

        # задание ссылки на файл
        if isinstance(link_to_file, tuple):
            self.file_name = link_to_file[0].split('/')[-1]
            self.link_to_file = link_to_file[0]
        else:
            self.file_name = link_to_file.split('/')[-1]
            self.link_to_file = link_to_file

        self.get_current_file_id()
        self.put_time_data_in_bd()
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
        итерируемый объект, если раньше его не загружали"""
        sqlite_insert_query = f"""select id from FileData where file_name = '{self.file_name}' 
                and path = '{self.link_to_file}'"""
        self.cursor.execute(sqlite_insert_query)
        self.connection.commit()
        return self.cursor.fetchone()

    def set_start_page(self):
        """Получает данные из БД, выводит окно с вопросом о продолжении с последней начатой
        страницы, по получении положительного ответа записывает в стартовую страницу на которой
        в последний раз остановился пользователь"""
        sqlite_insert_query = f"""Select max(Main.id), Main.last_page from Main inner join 
        FileData on FileData.id = Main.file_name where FileData.file_name = '{self.file_name}' and 
        FileData.path = '{self.link_to_file}' and Main.last_page is not null and Main.last_page is 
        not ''"""
        self.cursor.execute(sqlite_insert_query)
        sqlite_last_page_answer = self.cursor.fetchone()
        print(sqlite_last_page_answer)

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
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage('Не указан путь к файлу!')

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

    def put_time_data_in_bd(self):
        """
        Загружает в БД время открытия файла
        """
        if self.file_name.split('.')[1] == 'pdf':
            sqlite_insert_query = f"""INSERT INTO Main (file_name, date) VALUES (?,  ?)"""
            data_tuple = (
                self.current_file_data_id,
                datetime.today().strftime('%H:%M:%S %d.%m.%Y'))
            self.cursor.execute(sqlite_insert_query, data_tuple)

    def add_bookmark(self):
        """
        Добавляет в БД данные имени и страницу закладки
        """
        sqlite_action = """Insert into Bookmarks (file_name, page) values (?, ?)"""
        data_tuple = (self.current_file_data_id, self.page_number)
        self.cursor.execute(sqlite_action, data_tuple)
        self.connection.commit()

    def del_bookmark(self):
        """
        Удаляет из БД данные о существовании закладки у файла на странице page_number
        """
        sqlite_action = f"""delete from Bookmarks where page = {self.page_number}"""
        self.cursor.execute(sqlite_action)
        self.connection.commit()

    def is_bookmark_on_page(self, page_number):
        """
        Проверяет существование закладки на переданной странице

        :param page_number: Получает страницу для проверки
        :return: Возвращает bool который отражает существание закладки в данном файле на
        page_number странице
        """
        self.bookmarks = list(self.cursor.execute(
            f"""select page from Bookmarks inner join FileData on FileData.id 
                = Bookmarks.file_name where FileData.file_name = '{self.file_name}'"""))
        if (page_number,) in self.bookmarks:
            return True
        else:
            return False

    def switch_bookmark_button_action(self):
        """
        Переключает текст кнопки, так же выполняет разные действия,
        если на странице существует или не существует страница
        Если существует: закладка удаляется
        Если нет: создается
        """
        self.switch_bookmark_button_set_text()
        if self.is_bookmark_on_page(self.page_number):
            self.del_bookmark()
        else:
            self.add_bookmark()
        self.switch_bookmark_button_set_text()

    def switch_bookmark_button_set_text(self):
        """
        Изменяет текст кнопки в зависимости от того, существует ли
        закладка на данной странице или нет
        """
        if self.is_bookmark_on_page(self.page_number):
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
        Вызывается при заканчивании редактирования поля ввода
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
        вызывается при любом изменении zoom
        при вызове в конце редактирования поля zoom, new_zoom = None
        :param current_zoom: новый zoom
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
        вызывается при нужде изменения текста в поле ввода zoom
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
                self.file_manager.show()
            else:
                filesmanager.PdfFilesManager().show()

    def closeEvent(self, event):
        """
        Выполняет все что нужно выполнить до закрытия окна
        :param event: Событие закрытия окна
        """
        sqlite_action = f"""update Main set last_page = {self.page_number} \
        where id = last_insert_rowid();"""
        self.StopAllTrigger = True
        self.cursor.execute(sqlite_action)
        self.connection.commit()
        self.connection.close()
        event.accept()
