import sqlite3
import pdfbrowser
import showgroupselements
from functools import partial
from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QMessageBox
from PyQt5 import QtCore


class InterfaceTracks:
    file_name_in_label = None
    bookmark_page_global = None
    group_id = None
    connection = None
    cursor = None
    list_with_groups_widgets = []
    check_boxes_list = []
    check_box_unchecked_by_function = False


def clear_all_checkboxes():
    InterfaceTracks.check_box_unchecked_by_function = True
    for checkbox in InterfaceTracks.check_boxes_list:
        checkbox.setChecked(False)
    InterfaceTracks.check_box_unchecked_by_function = False


def is_checkbox_checked():
    for checkbox in InterfaceTracks.check_boxes_list:
        if checkbox.isChecked():
            return True
    return False


def get_sqlite_request(request):
    InterfaceTracks.cursor.execute(request)
    InterfaceTracks.connection.commit()
    return InterfaceTracks.cursor.fetchall()


def fill_layouts_with_widgets(parent, layouts_tuple, data_tuple, widgets, actions):
    for layout, data_list, action, widget in zip(layouts_tuple, data_tuple, actions, widgets):
        for data in data_list:
            if isinstance(data, tuple):
                fill_layout(parent, layout, data[0], widget, action, data[1])
            else:
                fill_layout(parent, layout, data, widget, action)


def fill_layout(parent, layout, text, widget, action, bookmark_page=0):
    InterfaceTracks.bookmark_page_global = bookmark_page
    InterfaceTracks.file_name_in_label = text
    if not bookmark_page:
        bookmark_page = 1

    sql_insert_query = f"""Select path from FileData where file_name = '{text}'"""
    link_to_file = get_sqlite_request(sql_insert_query)

    if action == 'OpenFile':
        layout.addWidget(widget(parent, link_to_file[0], action, bookmark_page),
                         QtCore.Qt.AlignCenter)
    elif action == 'OpenFileWithStartPage':
        layout.addWidget(widget(parent, link_to_file[0], action, bookmark_page),
                         QtCore.Qt.AlignCenter)
    elif action == 'OpenFileFromGroup':
        layout.addWidget(widget(parent, link_to_file[0], action, bookmark_page),
                         QtCore.Qt.AlignCenter)
    elif action == 'SelectFile':
        layout.addWidget(widget(parent, text, action),
                         QtCore.Qt.AlignCenter)
    elif action == 'DelGroup':
        layout.addWidget(widget(parent, text, action),
                         QtCore.Qt.AlignCenter)
    elif action == 'OpenGroup':
        layout.addWidget(widget(parent, text, action),
                         QtCore.Qt.AlignCenter)


