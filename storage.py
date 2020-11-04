import sqlite3

from migrations import STATEMENTS


class SQliteStore:
    def __init__(self):
        self.conn = sqlite3.connect('db.sqlite3')
        for statement in STATEMENTS:
            try:
                c = self.conn.cursor()
                c.execute(statement)
                self.conn.commit()
            except Exception as e:
                print(e)
                pass

    def _fetch_attr_clause(self, model, **kwargs):
        where_clause = []

        for pair in model.attributes:
            attr_type = pair.get('type')
            key = pair.get('key')
            if key not in kwargs:
                continue

            value = kwargs.get(key)
            if attr_type == str:
                value = "'{}'".format(value)
            elif attr_type == bool:
                value = bool(value)
            where_clause.append('{}={}'.format(key, value))

        if not where_clause:
            where_clause = ['1=1']

        return where_clause

    def retrieve(self, model, **kwargs):
        where_clause = self._fetch_attr_clause(model, **kwargs)

        c = self.conn.cursor()
        c.execute("select * from {} where {}".format(
            model.db_name,
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
            model.db_name,
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
        for pair in model.attributes:
            if pair.get('primary'):
                continue
            attr_type = pair.get('type')
            key = pair.get('key')
            keys.append(key)
            value = kwargs.get(key)
            if attr_type == str:
                value = "'{}'".format(value)
            elif attr_type == bool:
                value = bool(value)
            values.append(value)

        c = self.conn.cursor()
        c.execute(
            "insert into {} ({}) values ({})".format(
                model.db_name,
                ','.join(map(str, keys)),
                ','.join(map(str, values))
            )
        )
        self.conn.commit()

    def update(self, instance, **kwargs):
        set_clause = self._fetch_attr_clause(instance.__class__, **kwargs)
        c = self.conn.cursor()
        c.execute("update {} set {} where pk={}".format(
            instance.db_name,
            ', '.join(set_clause),
            instance.pk
        ))
        self.conn.commit()

    def delete(self, model, **kwargs):
        where_clause = self._fetch_attr_clause(model, **kwargs)
        c = self.conn.cursor()
        c.execute("delete from {} where {}".format(
            model.db_name,
            ' and '.join(where_clause)
        ))
        self.conn.commit()


SQliteDB = SQliteStore()
