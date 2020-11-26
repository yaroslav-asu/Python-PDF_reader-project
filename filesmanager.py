import sqlite3
import pdfbrowser
import showgroupselements
import sql_requests
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
    file_manager: object
    connection: sqlite3
    cursor: sqlite3
    list_with_groups_widgets = []
    check_boxes_list = set()
    block_checkbox = False


def clear_all_checkboxes():
    """
    Очищает все checkbox от выделения
    Вызывается при зоздании новой группы
    """
    InterfaceTracks.block_checkbox = True
    for checkbox in list(InterfaceTracks.check_boxes_list):
        checkbox.setChecked(False)
    InterfaceTracks.block_checkbox = False


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
        widget.close()
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
            layout.addWidget(widget(parent, InterfaceTracks.file_manager, link_to_file[0], action,
                                    bookmark_page),
                             QtCore.Qt.AlignCenter)
    elif action == 'SelectFile' or action == 'DelGroup' or action == 'OpenGroup':
        layout.addWidget(widget(parent, InterfaceTracks.file_manager, text, action),
                         QtCore.Qt.AlignCenter)


def update_layouts(file_manager, layouts):
    """
    Отвечает за обновление лэйаутов, переданных в функцию
    Вызывается при нужде обновить лэйаут

    :param file_manager: Объект файл менеджера
    :param layouts: итерируемый объект с лэйаутами
    """
    for layout in layouts:
        clear_layout(layout)
        widget = WidgetWithButton
        if layout == file_manager.delete_groups_layout or layout == file_manager.GroupsHLayout:

            sql_insert_query = """Select distinct group_name from Groups join main.GroupsElements on
                                          Groups.id = group_id join FileData FD on
                                          GroupsElements.file_name = FD.file_name
                                          where group_name != '' order by group_name"""
            data = list(map(lambda x: x[0], get_sqlite_request(
                sql_insert_query)))

            if layout == file_manager.GroupsHLayout:
                action = 'OpenGroup'
            else:
                action = 'DelGroup'

        elif layout == file_manager.OpenedFilesHLayout:
            sql_insert_query = """Select distinct file_name from FileData where file_name is 
                                  not '' and file_name is not null order by file_name"""
            data = list(map(lambda x: x[0], get_sqlite_request(
                sql_insert_query)))
            data = list(
                filter(lambda x: 'pdf' in x.split('.')[1], data))
            action = "OpenFile"

        elif layout == file_manager.BookmarksHLayout:
            sql_insert_query = """Select FileData.file_name, page from Bookmarks join FileData on 
                                  FileData.id = Bookmarks.file_name order by FileData.file_name"""
            data = get_sqlite_request(sql_insert_query)
            action = "OpenFileWithStartPage"
        elif layout == file_manager.select_widgets_layout:
            widget = SelectFile
            sql_insert_query = """Select file_name from FileData where file_name is 
                                  not '' and file_name is not null order by file_name"""
            data = sorted(list(map(lambda x: x[0], get_sqlite_request(
                sql_insert_query))))
            data = list(
                filter(lambda x: 'pdf' in x.split('.')[1], data))
            action = 'SelectFile'

        fill_layouts_with_widgets(file_manager, (layout,), (data,), (widget,),
                                  (action,))


def get_group_id():
    sql_insert_query = """insert into Groups (group_name) values ('')"""
    InterfaceTracks.cursor.execute(sql_insert_query)
    sql_insert_query = """select id from Groups where group_name = ''"""
    InterfaceTracks.group_id = get_sqlite_request(sql_insert_query)[0][0]


def get_file_name(link):
    return link.split('/')[-1]


