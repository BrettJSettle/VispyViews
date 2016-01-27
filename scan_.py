from sklearn.cluster import DBSCAN
from PyQt4 import QtCore
import numpy as np
from PyQt4.QtCore import pyqtSignal as Signal
from Visuals import ClusterVisual

class DensityBasedScanner(QtCore.QThread):
	'''
	Density Based Clustering algorithm on a list of ActivePoint objects. returns a list of clustered point lists, and a list of noise points
	'''
	scanFinished = Signal(object, object)
	def __init__(self, points = [], epsilon = 30, minP = 5, minNeighbors = 1):
		QtCore.QThread.__init__(self)
		self.points = points
		self.epsilon = epsilon
		self.minP = minP
		self.minNeighbors = minNeighbors
		self.scanner = DBSCAN(eps=self.epsilon, min_samples=self.minNeighbors)

	def setPoints(self, points):
		self.points = points
		self.start()

	def update(self, epsilon=None, minP = None, minNeighbors = None):
		if epsilon != None:
			self.epsilon = epsilon
		if minP != None:
			self.minP = minP
		if minNeighbors != None:
			self.minNeighbors = minNeighbors
		self.scanner = DBSCAN(eps=self.epsilon, min_samples=self.minNeighbors)

	def run(self):
		clusters = []
		labels = self.scanner.fit_predict([p.pos for p in self.points])
		noise = [self.points[p] for p in np.where(labels == -1)[0]]
		for i in range(1, max(labels) + 1):
			print('Analyzing cluster %d of %d' % (i, max(labels)))
			clust = []
			for p in np.where(labels == i)[0]:
				clust.append(self.points[p])
			if len(clust) >= self.minP:
				clusters.append(ClusterVisual(clust))
			else:
				noise.extend(clust)
		self.scanFinished.emit(clusters, noise)
	
