#!/usr/bin/env python2

import sys
if sys.platform == "win32":
    from time import sleep, clock
else:
    from time import sleep
    from time import time as clock

import numpy as np

from PyQt4 import QtCore, QtGui
import pyqtgraph as pg
pg.setConfigOptions(antialias=True)

class plot_item(pg.PlotItem):

    def __init__(self, *args, **kwargs):
        pg.PlotItem.__init__(self, *args, **kwargs)
        
        # install event filter for viewbox and axes items
        self.vb.installEventFilter(self)
        for axesDict in self.axes.values():
            axesDict['item'].installEventFilter(self)

    def eventFilter(self, target, ev):
        if ev.type() == QtCore.QEvent.GraphicsSceneWheel:
            if ev.modifiers() == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                # print 'ctrl-shift-wheel'
                self.axes['left']['item'].wheelEvent(ev)
            else:
                # print 'ctrl-wheel'
                self.axes['bottom']['item'].wheelEvent(ev)
            return True
        return False

class ViewPort(pg.GraphicsLayoutWidget):

    def __init__(self, dataSlab, num_rows, num_cols):
        pg.GraphicsLayoutWidget.__init__(self)
        self.setStyleSheet("background-color: #0F0F0F")
        self.dataSlab = dataSlab
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.plotItems = []
        self.initializePlots()
        self.moved = False

    def initializePlots(self):
        t = np.linspace(0, 2, 60000)
        for i in range(self.num_rows * self.num_cols):
            plotItem = plot_item()
            plotItem.plot(y=self.dataSlab[i,:], x=t)
            
            plotItem.hideButtons()
            plotItem.showGrid(x=True, y=True, alpha=.25)
            
            if i > 0:
                plotItem.setXLink(self.plotItems[i-1])
                plotItem.setYLink(self.plotItems[i-1])
            
            self.addItem(plotItem)
            self.plotItems.append(plotItem)
            
            if i % 2 == 1:
                self.nextRow()

    def updateSlab(self, dataSlab):
        # dataSlab should have form: (dataSlab[12,60000], chans[12], time, colors[12])
        # TODO: clean this up
        min, max = dataSlab[0].min(), dataSlab[0].max()
        guard_band = (max - min) * .075
        t_offset = float(dataSlab[2]) / 30000.
        t = np.linspace(0, 2, 60000) + t_offset
        for index, item in enumerate(self.plotItems):
            title = "willow chan %.4d" % (int(dataSlab[1][index]))
            item.setTitle(title=title)
            item.curves[0].setData(x=t, y=dataSlab[0][index,:],antialias=True,
                        pen=QtGui.QColor(*tuple(dataSlab[3][index])))
            item.setLimits(xMin=t_offset, xMax=2+t_offset,
                yMin=min-guard_band, yMax=max+guard_band, maxXRange=2, minXRange=.03)
            item.setYRange(min, max, update=True)


if __name__ =="__main__":
    app = QtGui.QApplication(sys.argv)
    dataSlab = np.zeros((12,60000))
    widget = ViewPort(dataSlab, 6, 2)
    widget.show()
    sys.exit(app.exec_())
