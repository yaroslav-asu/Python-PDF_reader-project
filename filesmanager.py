import sqlite3
import pdfbrowser
import showgroupselements
from functools import partial
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QMessageBox, QFileDialog
from PyQt5 import QtCore


class InterfaceTracks:
    """
    Класс содержащий переменные для пользования программой
    """
    file_name_in_label: str
    bookmark_page_interface: int
    group_id: str
    connection: sqlite3
    cursor: sqlite3
    list_with_groups_widgets = []
    check_boxes_list = []
    check_box_unchecked_by_function = False


def clear_all_checkboxes():
    """
    Очищает все chackbox от выделения
    Вызывается при зоздании новой группы
    """
    InterfaceTracks.check_box_unchecked_by_function = True
    for checkbox in list(InterfaceTracks.check_boxes_list):
        checkbox.setChecked(False)
    InterfaceTracks.check_box_unchecked_by_function = False


def clear_layout(layout):
    """
    Очищает все объекты из лэйаута
    Вызывается при нужде очистки лэйаута от объектов внутри
    :param layout: лэйаут
    """
    index = layout.count() - 1
    while index >= 0:
        widget = layout.itemAt(index).widget()
        widget.setParent(None)
        index -= 1


def is_checkbox_checked():
    """
    Проверяет выбран ли чекбокс или нет
    :return: bool выбран ли чекбокс
    """
    for checkbox in list(InterfaceTracks.check_boxes_list):
        if checkbox.isChecked():
            return True
    return False


def get_sqlite_request(request):
    """
    Выполняет запрос к БД
    Вызывается при нужде выполнения запроса к БД

    :param request: Запрос к БД
    :return: Ответ от БД
    """
    InterfaceTracks.cursor.execute(request)
    InterfaceTracks.connection.commit()
    return InterfaceTracks.cursor.fetchall()


def fill_layouts_with_widgets(parent, layouts_tuple, data_tuple, widgets, actions):
    """
    Итерируется по всем кортежам, передает их в fill_layout и тем самым заполняет все лэйауты
    виджетами с записанными в их местами для текста данными и применеными вариантами действий
    Вызывается при нужде заполнения лэйаутов

    :param parent: Родитель для дальнейшего обращения виджетами к нему
    :param layouts_tuple: Кортеж из лэйаутов
    :param data_tuple: Кортеж из текста и возможно страниц закладок, которые будут записаны в
    виджеты
    :param widgets: Кортеж виджетов, которые нужно поместить в лэйауты
    :param actions: Итерируемый объект в котором записаны действия с которыми должны быть
    объявлены виджеты
    """
    for layout, data_list, action, widget in zip(layouts_tuple, data_tuple, actions, widgets):
        for data in data_list:
            if isinstance(data, tuple):
                # Если дата - кортеж => передается текст для виджета и страница закладки
                fill_layout(parent, layout, data[0], widget, action, data[1])
            else:
                fill_layout(parent, layout, data, widget, action)


def fill_layout(parent, layout, text, widget, action, bookmark_page=0):
    """
    Заполняет переданный лэйаут переданными виджетами с записанным в них текстом
    (где нужно еще и закладками) и переданными в них видами действий при нажатии на кнопку
    Выполняется при нужде заполнения лэйаута виджетами

    :param parent: Родитель, для дальнейшего обращения к нему виджетами
    :param layout: Лэйаут для заполнения
    :param text: Текст для помещения в виджеты
    :param widget: Виджет для помещения в лэйаут
    :param action: Действие для выполнения по нажатии на кнопку
    :param bookmark_page: Страница с закладкой
    """
    InterfaceTracks.bookmark_page_interface = bookmark_page
    InterfaceTracks.file_name_in_label = text
    if not bookmark_page:
        bookmark_page = 1

    sql_insert_query = f"""Select path from FileData where file_name = '{text}'"""
    link_to_file = get_sqlite_request(sql_insert_query)

    if action == 'OpenFile' or action == 'OpenFileFromGroup' or action == 'OpenFileWithStartPage':
        if link_to_file != []:
            layout.addWidget(widget(parent, link_to_file[0], action, bookmark_page),
                             QtCore.Qt.AlignCenter)
    elif action == 'SelectFile' or action == 'DelGroup' or action == 'OpenGroup':
        layout.addWidget(widget(parent, text, action),
                         QtCore.Qt.AlignCenter)


class PdfFilesManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # TODO разбить на функции
        uic.loadUi('uploadedfiles.ui', self)
        InterfaceTracks.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        InterfaceTracks.cursor = InterfaceTracks.connection.cursor()

        sql_insert_query = """delete from Groups where group_name = ''"""
        InterfaceTracks.cursor.execute(sql_insert_query)

        self.CreateGroupButton.clicked.connect(self.create_group_button_action)
        for action in [self.upload_new_file, partial(self.update_layouts,
                                                     [self.OpenedFilesHLayout, self.select_widgets_layout])]:
            self.uploadFileButton.clicked.connect(action)

        sql_insert_query = """insert into Groups (group_name) values ('')"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        sql_insert_query = """select id from Groups where group_name = ''"""
        InterfaceTracks.group_id = get_sqlite_request(sql_insert_query)[0][0]

        sql_insert_query = """Select file_name from FileData where file_name is not '' 
                              and file_name is not null"""
        uploaded_files_data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
            sql_insert_query)))))
        uploaded_files_data = list(filter(lambda x: 'pdf' in x.split('.')[1], uploaded_files_data))
        uploaded_files_layout = self.OpenedFilesHLayout

        sql_insert_query = """Select FileData.file_name, page from Bookmarks join FileData on 
        FileData.id = Bookmarks.file_name order by FIleData.file_name"""
        bookmarks_data = get_sqlite_request(sql_insert_query)
        bookmarks_layout = self.BookmarksHLayout

        delete_groups_layout = self.delete_groups_layout

        sql_insert_query = """Select Groups.group_name from Groups where group_name != '' order 
        by group_name"""
        groups_data = list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query)))

        open_groups_layout = self.GroupsHLayout

        sql_insert_query = """Select FileData.file_name from FileData where file_name is not '' 
        and file_name is not null"""
        data4 = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
            sql_insert_query)))))
        select_widget_layout = self.select_widgets_layout

        self.layouts_tuple = (
            select_widget_layout, uploaded_files_layout, bookmarks_layout, delete_groups_layout,
            open_groups_layout)
        self.data_tuple = (data4, uploaded_files_data, bookmarks_data) + (groups_data,) * 2
        self.actions_tuple = (
            'SelectFile', 'OpenFile', 'OpenFileWithStartPage', 'DelGroup', 'OpenGroup')
        self.widgets = (SelectFile,) + (WidgetWithButton,) * 4
        fill_layouts_with_widgets(self, self.layouts_tuple, self.data_tuple,
                                  self.widgets, self.actions_tuple)

        self.group_name = None

    def upload_new_file(self):
        link_to_file = QFileDialog.getOpenFileName(self, 'Open file', '', 'Файл Pdf (*pdf)')[0]

        file_name = self.get_file_name(link_to_file)
        sqlite_insert_query = f"""select file_name from FileData where file_name = '{file_name}'"""
        InterfaceTracks.cursor.execute(sqlite_insert_query)
        sqlite_request = InterfaceTracks.cursor.fetchone()
        if sqlite_request != None:
            QMessageBox.critical(self, "Ошибка ", "Данный файл уже был загружен \nОн не будет "
                                                  "загружен",
                                 QMessageBox.Ok)
            return
        sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
        data_tuple = (
            file_name, link_to_file)
        InterfaceTracks.cursor.execute(sqlite_insert_query, data_tuple)
        InterfaceTracks.connection.commit()

    def get_file_name(self, link):
        return link.split('/')[-1]

    def create_group_button_action(self):
        """
        Проверяет правильность названия группы и выбраны ли какие то файлы для группы, если все
        хорошо, создает группу
        Вызывается при нажатии на кнопку создания группы
        """
        InterfaceTracks.connection.commit()
        self.group_name = self.group_name_line_edit.text()

        if self.group_name == '':
            clear_all_checkboxes()
            QMessageBox.critical(self, "Ошибка ", "Введите название группы",
                                 QMessageBox.Ok)
            return
        if not is_checkbox_checked():
            QMessageBox.critical(self, "Ошибка ", "Выберете хотя бы один файл",
                                 QMessageBox.Ok)
            return
        clear_all_checkboxes()
        sql_insert_query = f"""Select group_name from Groups where group_name = 