class PdfFilesManager(QMainWindow):
    uploaded_files_data: list
    bookmarks_data: list
    groups_data: list
    select_widget_data: list

    def __init__(self):
        super().__init__()
        uic.loadUi('uploadedfiles.ui', self)
        InterfaceTracks.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        InterfaceTracks.cursor = InterfaceTracks.connection.cursor()
        InterfaceTracks.file_manager = self
        sql_insert_query = """delete from Groups where group_name = ''"""
        InterfaceTracks.cursor.execute(sql_insert_query)

        self.CreateGroupButton.clicked.connect(self.create_group_button_action)
        for action in [self.upload_new_file, partial(update_layouts,
                                                     self, [self.OpenedFilesHLayout,
                                                            self.select_widgets_layout])]:
            self.uploadFileButton.clicked.connect(action)

        get_group_id()
        self.get_uploaded_files_data()
        self.get_bookmarks_data()
        self.get_select_widget_data()
        self.get_groups_data()

        layouts_tuple = (
            self.select_widgets_layout, self.OpenedFilesHLayout, self.BookmarksHLayout,
            self.delete_groups_layout, self.GroupsHLayout)
        data_tuple = (self.select_widget_data, self.uploaded_files_data, self.bookmarks_data) + (
            self.groups_data,) * 2
        actions_tuple = (
            'SelectFile', 'OpenFile', 'OpenFileWithStartPage', 'DelGroup', 'OpenGroup')
        widgets = (SelectFile,) + (WidgetWithButton,) * 4
        fill_layouts_with_widgets(self, layouts_tuple, data_tuple,
                                  widgets, actions_tuple)

        self.group_name = None

    def get_uploaded_files_data(self):
        """
        Получение из БД имен загруженных файлов
        """
        sql_insert_query = """Select distinct file_name from FileData where file_name is not '' 
                              and file_name is not null order by file_name"""
        uploaded_files_data = sorted(list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query))))
        self.uploaded_files_data = list(filter(lambda x: 'pdf' in x.split('.')[1],
                                               uploaded_files_data))

    def get_bookmarks_data(self):
        """
        Получение из БД данных на каких страницах закладки и имен файлов с закладками
        """
        sql_insert_query = """Select distinct FileData.file_name, page from Bookmarks join 
                              FileData on FileData.id = Bookmarks.file_name order by 
                              FIleData.file_name"""
        self.bookmarks_data = list(get_sqlite_request(sql_insert_query))

    def get_groups_data(self):
        """
        Получение из БД названий групп
        """
        sql_insert_query = """Select distinct group_name from Groups join main.GroupsElements on
                              Groups.id = group_id join FileData FD on GroupsElements.file_name = 
                              FD.file_name where group_name != '' order by group_name"""
        self.groups_data = list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query)))

    def get_select_widget_data(self):
        """
        Получение из БД данных имен виджетов для select_widget
        """
        sql_insert_query = """Select distinct FileData.file_name from FileData where file_name is 
                              not '' and file_name is not null order by FileData.file_name"""
        self.select_widget_data = sorted(list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query))))

    def upload_new_file(self):
        """
        Загрузка нового файла
        """
        link_to_file = QFileDialog.getOpenFileName(self, 'Open file', '', 'Файл Pdf (*pdf)')[0]

        file_name = get_file_name(link_to_file)
        sqlite_insert_query = f"""select file_name from FileData where file_name = '{file_name}'"""
        InterfaceTracks.cursor.execute(sqlite_insert_query)
        sqlite_request = InterfaceTracks.cursor.fetchone()
        if sqlite_request:
            QMessageBox.critical(self, "Ошибка ", "Данный файл уже был загружен \nОн не будет "
                                                  "загружен",
                                 QMessageBox.Ok)
            return
        sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
        data_tuple = (
            file_name, link_to_file)
        InterfaceTracks.cursor.execute(sqlite_insert_query, data_tuple)
        InterfaceTracks.connection.commit()

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

        sql_insert_query = """select group_name from Groups where id not in (select group_id from 
                              GroupsElements join FileData FD on GroupsElements.file_name = 
                              FD.file_name) and group_name is not ''"""
        self.delete_groups(get_sqlite_request(sql_insert_query))

        sql_insert_query = f"""Select group_name from Groups join GroupsElements GE on Groups.id = 
                               GE.group_id where group_name = '{self.group_name}'"""
        is_group_name_already_taken = get_sqlite_request(sql_insert_query) != []

        if is_group_name_already_taken:
            QMessageBox.critical(self, "Ошибка ", f'Группа "{self.group_name}" уже существует',
                                 QMessageBox.Ok)
        else:
            self.group_name_line_edit.setText('')
            QMessageBox.information(self, "Оповещение ", "Группа успешно создана",
                                    QMessageBox.Ok)
            self.create_group()
            update_layouts(self, [self.GroupsHLayout, self.delete_groups_layout])

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

    def delete_groups(self, group_names):
        """
        Отвечает за удаление группы
        :param group_names: Массив кортежей с именами групп для удаления
        """
        for group_name_tuple in group_names:
            group_name = group_name_tuple[0]
            sql_insert_query = f"""Delete from Groups where main.Groups.group_name = 
                                   '{group_name}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
            update_layouts(self, (self.delete_groups_layout, self.GroupsHLayout))

    def closeEvent(self, event):
        """
        Выполняет закрытие соединения с БД перед закрытием окна
        :param event: событие закрытия
        """
        InterfaceTracks.connection.close()
        event.accept()


class WidgetWithButton(QWidget):
    """
    Виджет для открытия файлов, групп; удаления групп и т.п (виджет с кнопкой)
    """
    open_pdf_browser: pdfbrowser
    group_name: str

    def __init__(self, parent, file_manager, text, action, bookmark_page=0):
        super().__init__(parent)
        uic.loadUi('opened_file_data_widget.ui', self)
        self.parent = parent
        self.file_manager = file_manager
        self.start_page = bookmark_page
        self.text = text
        self.group_viewer = None
        self.setup_widget_by_action(action)
        self.file_name_label.setText(str(InterfaceTracks.file_name_in_label))

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
            self.Button.clicked.connect(partial(self.file_manager.delete_groups, [(self.text,)]))
            self.Button.setText('Удалить')
            InterfaceTracks.list_with_groups_widgets.append(self)
        elif action == 'OpenGroup':
            self.Button.setText('Просмотреть')
            self.Button.clicked.connect(self.open_group)
            InterfaceTracks.list_with_groups_widgets.append(self)
            self.group_name = self.text

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
            update_layouts(self.file_manager, [self.file_manager.OpenedFilesHLayout,
                                               self.file_manager.BookmarksHLayout,
                                               self.file_manager.select_widgets_layout])

    def open_file_from_group(self):
        """открывает файл из группы"""
        try:
            self.open_pdf_browser = pdfbrowser.PdfBrowser(self.text, self.start_page,
                                                          self.parent.parent)
            self.parent.hide()
            self.open_pdf_browser.show()
        except RuntimeError:
            QMessageBox.critical(self, "Ошибка", "Невозможно получить доступ к данному файлу",
                                 QMessageBox.Ok)
            sql_insert_query = f"""delete from FileData where path = '{self.text}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
            update_layouts(self.file_manager, [self.file_manager.OpenedFilesHLayout,
                                               self.file_manager.BookmarksHLayout,
                                               self.file_manager.select_widgets_layout,
                                               self.file_manager.GroupsHLayout])
            self.close()

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
        sql_insert_query = f"""select distinct file_name from main.GroupsElements join Groups G on 
                               G.id = GroupsElements.group_id where group_name = '{self.text}' 
                               order by file_name"""
        files_in_group_data = sorted(list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query))))
        fill_layouts_with_widgets(self.group_viewer, files_in_group_layout, (files_in_group_data,),
                                  (WidgetWithButton,), ('OpenFileFromGroup',))


