from PyQt4.QtCore import *
from PyQt4.QtGui import *
import file_manager
import os
import numpy as np
from PyQt4.QtGui import QFileDialog, QApplication, QInputDialog
import fileinput

__all__ = ['open_file_gui', 'save_file_gui', 'file_to_array']


format_options = ['S1', 'S5', 'S10', 'S20', 'i1', 'i4', 'i8', 'f4', 'f8']

format_dict = \
{'Channel Name': 'S20',
'X': 'f8',
'Y': 'f8',
'Xc': 'f8',
'Yc': 'f8',
'Height': 'f8',
'Area': 'f8',
'Width': 'f8',
'Ax': 'f8',
'BG': 'f8',
'I': 'f8',
'Frame': 'i4',
'Length': 'i4',
'Link': 'i4',
'Valid': 'i4',
'Z': 'f4',
'Zc': 'f4',
'Photons': 'f8',
'Phi': 'f8',
'Lateral Localization Accuracy': 'f8',
'Xw': 'f8',
'Yw': 'f8',
'Xwc': 'f8',
'Ywc': 'f8'
} # end


def open_file_gui(func, filetypes, prompt='Open File', args=[]):
    filename= file_manager.getOpenFileName(caption=prompt, filter=filetypes)
    if filename != '':
        func(filename, *args)

def save_file_gui(func, filetypes, prompt = 'Save File', args = []):
    filename= file_manager.getSaveFileName(caption=prompt, filter=filetypes)
    if filename != '':
        func(filename, *args)

def get_format(name):
    if name in format_dict:
        return format_dict[name]
    form = QInputDialog.getItem(None, "Format for %s" % name, 'Pick a format: (S for string, i for integer, f for floating point):', format_options)
    for line in fileinput.input():
        if line.endswith('# end'):
            print('\n\n} # end')
        else:
            print(line)
    return form

def file_to_array(filename, columns=[]):
    lines = [line.strip() for line in open(filename).readlines()]
    names = lines[0].split('\t')
    formats = [get_format(i) for i in names]
    cols = None if len(columns) == 0 else [names.index(i) for i in columns]
    data = np.loadtxt(filename, dtype={'names': names, 'formats': formats}, delimiter='\t', skiprows=1, usecols = cols)
    return data