'{self.group_name}' """
        is_group_name_already_taken = get_sqlite_request(sql_insert_query) != []

        if is_group_name_already_taken:
            QMessageBox.critical(self, "Ошибка ", f'Группа "{self.group_name}" уже существует',
                                 QMessageBox.Ok)
        else:
            self.group_name_line_edit.setText('')
            QMessageBox.information(self, "Оповещение ", "Группа успешно создана",
                                    QMessageBox.Ok)
            self.create_group()

    def create_group(self):
        """
        Переименовывает последнюю группу с названием '' в название группы, так же создает новую
        группу с названием '' для привязки к ее id файлов
        Вызывается после нажатия на кнопку создания группы из функции create_group_button_action
        """

        sql_insert_query = f"""Update Groups set group_name = '{self.group_name}' where id = '{
        InterfaceTracks.group_id}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()
        sql_insert_query = """insert into Groups (group_name) values ('')"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.group_id += 1
        self.update_layouts([self.GroupsHLayout, self.delete_groups_layout])

    def delete_group(self, group_name):
        """
        Отвечает за удаление группы
        :param group_name: Название группы которую нужно удалить
        """
        sql_insert_query = f"""Delete from Groups where main.Groups.group_name = '{group_name}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()
        self.update_layouts((self.delete_groups_layout, self.GroupsHLayout))

    def update_layouts(self, layouts):
        """
        Отвечает за обновление лэйаутов, переданных в функцию
        Вызывается при нужде обновить лэйаут

        :param layouts: итерируемый объект с лэйаутами
        """
        for layout in layouts:
            clear_layout(layout)
            widget = WidgetWithButton
            if layout == self.delete_groups_layout or layout == self.GroupsHLayout:
                sql_insert_query = """Select Groups.group_name from Groups where group_name != '' order
                                    by group_name"""
                data = list(map(lambda x: x[0], get_sqlite_request(
                    sql_insert_query)))
                if layout == self.GroupsHLayout:
                    action = 'OpenGroup'
                else:
                    action = 'DelGroup'

            elif layout == self.OpenedFilesHLayout:
                sql_insert_query = """Select file_name from FileData where file_name is 
                                      not '' and file_name is not null"""
                data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
                    sql_insert_query)))))
                data = list(
                    filter(lambda x: 'pdf' in x.split('.')[1], data))
                action = "OpenFile"

            elif layout == self.BookmarksHLayout:
                sql_insert_query = """Select FileData.file_name, page from Bookmarks join FileData on 
        FileData.id = Bookmarks.file_name order by FileData.file_name"""
                data = get_sqlite_request(sql_insert_query)
                action = "OpenFileWithStartPage"
                # InterfaceTracks.bookmark_page_interface =
            elif layout == self.select_widgets_layout:
                widget = SelectFile
                sql_insert_query = """Select file_name from FileData where file_name is 
                                                      not '' and file_name is not null"""
                data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
                    sql_insert_query)))))
                data = list(
                    filter(lambda x: 'pdf' in x.split('.')[1], data))
                action = 'SelectFile'

            InterfaceTracks.check_boxes_list = set()
            fill_layouts_with_widgets(self, (layout,), (data,), (widget,),
                                      (action,))

    def closeEvent(self, event):
        """
        Выполняет закрытие соединения с БД перед закрытием окна
        :param event: событие закрытия
        """
        InterfaceTracks.connection.close()
        event.accept()


