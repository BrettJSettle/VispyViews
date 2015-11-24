import numpy as np


class ActivePoint():
    def __init__(self, data):
        self.pos = np.array([data['Xc'], data['Yc']])
        self.data = data

    def withZ(self):
        return np.array([self[0], self[1], self['Zc']])

    def __getitem__(self, item):
        if type(item) in (int, tuple, slice):
            return self.pos[item]
        if item in self.data:
            return self.data[item]
        else:
            return self.__dict__[item]
