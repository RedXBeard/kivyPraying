import os
from datetime import datetime

from kivy import kivy_home_dir
from kivy.storage.jsonstore import JsonStore


def find_parent(cur_class, target_class):
    """find wanted widget from selected or current one"""
    req_class = cur_class
    target_class_name = str(target_class().__class__).split('.')[1].replace("'>", "")
    while True:
        cls = str(req_class.__class__).split('.')[1].replace("'>", "")
        if cls == target_class_name:
            break
        elif cls == 'core':
            req_class = None
            break

        req_class = req_class.parent
    return req_class


def get_color(obj):
    u"""Color of widget returns."""
    try:
        obj_color = list(filter(lambda x: str(x).find('Color') != -1, obj.canvas.before.children))[0]
    except IndexError:
        obj_color = None
    return obj_color


def set_color(obj, color):
    obj_color = get_color(obj)
    try:
        obj_color.rgba = color
    except AttributeError:
        pass


def set_children_color(obj, color):
    for child in getattr(obj, 'children', []):
        set_color(child, color)


def seconds_converter(scnds):
    seconds = scnds % 60
    mnts = (scnds - seconds) / 60
    minutes = mnts % 60
    hours = (mnts - minutes) / 60

    return list(map(lambda x: str(x).zfill(2), map(int, [hours, minutes, seconds])))


WEEKDAYS = ['Pazartesi', 'Salı', 'Çarsamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
MONTHS = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
          'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
PATH_SEPARATOR = '/'
if os.path.realpath(__file__).find('\\') != -1:
    PATH_SEPARATOR = '\\'

PROJECT_PATH = PATH_SEPARATOR.join(os.path.realpath(__file__).split(PATH_SEPARATOR)[:-1])

REPO_FILE = "{0}{1}.kivy-praying{1}praying".format(kivy_home_dir.rstrip(), PATH_SEPARATOR)

directory = os.path.dirname(REPO_FILE)
if not os.path.exists(directory):
    os.makedirs(directory)
DB = JsonStore(REPO_FILE)
DB.store_sync()


def _date_parser(rec):
    return datetime.strptime(rec, '%d.%m.%Y').date()


def _datetime_parser(rec):
    return datetime.strptime(rec, '%d.%m.%Y %H:%M')


def _concat_date_time(time, date):
    date = '{}.{}.{}'.format(date.day, date.month, date.year)
    return '{} {}'.format(date, time)
