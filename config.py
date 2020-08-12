import os

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
