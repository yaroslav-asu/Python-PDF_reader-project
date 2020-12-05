import sqlite3
import pdfbrowser
import showgroupselements
from interface_tracks import InterfaceTracks
from sql_requests import SqliteRequest
from functools import partial
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QMessageBox, QFileDialog
from PyQt5 import QtCore


def clear_all_checkboxes():
    """
    Очищает все checkbox от выделения
    """
    InterfaceTracks.block_checkbox = True
    for checkbox in list(InterfaceTracks.check_boxes_list):
        checkbox.setChecked(False)
    InterfaceTracks.block_checkbox = False


def clear_layout(layout):
    """
    Очищает все объекты из лэйаута
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

    link_to_file = SqliteRequest().get_link_to_file(text)

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

    :param file_manager: Объект файл менеджера
    :param layouts: итерируемый объект с лэйаутами
    """
    for layout in layouts:
        clear_layout(layout)
        widget = WidgetWithButton
        if layout == file_manager.delete_groups_layout or layout == file_manager.GroupsHLayout:
            data = SqliteRequest().get_groups_names()
            if layout == file_manager.GroupsHLayout:
                action = 'OpenGroup'
            else:
                action = 'DelGroup'
        elif layout == file_manager.OpenedFilesHLayout:
            data = SqliteRequest().get_uploaded_file_names()
            action = "OpenFile"
        elif layout == file_manager.BookmarksHLayout:
            data = SqliteRequest().get_file_names_and_pages()
            action = "OpenFileWithStartPage"
        elif layout == file_manager.select_widgets_layout:
            widget = SelectFile
            data = SqliteRequest().get_file_names()
            action = 'SelectFile'

        fill_layouts_with_widgets(file_manager, (layout,), (data,), (widget,),
                                  (action,))


def get_file_name(link):
    return link.split('/')[-1]


def delete_groups(parent, group_names):
    """
    Отвечает за удаление групп, подающихся на вход
    :param parent: объект файл менеджера для обращения к нему
    :param group_names: Массив кортежей с именами групп для удаления
    """
    for group_name_tuple in group_names:
        group_name = group_name_tuple[0]
        SqliteRequest().delete_group(group_name)
        update_layouts(parent, (parent.delete_groups_layout, parent.GroupsHLayout))


class PdfFilesManager(QMainWindow):
    uploaded_files_data: list
    bookmarks_data: list
    groups_data: list
    select_widget_data: list

    def __init__(self):
        super().__init__()
        uic.loadUi('uis/file_manager.ui', self)
        InterfaceTracks.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        InterfaceTracks.cursor = InterfaceTracks.connection.cursor()
        InterfaceTracks.file_manager = self
        SqliteRequest().delete_group_with_none_name()

        self.CreateGroupButton.clicked.connect(self.create_group_button_action)
        for action in [self.upload_new_file, partial(update_layouts,
                                                     self, [self.OpenedFilesHLayout,
                                                            self.select_widgets_layout])]:
            self.uploadFileButton.clicked.connect(action)

        SqliteRequest().get_group_id()
        self.uploaded_files_data = SqliteRequest().get_uploaded_files_data()
        self.bookmarks_data = SqliteRequest().get_bookmarks_data()
        self.select_widget_data = SqliteRequest().get_select_widget_data()
        self.groups_data = SqliteRequest().get_groups_data()

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

    def upload_new_file(self):
        """
        Загрузка новых файлов
        """
        message_showed = False
        links_to_files = \
            QFileDialog.getOpenFileNames(self, 'Upload file(s)', '', 'Файл Pdf (*pdf)')[0]
        for link_to_file in links_to_files:
            file_name = get_file_name(link_to_file)
            sqlite_request = SqliteRequest().get_file_name(file_name)
            if sqlite_request and not message_showed:
                QMessageBox.critical(self, "Ошибка ", "Среди выбранных вами файлов есть уже "
                                                      "загруженные, они не будут загружены",
                                     QMessageBox.Ok)
                message_showed = True
            elif not sqlite_request:
                SqliteRequest().insert_file_name_and_path_into_db(file_name, link_to_file)

    def create_group_button_action(self):
        """
        Проверяет правильность названия группы и выбраны ли какие то файлы для группы, если все
        хорошо, создает группу
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

        delete_groups(self, SqliteRequest().get_group_names_for_delete())
        is_group_name_already_taken = SqliteRequest().is_group_name_already_taken(self.group_name)

        if is_group_name_already_taken:
            QMessageBox.critical(self, "Ошибка ", f'Группа "{self.group_name}" уже существует',
                                 QMessageBox.Ok)
        else:
            self.group_name_line_edit.setText('')
            QMessageBox.information(self, "Оповещение ", "Группа успешно создана",
                                    QMessageBox.Ok)
            SqliteRequest().create_group(self.group_name)
            update_layouts(self, [self.GroupsHLayout, self.delete_groups_layout])

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
        uic.loadUi('uis/opened_file_data_widget.ui', self)
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
            self.Button.clicked.connect(partial(delete_groups, self.file_manager,
                                                [(self.text,)]))
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
            QMessageBox.critical(self, "Ошибка", "Файл был перемещен или удален.",
                                 QMessageBox.Ok)
            SqliteRequest().delete_file_from_db(self.text)
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
        files_in_group_data = SqliteRequest().get_group_elements(self.text)

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
        uic.loadUi('uis/select_file_to_create_group_widget.ui', self)
        if action == 'SelectFile':
            self.file_name = file_name
            self.file_name_label.setText(self.file_name)
            self.checkBox.stateChanged.connect(self.checkbox_handler)
        InterfaceTracks.check_boxes_list.add(self.checkBox)

    def checkbox_handler(self):
        """
        Обрабатывает нажатые чекбоксы
        """
        if self.checkBox.checkState():
            SqliteRequest().insert_group_element(self.file_name)
        elif not InterfaceTracks.block_checkbox:
            SqliteRequest().delete_group_element(self.file_name)

    def closeEvent(self, event):
        InterfaceTracks.check_boxes_list.remove(self.checkBox)
        event.accept()
