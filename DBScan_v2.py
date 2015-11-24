from __future__ import division
import numpy as np
from PyQt4.QtCore import pyqtSignal as Signal
from vispy import app
from vispy import gloo
from vispy.visuals.shaders import ModularProgram
from vispy.visuals import Visual, LinePlotVisual, LineVisual, PolygonVisual
from vispy.visuals.transforms import (STTransform, LogTransform,
                                      TransformSystem, ChainTransform)
from pyqtgraph import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from Visuals import *
from Canvas2D import *
from Points import *
from PyQt4 import uic
import sys
from DataWidget import DataWidget

class Visual3D(gl.GLScatterPlotItem):
    def __init__(self, active_points):
        gl.GLScatterPlotItem.__init__(self)
        self.points = active_points
        colors = np.array([255 * ChannelVisual.getChannelColor(ap['Channel Name']) for ap in active_points])
        pos = [ap.withZ() for ap in active_points]
        self.setData(pos=np.array(pos), color=colors, pxMode=True, size=4)

def make3DPlot(roi):
    global view3DWindow
    points = []
    for ch in canvas.markers:
        for p in ch.points:
            if roi.contains(p.pos):
                points.append(p)
    center = np.average([p.withZ() for p in points], 0)
    if len(points) == 0:
        return
    scatter = Visual3D(points)
    view3DWindow = gl.GLViewWidget()
    view3DWindow.addItem(scatter)
    atX, atY, atZ = view3DWindow.cameraPosition()
    view3DWindow.pan(-atX, -atY, -atZ)
    view3DWindow.opts['distance'] = 1000
    view3DWindow.opts['center'] = QtGui.QVector3D(*center)
    return view3DWindow.show()

def remove_points_in_roi(roi):
    for ch in canvas.markers:
        points = []
        for p in ch.points:
            if not roi.contains(p.pos):
                points.append(p)
        ch.set_data(points)

def points_in_roi(roi):
    points = []
    for ch in canvas.markers: 
        for p in ch.points:
            if not roi.contains(p.pos):
                points.append(p)
    return points


def connect_roi(roi):
    roi.menu.addAction(QtGui.QAction("Plot points on 3D Plane", roi.menu, triggered = lambda : make3DPlot(roi)))
    roi.menu.addAction(QAction("Export points in ROI", roi.menu, triggered=lambda : \
    exportPointsInROI(roi)))
    roi.menu.addAction(QtGui.QAction('Remove points in ROI', roi.menu, triggered = lambda : remove_points_in_roi(roi)))

def mouseRelease(event):
    if event.button == 2 and canvas.drawing_roi:
        connect_roi(canvas.current_roi)
    Canvas.on_mouse_release(canvas, event)

def openFile(fname=''):
    global c
    if type(fname) != str or fname == '':
        fname= QtGui.QFileDialog.getOpenFileName(None, "Open a text file", '', "Text Files (*.txt)")
    channel_names = set(np.loadtxt(fname, usecols=[0], delimiter='\t', dtype='S16', skiprows=1))
    headers = [s.strip() for s in open(fname, 'r').readline().split('\t')]
    channels = []
    dtypes = {'names': headers, 'formats': ['a16'] + (['f16'] * (len(headers) - 1))}
    data = np.loadtxt(fname, skiprows=1, dtype=dtypes, delimiter='\t')
    active_points = [ActivePoint(dict(zip(headers, d))) for d in data]
    for ch in channel_names:
        ps = [p for p in active_points if p['Channel Name'] == ch]
        channels.append(ChannelVisual(name=ch.decode('utf-8'), active_points=ps))
        canvas.markers.append(channels[-1])
    canvas.set_pos(np.mean([p.pos for p in active_points], 0))

