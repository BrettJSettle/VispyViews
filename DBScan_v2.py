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
import sys, time
from DataWidget import DataWidget
from scan_ import DensityBasedScanner
import threading
from file_ import *
from settings import settings

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

def points_in_roi(roi, channel = None):
    points = []
    for ch in canvas.markers:
        if channel in (None, ch):
            for p in ch.points:
                if roi.contains(p.pos):
                    points.append(p)
    return points


def connect_roi(roi):
    if scanThread.isRunning():
        scanThread.terminate()
        performScan(roi)
    roi.translateFinished.connect(performScan)
    roi.translateFinished.connect(fillROITable)
    roi.selectionChanged.connect(lambda roi, b: performScan(roi))
    roi.menu.addAction(QtGui.QAction("Plot points on 3D Plane", roi.menu, triggered = lambda : make3DPlot(roi)))
    roi.menu.addAction(QtGui.QAction("Export points in ROI", roi.menu, triggered=lambda : save_file_gui(exportPointsInROI, prompt='Export Points in roi %d to a text file' % roi.id, filetypes='Text Files (*.txt)', args=[roi])))
    roi.menu.addAction(QtGui.QAction('Remove points in ROI', roi.menu, triggered = lambda : remove_points_in_roi(roi)))
    fillROITable()

def import_channels(fname):
    global canvas
    channel_names = set(np.loadtxt(fname, usecols=[0], delimiter='\t', dtype='S16', skiprows=1))
    win.statusBar().showMessage('Found channels: ' + ', '.join([c.decode('utf-8') for c in channel_names]))
    t = time.time()
    headers = [s.strip() for s in open(fname, 'r').readline().split('\t')]
    dtypes = {'names': headers, 'formats': ['a16'] + (['f8'] * (len(headers) - 1))}
    data = np.loadtxt(fname, skiprows=1, dtype=dtypes, delimiter='\t')
    active_points = [ActivePoint(dict(zip(headers, d))) for d in data]
    for ch in channel_names:
        ps = [p for p in active_points if p['Channel Name'] == ch]
        canvas.markers.append(ChannelVisual(name=ch.decode('utf-8'), active_points=ps))
    x, y = np.transpose([p.pos for p in active_points])
    canvas.panzoom.translate = [0, 0, 0, 0]
    canvas.panzoom.scale = [.05, .05, 0, 0]
    win.statusBar().showMessage('Successfully imported %s (%s s)' % (fname, time.time() - t))

def scanFinished(clusts, noise):
    global clusters
    clusters = clusts
    values = []
    for cluster in clusters[:100]:
        meanxy = np.mean([p.pos for p in cluster.points], 0)
        values.append([len(cluster.points), cluster.centroid, cluster.grid_area, cluster.box_area, cluster.density, cluster.averageDistance])
    dbscanWidget.clusterTable.setData(values)
    dbscanWidget.clusterTable.setHorizontalHeaderLabels(["N Points", 'Centroid', 'Grid Area', 'Box Area', 'Density', 'Average Distance'])
    win.statusBar().showMessage('%d clusters found (%s s)' % (len(clusters), time.time() - scanThread.start_time))

def performScan(roi=None):
    if not dbscanWidget.groupBox.isChecked():
        return
    if canvas.current_roi != None and canvas.current_roi.selected:
        roi = canvas.current_roi
    points = []
    if roi == None or not any([ROI.selected for ROI in canvas.roi_visuals]):
        return
        #for ch in canvas.markers:
        #    points.extend(ch.points)
    elif roi != None:
        points = points_in_roi(roi)
    if len(points) == 0:
        return
    win.statusBar().showMessage('Clustering %d points. Analysis progress in command prompt' % len(points))
    scanThread.start_time = time.time()
    scanThread.setPoints(points)

def fillROITable():
    values = []
    roiDataTable.clear()
    data = []
    for roi in canvas.roi_visuals:
        pts = []
        for channel in canvas.markers:
            pts.append(points_in_roi(roi, channel=channel))
        data.append([roi.id, sum([len(p) for p in pts])] + [len(p) for p in pts])
    data = sorted(data, key=lambda d: d[0])
    roiDataTable.setData(data)
    roiDataTable.setHorizontalHeaderLabels(['ROI #', 'N Points'] + ["N %s" % i.name for i in canvas.markers])

def exportPointsInROI(fname, roi):
    fname = str(QtGui.QFileDialog.getSaveFileName(None, 'Save Points in ROI to text file', '*.txt'))
    if fname == '':
        return
    points = points_in_roi(roi)
    win.statusBar().showMessage('Exporting %d points to %s' % (len(points), fname))
    t = time.time()
    headers = points[0].data.keys()
    with open(fname, 'w') as outf:
        outf.write('\t'.join(headers) + '\n')
        for p in points:
            outf.write('\t'.join([str(p.data[k]) for k in headers]) + '\n')
    win.statusBar().showMessage('Successfully exported points to %s (%s s)' % (fname, time.time() - t))

