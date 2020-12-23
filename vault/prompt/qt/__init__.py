import sys
from os.path import realpath, dirname
from pathlib import Path


def resource_path(path):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / path
    return Path(dirname(realpath(__file__))) / path
