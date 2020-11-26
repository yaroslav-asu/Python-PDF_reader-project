from datetime import datetime

from interface_tracks import InterfaceTracks


class SqliteRequest:
    def __init__(self):
        self.cursor = InterfaceTracks.cursor
        self.connection = InterfaceTracks.connection

    def get_sqlite_request(self, request):
        """
        Выполняет запрос к БД

        :param request: Запрос к БД
        :return: Ответ от БД
        """
        self.cursor.execute(request)
        self.connection.commit()
        return self.cursor.fetchall()

    def get_link_to_file(self, text):
        sql_insert_query = f"""Select path from FileData where file_name = '{text}'"""
        return self.get_sqlite_request(sql_insert_query)

    def get_groups_names(self):
        sql_insert_query = """Select distinct group_name from Groups join main.GroupsElements on
                              Groups.id = group_id join FileData FD on
                              GroupsElements.file_name = FD.file_name
                              where group_name != '' order by group_name"""
        data = list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query)))
        return data

    def get_uploaded_file_names(self):
        sql_insert_query = """Select distinct file_name from FileData where file_name is 
                              not '' and file_name is not null order by file_name"""
        data = list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query)))
        data = list(
            filter(lambda x: 'pdf' in x.split('.')[1], data))
        return data

    def get_file_names_and_pages(self):
        sql_insert_query = """Select FileData.file_name, page from Bookmarks join FileData on 
                              FileData.id = Bookmarks.file_name order by FileData.file_name"""
        data = self.get_sqlite_request(sql_insert_query)
        return data

    def get_file_names(self):
        sql_insert_query = """Select file_name from FileData where file_name is 
                              not '' and file_name is not null order by file_name"""
        data = sorted(list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query))))
        data = list(
            filter(lambda x: 'pdf' in x.split('.')[1], data))
        return data

    def get_group_id(self):
        sql_insert_query = """insert into Groups (group_name) values ('')"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        sql_insert_query = """select id from Groups where group_name = ''"""
        InterfaceTracks.group_id = self.get_sqlite_request(sql_insert_query)[0][0]

    @staticmethod
    def delete_group_with_none_name():
        sql_insert_query = """delete from Groups where group_name = ''"""
        InterfaceTracks.cursor.execute(sql_insert_query)

    def get_uploaded_files_data(self):
        """
        Получение из БД имен загруженных файлов
        """
        sql_insert_query = """Select distinct file_name from FileData where file_name is not '' 
                                  and file_name is not null order by file_name"""
        uploaded_files_data = sorted(list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query))))
        return list(filter(lambda x: 'pdf' in x.split('.')[1], uploaded_files_data))

    def get_bookmarks_data(self):
        """
        Получение из БД данных на каких страницах закладки и имен файлов с закладками
        """
        sql_insert_query = """Select distinct FileData.file_name, page from Bookmarks join 
                              FileData on FileData.id = Bookmarks.file_name order by 
                              FIleData.file_name"""
        return list(self.get_sqlite_request(sql_insert_query))

    def get_bookmarks_data(self):
        """
        Получение из БД данных на каких страницах закладки и имен файлов с закладками
        """
        sql_insert_query = """Select distinct FileData.file_name, page from Bookmarks join 
                              FileData on FileData.id = Bookmarks.file_name order by 
                              FIleData.file_name"""
        return list(self.get_sqlite_request(sql_insert_query))

    def get_groups_data(self):
        """
        Получение из БД названий групп
        """
        sql_insert_query = """Select distinct group_name from Groups join main.GroupsElements on
                              Groups.id = group_id join FileData FD on GroupsElements.file_name = 
                              FD.file_name where group_name != '' order by group_name"""
        return list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query)))

    def get_select_widget_data(self):
        """
        Получение из БД данных имен виджетов для select_widget
        """
        sql_insert_query = """Select distinct FileData.file_name from FileData where file_name is 
                              not '' and file_name is not null order by FileData.file_name"""
        return sorted(list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query))))

    @staticmethod
    def get_file_name(file_name):
        sqlite_insert_query = f"""select file_name from FileData where file_name = '{file_name}'"""
        InterfaceTracks.cursor.execute(sqlite_insert_query)
        return InterfaceTracks.cursor.fetchone()

    @staticmethod
    def insert_file_name_and_path_into_db(file_name, link_to_file):
        sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
        data_tuple = (
            file_name, link_to_file)
        InterfaceTracks.cursor.execute(sqlite_insert_query, data_tuple)
        InterfaceTracks.connection.commit()

    def get_group_names_for_delete(self):
        sql_insert_query = """select group_name from Groups where id not in (select group_id from 
                              GroupsElements join FileData FD on GroupsElements.file_name = 
                              FD.file_name) and group_name is not ''"""
        return self.get_sqlite_request(sql_insert_query)

    def is_group_name_already_taken(self, group_name):
        sql_insert_query = f"""Select group_name from Groups join GroupsElements GE on Groups.id = 
                               GE.group_id where group_name = '{group_name}'"""
        return self.get_sqlite_request(sql_insert_query) != []

    @staticmethod
    def create_group(group_name):
        """
        Переименовывает последнюю группу с названием '' в название группы, так же создает новую
        группу с названием '' для привязки к ее id файлов
        Вызывается после нажатия на кнопку создания группы из функции create_group_button_action
        """

        sql_insert_query = f"""Update Groups set group_name = '{group_name}' where id = '{
        InterfaceTracks.group_id}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()
        sql_insert_query = """insert into Groups (group_name) values ('')"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.group_id += 1

    @staticmethod
    def delete_groups(parent, group_names):
        """
        Отвечает за удаление группы
        :param parent: объект файл менеджера для обращения к нему
        :param group_names: Массив кортежей с именами групп для удаления
        """
        for group_name_tuple in group_names:
            group_name = group_name_tuple[0]
            sql_insert_query = f"""Delete from Groups where main.Groups.group_name = 
                                   '{group_name}'"""
            InterfaceTracks.cursor.execute(sql_insert_query)
            InterfaceTracks.connection.commit()
            parent.update_layouts(parent, (parent.delete_groups_layout, parent.GroupsHLayout))

    @staticmethod
    def delete_file_from_db(text):
        sql_insert_query = f"""delete from FileData where path = '{text}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()

    def get_group_elements(self, text):
        sql_insert_query = f"""select distinct file_name from main.GroupsElements join Groups G on 
                             G.id = GroupsElements.group_id where group_name = '{text}' 
                             order by file_name"""
        return sorted(list(map(lambda x: x[0], self.get_sqlite_request(
            sql_insert_query))))

    @staticmethod
    def insert_group_element(file_name):
        sql_insert_query = """insert into GroupsElements (group_id, 
                                          file_name) values (?, ?)"""
        InterfaceTracks.cursor.execute(sql_insert_query, (InterfaceTracks.group_id,
                                                          file_name))
        InterfaceTracks.connection.commit()

    @staticmethod
    def delete_group_element(file_name):
        sql_insert_query = f"""delete from GroupsElements where file_name = '{file_name}' \
                                           and group_id = '{InterfaceTracks.group_id}'"""
        InterfaceTracks.cursor.execute(sql_insert_query)
        InterfaceTracks.connection.commit()

    def get_current_file_data(self, file_name, link_to_file):
        """Возвращает итерируемый объект с id файла, если он ранее был загружен или же none,
        если раньше его не загружали"""
        sqlite_insert_query = f"""select id from FileData where file_name = '{file_name}' 
                and path = '{link_to_file}'"""
        self.cursor.execute(sqlite_insert_query)
        self.connection.commit()
        return self.cursor.fetchone()

    def insert_file_name_path_into_db(self, file_name, link_to_file):
        sqlite_insert_query = f"""INSERT INTO FileData (file_name, path) VALUES (?, ?)"""
        data_tuple = (
            file_name, link_to_file)
        self.cursor.execute(sqlite_insert_query, data_tuple)

    def get_current_file_data_id(self):
        sqlite_insert_query = """Select max(id) from FileData"""
        self.cursor.execute(sqlite_insert_query)
        self.connection.commit()
        return self.cursor.fetchone()[0]

    def put_time_data_in_bd(self, file_name, current_file_data_id):
        """
        Загружает в БД время открытия файла
        """
        if file_name.split('.')[1] == 'pdf':
            sqlite_insert_query = f"""INSERT INTO Main (file_name, date) VALUES (?,  ?)"""
            data_tuple = (
                current_file_data_id,
                datetime.today().strftime('%H:%M:%S %d.%m.%Y'))
            self.cursor.execute(sqlite_insert_query, data_tuple)

    def add_bookmark(self, current_file_data_id, page_number):
        """
        Добавляет в БД данные имени и страницу закладки
        """
        sqlite_action = """Insert into Bookmarks (file_name, page) values (?, ?)"""
        data_tuple = (current_file_data_id, page_number)
        self.cursor.execute(sqlite_action, data_tuple)
        self.connection.commit()

    def del_bookmark(self, page_number):
        """
        Удаляет из БД данные о существовании закладки у файла на странице page_number
        """
        sqlite_action = f"""delete from Bookmarks where page = {page_number}"""
        self.cursor.execute(sqlite_action)
        self.connection.commit()

    def is_bookmark_on_page(self, page_number, file_name):
        """
        Проверяет существование закладки на переданной странице

        :param file_name: название файла
        :param page_number: Получает страницу для проверки
        :return: Возвращает bool который отражает существание закладки в данном файле на
        page_number странице
        """
        bookmarks = list(self.cursor.execute(
            f"""select page from Bookmarks inner join FileData on FileData.id 
                = Bookmarks.file_name where FileData.file_name = '{file_name}'"""))
        if (page_number,) in bookmarks:
            return True
        else:
            return False

    def set_last_opened_page_to_file(self, page_number):
        sqlite_action = f"""update Main set last_page = {page_number} \
                                    where id = last_insert_rowid();"""
        self.cursor.execute(sqlite_action)
