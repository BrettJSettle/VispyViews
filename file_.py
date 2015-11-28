from PyQt4.QtCore import *
from PyQt4.QtGui import *
from settings import settings
import os

__all__ = ['open_file_gui', 'save_file_gui']

def open_file_gui(func, filetypes, prompt='Open File', args=[]):
    if hasattr(settings, 'filename') and settings.filename != None and os.path.isfile(settings.filename):
        filename=settings.filename
    else:
        filename = ''
    filename= QFileDialog.getOpenFileName(None, caption=prompt, directory=filename, filter=filetypes)
    filename=str(filename)
    settings.filename = filename
    if filename != '':
        func(filename, *args)

def save_file_gui(func, filetypes, prompt = 'Save File', args = []):
    if hasattr(settings, 'filename') and settings.filename != '' and os.path.isdir(os.path.dirname(settings.filename)):
        filename=settings.filename
    else:
        filename = ''
    filename= QFileDialog.getSaveFileName(None, caption=prompt, directory=directory, filter=filetypes)
    filename=str(filename)
    settings.filename = filename
    if filename != '':
        func(filename, *args)