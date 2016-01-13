import os
import numpy as np
from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtCore import pyqtSignal as Signal
from pyqtgraph.console import ConsoleWidget
from pyqtgraph.dockarea import *
import time
import pyqtgraph as pg

class DataWidget(pg.TableWidget):
	__name__ = "Data Widget"
	def __init__(self, sortable=False, **args):
		pg.TableWidget.__init__(self, **args)
		if 'name' in args:
			self.__name__ = args.pop('name')
		self.setSortingEnabled(sortable)
		self.addedMenu = QMenu('Other')

	def contextMenuEvent(self, ev):
		self._make_menu().exec_(ev.globalPos())

	def _make_menu(self):
		menu = QMenu('%s Options' % self.__name__)
		self.contextMenu.setTitle('Edit')
		menu.addMenu(self.contextMenu)
		dataMenu = menu.addMenu("Data Options")
		dataMenu.addAction(QAction('Transpose Data', menu, triggered=self.transpose))
		dataMenu.addAction(QAction('Remove Selected Column(s)', menu, triggered=lambda : [self.removeColumn(i) for i in sorted({cell.column() for cell in self.selectedItems()})[::-1]]))
		dataMenu.addAction(QAction('Remove Selected Row(s)', menu, triggered=lambda : [self.removeRow(i) for i in sorted({cell.row() for cell in self.selectedItems()})[::-1]]))
		dataMenu.addAction(QAction('Format All Cells', menu, triggered = self.changeFormat))
		menu.addAction(QAction('Clear Table', menu, triggered=self.clear))
		if not self.addedMenu.isEmpty():
			menu.addMenu(self.addedMenu)
		return menu
	
	def save(self, data):
	    fileName = QFileDialog.getSaveFileName(self, "Save As..", "", "Text file (*.txt)")
	    if fileName == '':
	        return
	    open(fileName, 'w').write(data)

	def isEmpty(self):
		return self.rowCount() == 0 and self.columnCount() == 0

	def getData(self):
		rs, cs = int(self.rowCount()), int(self.columnCount())
		data = np.zeros((rs, cs))
		for r in range(rs):
			for c in range(cs):
				if self.item(r, c) is not None:
					data[r, c] = self.item(r, c).value
		return np.reshape(data, (rs, cs))

	def changeFormat(self, f=''):
		if f == '':
			f = getString(self, "Formatting cells", 'How would you like to display cell values? (%#.#f/d)', initial=self.items[0]._defaultFormat)
		for item in self.items:
			item.setFormat(f)

	def transpose(self):
		cop = self.getData().transpose()
		hs = [self.horizontalHeaderItem(i).text() for i in range(self.columnCount()) if self.horizontalHeaderItem(i)]
		vs = [self.verticalHeaderItem(i).text() for i in range(self.rowCount()) if self.verticalHeaderItem(i)]
		self.setHorizontalHeaderLabels(vs)
		self.setVerticalHeaderLabels(hs)
		self.setData(cop)
