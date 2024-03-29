import os
import sqlite3
from copy import copy
from datetime import datetime, date

from kivy import kivy_home_dir

from migrations import STATEMENTS


class SQLiteStore:
    def __init__(self):
        self.conn = sqlite3.connect(os.path.join(kivy_home_dir, 'kivypraying.sqlite3'))
        for statement in STATEMENTS:
            try:
                c = self.conn.cursor()
                c.execute(statement)
                self.conn.commit()
            except Exception as e:
                pass

    @staticmethod
    def _fetch_attr_clause(model, **kwargs):
        where_clause = []

        prep = {}
        for key, value in kwargs.items():
            key_parts = key.split("__", 1)
            field = key_parts[0]
            ext = ''.join(key_parts[1:])

            prep[field] = {"value": value, "ext": ext}

        for key, attr_type in model.__annotations__.items():
            if key not in prep:
                continue

            value = prep.get(key, {}).get("value")
            ext = prep.get(key, {}).get("ext")

            if value is None:
                where_clause.append(f"{key} is null")
                continue
            elif attr_type in (date, datetime, str):
                value = f"'{value}'"
            elif attr_type == bool:
                value = bool(value)

            if ext == "ne":
                where_clause.append(f'{key}<>{value}')
            else:
                where_clause.append(f'{key}={value}')

        if not where_clause:
            where_clause = ['1=1']

        return where_clause

    def retrieve(self, model, **kwargs):
        where_clause = self._fetch_attr_clause(model, **kwargs)

        c = self.conn.cursor()
        c.execute("select * from {} where {}".format(
            model.Meta.db_name,
            ' and '.join(where_clause)
        ))
        data_set = c.fetchone()
        description = list(map(lambda x: x[0], c.description))
        if data_set:
            return model(**dict(list(zip(description, data_set))))
        return None

    def list(self, model, **kwargs):
        result = []
        where_clause = self._fetch_attr_clause(model, **kwargs)

        c = self.conn.cursor()
        c.execute("select * from {} where {}".format(
            model.Meta.db_name,
            ' and '.join(where_clause)
        ))

        data = c.fetchall()
        description = list(map(lambda x: x[0], c.description))
        for data_set in data:
            tmp = list(zip(description, data_set))
            result.append(model(**dict(tmp)))
        return result

    def create(self, model, **kwargs):
        values = []
        keys = []
        for key, attr_type in model.__annotations__.items():
            if key == 'pk':
                continue
            keys.append(key)
            value = kwargs.get(key)
            if value is None:
                value = 'null'
            elif attr_type in (date, datetime, str):
                value = "'{}'".format(value)
            elif attr_type == bool:
                value = bool(value)
            values.append(value)

        c = self.conn.cursor()
        c.execute(
            "insert into {} ({}) values ({})".format(
                model.Meta.db_name,
                ','.join(map(str, keys)),
                ','.join(map(str, values))
            )
        )
        self.conn.commit()

    def create_bulk(self, model, **kwargs):
        values = []
        keys = []
        kwargs_set = copy(kwargs.get('chunks'))
        for key, attr_type in model.__annotations__.items():
            if key == 'pk':
                continue
            keys.append(key)
            for kwarg in kwargs_set:
                value = kwarg.get(key)
                if attr_type == bool:
                    value = bool(value) and 1 or 0
                kwarg[key] = value

        for kwarg in kwargs_set:
            tmp = []
            for key in keys:
                tmp.append(kwarg.get(key))
            values.append(tmp)
        c = self.conn.cursor()

        c.executemany(
            "insert into {} ({}) values ({})".format(
                model.Meta.db_name,
                ','.join(map(str, keys)),
                ('?,' * len(keys)).strip(',')
            ),
            values
        )
        self.conn.commit()

    def update(self, instance, **kwargs):
        set_clause = self._fetch_attr_clause(instance.__class__, **kwargs)
        c = self.conn.cursor()
        c.execute("update {} set {} where pk={}".format(
            instance.Meta.db_name,
            ', '.join(set_clause),
            instance.pk
        ))
        self.conn.commit()

    def delete(self, model, **kwargs):
        where_clause = self._fetch_attr_clause(model, **kwargs)
        c = self.conn.cursor()
        c.execute("delete from {} where {}".format(
            model.Meta.db_name,
            ' and '.join(where_clause)
        ))
        self.conn.commit()

    def get_size(self):
        c = self.conn.cursor()
        c.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
        data_set = c.fetchone()
        return data_set[0]


SQLiteDB = SQLiteStore()