def performDBSCAN(roi=None):
    if roi != None:
        points = points_in_roi(roi)
    else:
        points = []
        for ch in channels:
            points.extend(ch.active_points)
    values = []
    if dbscanWidget.groupBox.isChecked():
        for channel in channels:
            if not channel.analyzed:
                epsi = dbscanWidget.epsilonSpin.value()
                minP = dbscanWidget.minDensitySpin.value()
                minNeighbs = dbscanWidget.minNeighborsSpin.value()
                channel.analyze(points = points, epsilon=epsi, minPoints = minP, minNeighbors=minNeighbs)
            for i, cluster in enumerate(channel.clusters):
                meanxy = np.mean(cluster.points, 0)
                if roi.contains(QPointF(*meanxy)):
                    values.append([i, len(cluster), "(%.3f, %.3F)" % meanxy])
        dbscanWidget.clusterTable.setData(values)
    else:
        for channel in channels:
            channel.showAll()
            for cluster in channel.clusters:
                plotWidget.removeItem(cluster)
                plotWidget.removeItem(cluster.skeleton)
                plotWidget.removeItem(cluster.border)
    for channel in channels:
        channel.analyzed = False
    dbscanWidget.clusterTable.setHorizontalHeaderLabels(["Cluster #", "N Points", 'Mean XY'])

def fillROITable():
    values = []
    roiDataTable.clear()
    data = []
    for roi in plotWidget.getViewBox().addedItems:
        if isinstance(roi, Freehand):
            pts = []
            for channel in channels:
                pts.append(points_in_roi(roi, channel=channel))
            data.append([roi.id, sum([len(p) for p in pts])] + [len(p) for p in pts])
    roiDataTable.setData(data)
    roiDataTable.setHorizontalHeaderLabels(['ROI #', 'N Points'] + ["N %s" % i.channel_name for i in channels])

def exportPointsInROI(roi):
    fname = str(QtGui.QFileDialog.getSaveFileName(None, 'Save Points in ROI to text file', '*.txt'))
    if fname == '':
        return
    points = points_in_roi(roi)
    headers = points[0].data.keys()
    with open(fname, 'w') as outf:
        outf.write('\t'.join(headers) + '\n')
        for p in points:
            outf.write('\t'.join([p.data[k] for k in headers]) + '\n')

def onClose(event):
    sys.exit(0)

if __name__ == '__main__':
    a = QtGui.QApplication([])
    ignore = {'Z Rejected'}

    dbscanWidget = uic.loadUi('ui/DBScan.ui')
    dbscanWidget.__name__ = 'DBSCAN'

    dbscanWidget.epsilonSpin.setOpts(value=30, step=.1, maximum=1000)
    dbscanWidget.epsilonSpin.valueChanged.connect(performDBSCAN)
    dbscanWidget.minNeighborsSpin.setOpts(value=1, int=True, step=1)
    dbscanWidget.minNeighborsSpin.valueChanged.connect(performDBSCAN)
    dbscanWidget.minDensitySpin.setOpts(value=4, int=True, step=1)
    dbscanWidget.minDensitySpin.valueChanged.connect(performDBSCAN)
    dbscanWidget.groupBox.toggled.connect(performDBSCAN)

    roiDataTable = DataWidget(sortable=True)
    roiDataTable.setFormat("%3.3f")
    roiDataTable.__name__ = "ROI Data"
    roiDataTable.setHorizontalHeaderLabels(['ROI #', 'N Points'])
    
    win = QtGui.QMainWindow()
    widg = QtGui.QWidget()
    win.setCentralWidget(widg)
    layout = QtGui.QGridLayout(widg)
    layout.addWidget(dbscanWidget, 0, 0)
    layout.addWidget(roiDataTable, 1, 0)
    win.setGeometry(20, 50, 200, 800)

    canvas = Canvas()
    canvas.native.closeEvent = onClose
    win.closeEvent = onClose
    canvas.on_mouse_release = mouseRelease
    canvas.native.show()
    #canvas.native.setGeometry(300, 50, 800, 800)
    menuBar = win.menuBar()
    fileMenu = menuBar.addMenu('File')
    fileMenu.addAction(QtGui.QAction('Open Scatter', fileMenu, triggered=lambda : openFile()))
    view3DWindow = None
    win.show()
    a.exec_()