class WidgetWithButton(QWidget):
    open_pdf_browser: pdfbrowser

    def __init__(self, parent, text, action, bookmark_page=0):
        super().__init__(parent)
        uic.loadUi('opened_file_data_widget.ui', self)
        self.parent = parent
        self.start_page = bookmark_page
        self.text = text
        self.group_viewer = None
        self.setup_widget_by_action(action)
        self.file_name_label.setText(InterfaceTracks.file_name_in_label)

    def setup_widget_by_action(self, action):
        """
        Заполняет виджет в зависимости от его предназначения
        :param action: вид виджета
        """
        if action == 'OpenFile':
            self.text = self.text[0]
            self.Button.clicked.connect(self.open_file)
        elif action == 'OpenFileWithStartPage':
            self.text = self.text[0]
            self.Button.clicked.connect(self.open_file)
            self.create_bookmark_page_label(InterfaceTracks.bookmark_page_interface)
        elif action == 'OpenFileFromGroup':
            self.text = self.text[0]
            self.Button.clicked.connect(self.open_file_from_group)
        elif action == 'DelGroup':
            self.Button.clicked.connect(self.delete_group)
            self.Button.setText('Удалить')
            InterfaceTracks.list_with_groups_widgets.append(self)
        elif action == 'OpenGroup':
            self.Button.setText('Просмотреть')
            self.Button.clicked.connect(self.open_group)
            InterfaceTracks.list_with_groups_widgets.append(self)
            self.group_name = self.text

    def delete_group(self):
        self.parent.delete_group(self.text)

    def create_bookmark_page_label(self, text):
        """
        Создает строку со страницей закладки в виджете
        :param text: страница с закладкой
        """
        label = QtWidgets.QLabel()
        label.setText('Страница: ' + str(text))
        label.setAlignment(QtCore.Qt.AlignHCenter)
        self.vertical_layout.addWidget(label)

    def open_file(self):
        """
        Открывает pdf файл
        """
        try:
            self.open_pdf_browser = pdfbrowser.PdfBrowser(self.text, self.start_page,
                                                          self.parent)
            self.parent.hide()
            self.open_pdf_browser.show()
        except RuntimeError:
            QMessageBox.critical(self, "Ошибка", "Невозможно получить доступ к данному файлу",
                                 QMessageBox.Ok)
            sql_insert_query = f"""delete from FileData where path = '{self.text}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
            self.parent.update_layouts([self.parent.OpenedFilesHLayout,
                                        self.parent.BookmarksHLayout, self.parent.select_widgets_layout])

    def open_file_from_group(self):
        """открывает файл из группы"""
        self.open_pdf_browser = pdfbrowser.PdfBrowser(self.text, self.start_page,
                                                      self.parent.parent)
        self.parent.hide()
        self.open_pdf_browser.show()

    def open_group(self):
        """
        Открывает обзорщик групп
        """
        if not self.group_viewer:
            self.create_group_viewer()
        self.group_viewer.show()
        self.parent.hide()

    def create_group_viewer(self):
        """
        Создает обзорщик групп
        """
        self.group_viewer = showgroupselements.Window(self.parent)
        self.group_viewer.Group_name_label.setText(str(self.group_name))
        files_in_group_layout = (self.group_viewer.horizontalLayout,)
        sql_insert_query = f"""select file_name from main.GroupsElements join Groups G on G.id = 
GroupsElements.group_id where group_name = '{self.text}'"""
        files_in_group_data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
            sql_insert_query)))))
        fill_layouts_with_widgets(self.group_viewer, files_in_group_layout, (files_in_group_data,),
                                  (WidgetWithButton,), ('OpenFileFromGroup',))


class SelectFile(QWidget):
    def __init__(self, parent, file_name, action):
        super().__init__(parent)
        self.parent = parent

        uic.loadUi('select_file_to_create_group_widget.ui', self)
        if action == 'SelectFile':
            self.file_name = file_name
            self.file_name_label.setText(self.file_name)
            self.checkBox.stateChanged.connect(self.checkbox_handler)
            
        InterfaceTracks.check_boxes_list.append(self.checkBox)

    def checkbox_handler(self):
        """
        Обрабатывает нажатые чекбоксы
        Вызывается при изменении состояния чекбокса
        """
        if self.checkBox.checkState():
            sql_insert_query = """insert into GroupsElements (group_id, 
            file_name) values (?, 
            ?)"""
            InterfaceTracks.cursor.execute(sql_insert_query, (InterfaceTracks.group_id,
                                                              self.file_name))
            InterfaceTracks.connection.commit()
        elif not InterfaceTracks.check_box_unchecked_by_function:
            sql_insert_query = f"""delete from GroupsElements where file_name = '{self.file_name}' \
    and group_id = '{InterfaceTracks.group_id}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
