import sqlite3


class InterfaceTracks:
    """
    Класс содержащий переменные для пользования программой
    """
    file_name_in_label: str
    bookmark_page_interface: int
    group_id: str
    file_manager: object
    connection = sqlite3.connect("Pdf_reader_db.sqlite")
    cursor = connection.cursor()
    list_with_groups_widgets = []
    check_boxes_list = set()
    block_checkbox = False