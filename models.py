from datetime import datetime, date

from storage import SQLiteDB


class ModelBase:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            annotation = self.__annotations__.get(key)
            if value is None:
                value = None
            elif annotation == date:
                value = value and datetime.strptime(value, "%Y-%m-%d").date()
            elif annotation == datetime:
                value = datetime.strptime(value, "%d.%m.%Y %H:%M")
            elif annotation == bool:
                value = bool(value)
            elif annotation == int:
                value = int(value)
            elif annotation == str:
                value = str(value)
            setattr(self, key, value)

    @classmethod
    def list(cls, **kwargs):
        return SQLiteDB.list(cls, **kwargs)

    @classmethod
    def get(cls, **kwargs):
        return SQLiteDB.retrieve(cls, **kwargs)

    @classmethod
    def create(cls, **kwargs):
        return SQLiteDB.create(cls, **kwargs)

    @classmethod
    def create_bulk(cls, **kwargs):
        return SQLiteDB.create_bulk(cls, **kwargs)

    def update(self, **kwargs):
        return SQLiteDB.update(self, **kwargs)

    @classmethod
    def delete(cls, **kwargs):
        return SQLiteDB.delete(cls, **kwargs)


class Country(ModelBase):
    pk: int
    name: str
    country_key: str
    id: int
    selected: bool

    class Meta:
        db_name = "countries"


class City(ModelBase):
    pk: int
    name: str
    city_key: str
    id: int
    selected: bool
    country_id: int
    direct_city_id: int

    class Meta:
        db_name = "cities"

    @property
    def country(self):
        return Country.get(id=self.country_id)


class Time(ModelBase):
    pk: int
    time_name: str
    from_time: datetime
    to_time: datetime
    date: date
    city_id: int

    class Meta:
        db_name = "times"


class Status(ModelBase):
    pk: int
    time_name: str
    is_prayed: bool
    date: date

    class Meta:
        db_name = "praying_status"


class Language(ModelBase):
    pk: int
    lang: str
    lang_text: str
    selected: bool

    class Meta:
        db_name = "languages"


class Reward(ModelBase):
    pk: int
    name: str
    count: int

    class Meta:
        db_name = "rewards"