def exportCluster(fname):
    win.statusBar().showMessage('Exporting %d clusters to %s' % (len(clusters), fname))
    t = time.time()
    headers = ["N Points", 'Centroid', 'Grid Area', 'Box Area', 'Density', 'Average Distance']
    with open(fname, 'w') as outf:
        outf.write('\t'.join(headers) + '\n')
        for cluster in clusters:
            outf.write('\t'.join([len(cluster.points), cluster.centroid, cluster.grid_area, cluster.box_area, cluster.density, cluster.averageDistance]) + '\n')
    win.statusBar().showMessage('Successfully clusters points to %s (%s s)' % (fname, time.time() - t))

class EventFilter(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)

    def eventFilter(self, obj, event):
        if (event.type()==QtCore.QEvent.DragEnter):
            if event.mimeData().hasUrls():
                event.accept()   # must accept the dragEnterEvent or else the dropEvent can't occur !!!
            else:
                event.ignore()
        if (event.type() == QtCore.QEvent.Drop):
            if event.mimeData().hasUrls():   # if file or link is dropped
                url = event.mimeData().urls()[0]   # get first url
                filename=url.toString()
                filename=filename.split('file:///')[1]
                if filename.endswith('.txt'):
                    win.statusBar().showMessage('Loading channels from %s' % (filename))
                    import_channels(filename)#This fails on windows symbolic links.  http://stackoverflow.com/questions/15258506/os-path-islink-on-windows-with-python
                else:
                    obj.statusBar().showMessage('%s widget does not support %s files...' % (obj.__name__, filetype))
                event.accept()
            else:
                event.ignore()
        return False # lets the event continue to the edit
eventFilter = EventFilter()

def onClose(event):
    scanThread.exit(0)
    scanThread.terminate()
    settings.save()
    sys.exit(0)

def drawEvent(event):
    global clusters
    Canvas.on_draw(canvas, event)
    for cluster in clusters:
        cluster.draw(canvas.tr_sys)

if __name__ == '__main__':
    a = QtGui.QApplication([])
    ignore = {'Z Rejected'}
    clusters = []
    dbscanWidget = uic.loadUi('ui/DBScan.ui')
    dbscanWidget.__name__ = 'DBSCAN'
    settings.reload()
    scanThread = DensityBasedScanner()
    scanThread.scanFinished.connect(scanFinished)
    dbscanWidget.epsilonSpin.setOpts(value=60, step=.1, maximum=1000)
    dbscanWidget.epsilonSpin.valueChanged.connect(lambda epsi: scanThread.update(epsilon=epsi))
    dbscanWidget.minNeighborsSpin.setOpts(value=3, int=True, step=1)
    dbscanWidget.minNeighborsSpin.valueChanged.connect(lambda minNeighbors: scanThread.update(minNeighbors=minNeighbors))
    dbscanWidget.minDensitySpin.setOpts(value=8, int=True, step=1)
    dbscanWidget.minDensitySpin.valueChanged.connect(lambda minP: scanThread.update(minP = minP))
    dbscanWidget.groupBox.toggled.connect(lambda : performScan())
    dbscanWidget.exportButton.clicked.connect(lambda : save_file_gui(exportClusters, prompt='Export cluster data to text file', filetypes='*.txt'))

    roiDataTable = DataWidget(sortable=True)
    roiDataTable.setFormat("%3.3f")
    roiDataTable.__name__ = "ROI Data"
    roiDataTable.setHorizontalHeaderLabels(['ROI #', 'N Points'])
    
    win = QtGui.QMainWindow()
    win.setAcceptDrops(True)
    #win.installEventFilter(eventFilter)
    widg = QtGui.QWidget()
    win.setCentralWidget(widg)
    layout = QtGui.QGridLayout(widg)
    layout.addWidget(dbscanWidget, 0, 0)
    layout.addWidget(roiDataTable, 1, 0)
    win.setGeometry(200, 100, 400, 800)

    canvas = Canvas()
    canvas.on_draw = drawEvent
    canvas.native.installEventFilter(eventFilter)
    canvas.native.setAcceptDrops(True)
    canvas.native.closeEvent = onClose
    win.closeEvent = onClose
    #canvas.on_mouse_release = mouseRelease
    canvas.roiCreated.connect(connect_roi)
    canvas.roiDeleted.connect(fillROITable)
    canvas.native.show()
    #canvas.native.setGeometry(300, 50, 800, 800)
    menuBar = win.menuBar()
    fileMenu = menuBar.addMenu('File')
    fileMenu.addAction(QtGui.QAction('Open Scatter', fileMenu, triggered=lambda : open_file_gui(import_channels, prompt='Import channels from Text file', filetypes="Text Files (*.txt)")))
    view3DWindow = None
    win.show()
    a.exec_()