class SelectFile(QWidget):
    """
    Виджет применяется для выбора файлов (Виджет с галочкой)
    """
    def __init__(self, parent, file_manager, file_name, action):
        super().__init__(parent)
        self.parent = parent
        self.file_manager = file_manager
        uic.loadUi('select_file_to_create_group_widget.ui', self)
        if action == 'SelectFile':
            self.file_name = file_name
            self.file_name_label.setText(self.file_name)
            self.checkBox.stateChanged.connect(self.checkbox_handler)
        InterfaceTracks.check_boxes_list.add(self.checkBox)

    def checkbox_handler(self):
        """
        Обрабатывает нажатые чекбоксы
        Вызывается при изменении состояния чекбокса
        """
        if self.checkBox.checkState():
            sql_insert_query = """insert into GroupsElements (group_id, 
                                  file_name) values (?, ?)"""
            InterfaceTracks.cursor.execute(sql_insert_query, (InterfaceTracks.group_id,
                                                              self.file_name))
            InterfaceTracks.connection.commit()
        elif not InterfaceTracks.block_checkbox:
            sql_insert_query = f"""delete from GroupsElements where file_name = '{self.file_name}' \
                                   and group_id = '{InterfaceTracks.group_id}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()

    def closeEvent(self, event):
        InterfaceTracks.check_boxes_list.remove(self.checkBox)
        event.accept()
