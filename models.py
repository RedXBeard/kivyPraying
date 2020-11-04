from storage import SQliteDB


class ModelBase:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def list(cls, **kwargs):
        return SQliteDB.list(cls, **kwargs)

    @classmethod
    def get(cls, **kwargs):
        return SQliteDB.retrieve(cls, **kwargs)

    @classmethod
    def create(cls, **kwargs):
        return SQliteDB.create(cls, **kwargs)

    def update(self, **kwargs):
        return SQliteDB.update(self, **kwargs)
    
    @classmethod
    def delete(cls, **kwargs):
        return SQliteDB.delete(cls, **kwargs)


class City(ModelBase):
    db_name = 'cities'
    attributes = ({'key': 'pk', 'type': int, 'primary': True},
                  {'key': 'name', 'type': str},
                  {'key': 'city_key', 'type': str},
                  {'key': 'id', 'type': int},
                  {'key': 'selected', 'type': bool})


class Time(ModelBase):
    db_name = 'times'
    attributes = ({'key': 'pk', 'type': int, 'primary': True},
                  {'key': 'time_name', 'type': str},
                  {'key': 'from_time', 'type': str},
                  {'key': 'to_time', 'type': str},
                  {'key': 'date', 'type': str},
                  {'key': 'city_id', 'type': int})


class Status(ModelBase):
    db_name = 'praying_status'
    attributes = ({'key': 'pk', 'type': int, 'primary': True},
                  {'key': 'time_name', 'type': str},
                  {'key': 'is_prayed', 'type': bool},
                  {'key': 'date', 'type': str})


class Language(ModelBase):
    db_name = 'languages'
    attributes = ({'key': 'pk', 'type': int, 'primary': True},
                  {'key': 'lang', 'type': str},
                  {'key': 'lang_text', 'type': str},
                  {'key': 'selected', 'type': bool})


class Reward(ModelBase):
    db_name = 'rewards'
    attributes = ({'key': 'pk', 'type': int, 'primary': True},
                  {'key': 'name', 'type': str},
                  {'key': 'count', 'type': int})