class PdfFilesManager(QMainWindow):
    def __init__(self):
        super().__init__()
        # TODO разбить на функции
        uic.loadUi('C:/Python Projects/Pdf reader/uploadedfiles.ui', self)
        InterfaceTracks.connection = sqlite3.connect("Pdf_reader_db.sqlite")
        InterfaceTracks.cursor = InterfaceTracks.connection.cursor()

        sql_insert_query = """delete from Groups where group_name = ''"""
        InterfaceTracks.cursor.execute(sql_insert_query)

        self.CreateGroupButton.clicked.connect(self.create_group_button_action)
        self.uploadFileButton.clicked.connect(partial(self.update_layouts, self.OpenedFilesHLayout))

        sql_insert_query = """insert into Groups (group_name) values ('')"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        sql_insert_query = """select id from Groups where group_name = ''"""
        InterfaceTracks.group_id = get_sqlite_request(sql_insert_query)[0][0]

        sql_insert_query = """Select FileData.file_name from Main join FileData on FileData.id = 
        Main.file_name where 
        FileData.file_name is 
        not '' and 
        FileData.file_name 
        is not null"""
        uploaded_files_data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
            sql_insert_query)))))
        uploaded_files_data = list(filter(lambda x: 'pdf' in x.split('.')[1], uploaded_files_data))
        uploaded_files_layout = self.OpenedFilesHLayout

        sql_insert_query = """Select FileData.file_name, page from Bookmarks join FileData on 
        FileData.id = Bookmarks.file_name"""
        bookmarks_data = get_sqlite_request(sql_insert_query)
        bookmarks_layout = self.BookmarksHLayout

        delete_groups_layout = self.delete_groups_layout

        sql_insert_query = """Select Groups.group_name from Groups where group_name != '' order 
        by group_name"""
        groups_data = list(map(lambda x: x[0], get_sqlite_request(
            sql_insert_query)))

        open_groups_layout = self.GroupsHLayout

        sql_insert_query = """Select FileData.file_name from Main join FileData on
                        FileData.id = Main.file_name"""
        data4 = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
            sql_insert_query)))))
        layout4 = self.select_widgets_layout

        self.layouts_tuple = (
            layout4, uploaded_files_layout, bookmarks_layout, delete_groups_layout,
            open_groups_layout)
        self.data_tuple = (data4, uploaded_files_data, bookmarks_data) + (groups_data,) * 2
        self.actions_tuple = (
            'SelectFile', 'OpenFile', 'OpenFileWithStartPage', 'DelGroup', 'OpenGroup')
        self.widgets = (SelectFile,) + (WidgetWithButton,) * 4
        fill_layouts_with_widgets(self, self.layouts_tuple, self.data_tuple,
                                  self.widgets, self.actions_tuple)

        self.group_name = None

    def create_group_button_action(self):
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
            QMessageBox.information(self, "Оповещение ", "Группа успешно создана",
                                    QMessageBox.Ok)
            sql_insert_query = f"""Update Groups set group_name = '{self.group_name}' where id = '{
            InterfaceTracks.group_id}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
            sql_insert_query = """insert into Groups (group_name) values ('')"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.group_id += 1
            self.update_layouts(self.GroupsHLayout)

    def delete_group(self, group_name):
        sql_insert_query = f"""Delete from Groups where main.Groups.group_name = '{group_name}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()
        self.update_layouts(self.delete_groups_layout)

    def update_layouts(self, layout):
        index = layout.count() - 1
        while (index >= 0):
            widget = layout.itemAt(index).widget()
            widget.setParent(None)
            index -= 1
        widget = WidgetWithButton
        if layout == self.delete_groups_layout or layout == self.GroupsHLayout:
            sql_insert_query = """Select Groups.group_name from Groups where group_name != '' order
                                by group_name"""
            data = list(map(lambda x: x[0], get_sqlite_request(
                sql_insert_query)))
            action = 'DelGroup'
            if layout == self.GroupsHLayout:
                action = 'OpenGroup'
        elif layout == self.OpenedFilesHLayout:
            sql_insert_query = """Select FileData.file_name from Main join FileData on FileData.id = 
                    Main.file_name where 
                    FileData.file_name is 
                    not '' and 
                    FileData.file_name 
                    is not null"""
            data = sorted(list(map(lambda x: x[0], set(get_sqlite_request(
                sql_insert_query)))))
            data = list(
                filter(lambda x: 'pdf' in x.split('.')[1], data))
            action = "OpenFile"

        fill_layouts_with_widgets(self, (layout,), (data,), (widget,),
                                  (action,))

    def closeEvent(self, event):
        # InterfaceTracks.connection.close()
        event.accept()


class WidgetWithButton(QWidget):
    def __init__(self, parent, text, action, bookmark_page=0):
        super().__init__(parent)
        uic.loadUi('C:/Python Projects/Pdf reader/opened_file_data_widget.ui', self)
        self.parent = parent
        self.start_page = bookmark_page
        self.text = text
        self.open_pdf_browser = None
        self.group_viewer = None
        if action == 'OpenFile':
            self.text = text[0]
            self.Button.clicked.connect(self.open_file)
        elif action == 'OpenFileWithStartPage':
            self.text = text[0]
            self.Button.clicked.connect(self.open_file)
            self.create_bookmark_page_label(InterfaceTracks.bookmark_page_global)
        elif action == 'OpenFileFromGroup':
            self.text = text[0]
            self.Button.clicked.connect(self.open_file_from_group)
        elif action == 'DelGroup':
            self.Button.clicked.connect(self.delete_group)
            self.Button.setText('Удалить')
            InterfaceTracks.list_with_groups_widgets.append(self)
        elif action == 'OpenGroup':
            self.Button.setText('Просмотреть')
            self.Button.clicked.connect(self.open_group)
            InterfaceTracks.list_with_groups_widgets.append(self)
            self.group_name = text

        self.file_name_label.setText(InterfaceTracks.file_name_in_label)

    def delete_group(self):
        self.parent.delete_group(self.text)

    def create_bookmark_page_label(self, text):
        label = QtWidgets.QLabel()
        label.setText('Страница: ' + str(text))
        self.vertical_layout.addWidget(label)

    def open_file(self):
        self.open_pdf_browser = pdfbrowser.PdfBrowser(self.text, self.start_page,
                                                      self.parent)
        self.parent.hide()
        self.open_pdf_browser.show()

    def open_file_from_group(self):
        self.open_pdf_browser = pdfbrowser.PdfBrowser(self.text, self.start_page,
                                                      self.parent.parent)
        self.parent.hide()
        self.open_pdf_browser.show()

    def open_group(self):
        if not self.group_viewer:
            self.create_group_viewer()
        self.group_viewer.show()
        self.parent.hide()

    def create_group_viewer(self):
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

        uic.loadUi('C:/Python Projects/Pdf reader/select_file_to_create_group_widget.ui', self)
        if action == 'SelectFile':
            self.file_name = file_name
            self.file_name_label.setText(self.file_name)
            self.checkBox.stateChanged.connect(self.checkbox_handler)
        InterfaceTracks.check_boxes_list.append(self.checkBox)

    def checkbox_handler(self):
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
