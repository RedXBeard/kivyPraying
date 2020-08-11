import os
from subprocess import Popen, PIPE

from kivy.storage.jsonstore import JsonStore


def run_syscall(cmd):
    """
    run_syscall; handle sys calls this function used as shortcut.
    ::cmd: String, shell command is expected.
    """
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    return out.rstrip()


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


PATH_SEPARATOR = '/'
if os.path.realpath(__file__).find('\\') != -1:
    PATH_SEPARATOR = '\\'

PROJECT_PATH = PATH_SEPARATOR.join(os.path.realpath(__file__).split(PATH_SEPARATOR)[:-1])

if PATH_SEPARATOR == '/':
    cmd = "echo $HOME"
else:
    cmd = "echo %USERPROFILE%"

out = run_syscall(cmd).decode()
DEF_USER = out.split(PATH_SEPARATOR)[-1]
REPO_FILE = "{0}{1}.kivy-praying{1}praying".format(out.rstrip(), PATH_SEPARATOR)

directory = os.path.dirname(REPO_FILE)
if not os.path.exists(directory):
    os.makedirs(directory)
DB = JsonStore(REPO_FILE)
DB.store_sync()
