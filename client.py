#!/usr/bin/env python2

import os, sys
if sys.platform == "win32":
    from time import sleep, clock
else:
    from time import sleep
    from time import time as clock

from PyQt4 import QtCore, QtGui

import numpy as np
from copy import deepcopy as copy
import socket, Queue, threading

from ViewPort import ViewPort
from ProbeMap import ProbeMap
from TimeScrubber import TimeScrubber

####

def socket_recv(socket, num_bytes):
    buf = bytearray(num_bytes)
    view = memoryview(buf)
    while num_bytes:
        nbytes = socket.recv_into(view, num_bytes)
        view = view[nbytes:] # slicing views is cheap
        num_bytes -= nbytes
    return str(buf)

####

class IOThread(QtCore.QThread):

    dataReceived = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.mtx = QtCore.QMutex()
        self.cv = QtCore.QWaitCondition()
        with QtCore.QMutexLocker(self.mtx):
            self.reqStack = None       # stack of max length 1
        self.alive = threading.Event()
        self.alive.set()

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10)
        self.connect()

    def connect(self):
        self.socket.connect((SERVER_ADDR, SERVER_PORT))

    def disconnect(self):
        self.socket.close()

    def run(self):
        while True:
            self.mtx.lock()
            while not self.reqStack:
                self.cv.wait(self.mtx)
            req = copy(self.reqStack) # this could be replaced by a proper stack structure
            self.reqStack = None
            self.mtx.unlock()
            self._handleRequest(req)

    def postRequest(self, req):
        with QtCore.QMutexLocker(self.mtx):
            self.reqStack = req
        self.cv.wakeAll()

    def _handleRequest(self, req):
        pass


class DataSlabRequest():

    def __init__(self, chan, time, filt):
        self.chan = chan
        self.time = time
        self.filt = filt

class DataSlabThread(IOThread):

    def _handleRequest(self, req):
        chan, time, filt = req.chan, req.time, req.filt
        payload = 'dataSlab,%d,%d,%r' % (chan, time, filt)
        self.socket.send(payload)
        try:
            chans = np.fromstring(socket_recv(self.socket, 12*2), dtype=np.uint16) # TODO: really need this?
            dataSlab = np.fromstring(socket_recv(self.socket, 12*60000*2), dtype=np.float16).reshape((12,60000))
            colors = 255*np.ones((12,4), dtype=np.uint8) # white for now
            self.dataReceived.emit((dataSlab, chans, time, colors))
        except socket.timeout:
            print 'dataSlab request timed out!'


class ActivityRequest():

    def __init__(self, time):
        self.time = time

class ActivityThread(IOThread):

    def _handleRequest(self, req):
        time = req.time
        payload = 'activity,%d' % time
        self.socket.send(payload)
        try:
            activity = np.fromstring(socket_recv(self.socket, 1020*2), dtype=np.float16)
            self.dataReceived.emit(activity)
        except socket.timeout:
            print 'activity request timed out!'

####

class MainWindow(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)


        self.event_time = clock()

        # IO threads
        self.dataSlabThread = DataSlabThread()
        self.dataSlabThread.start()
        self.activityThread = ActivityThread()
        self.activityThread.start()

        # GUI
        self.setStyleSheet("background-color: #0F0F0F")

        # temporary hack to get nsamples
        tmpsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tmpsock.connect((SERVER_ADDR, SERVER_PORT))
        tmpsock.send("nsamples")
        nsamples = np.fromstring(socket_recv(tmpsock,8), dtype=np.uint64)
        tmpsock.close()

        ## widgets
        self.probeMap = ProbeMap(410, "shanks.jpg")
        self.probeMap.chanSelected.connect(self.handleChannelSelection)
        self.timeScrubber = TimeScrubber(nsamples)
        self.timeScrubber.timeSelected.connect(self.handleTimeSelection)
        self.viewPort = ViewPort(np.zeros((12, 60000)), 6, 2)

        ## layout
        top_layout = QtGui.QHBoxLayout()
        top_layout.addWidget(self.probeMap)
        top_layout.addWidget(self.timeScrubber)
        layout = QtGui.QVBoxLayout()
        layout.addLayout(top_layout)
        layout.addWidget(self.viewPort)
        self.setLayout(layout)

        ## window and margin settings
        top_layout.setContentsMargins(0,0,0,0)
        layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(0,0,0,0)
        self.setWindowTitle('Aspen WDX (1020 Chan)')
        self.setWindowIcon(QtGui.QIcon('aspen_leaf.svg'))
        self.resize(1400,800)

        # signals/slots
        self.dataSlabThread.dataReceived.connect(self.viewPort.updateSlab)
        self.activityThread.dataReceived.connect(self.probeMap.set_intensities)

        # initialization
        self.slab_sample_index = 0
        self.slab_channel_index = 0
        self.filtered = True
        self.dataSlabThread.connect()
        self.activityThread.connect()

    def handleChannelSelection(self, probeCoords):
        shank, row, col = probeCoords
        self.slab_channel_index = 204 * shank + row * 2
        self.postRequests(activity=False)
    
    def handleTimeSelection(self, time):
        self.slab_sample_index = int(time)
        self.postRequests(activity=True)

    def postRequests(self, activity=False):
        slabReq = DataSlabRequest(self.slab_channel_index, self.slab_sample_index, self.filtered)
        self.dataSlabThread.postRequest(slabReq)
        if activity:
            actReq = ActivityRequest(self.slab_sample_index)
            self.activityThread.postRequest(actReq)
        
    def keyPressEvent(self, event):
        if clock() - self.event_time > 0.33:
            if event.key() == QtCore.Qt.Key_F:
                self.filtered = not self.filtered
                self.postRequests(activity=True)
                for item in self.viewPort.plotItems:
                    item.autoRange()

            if event.key() == QtCore.Qt.Key_Left:
                self.timeScrubber.decrement_time()
            
            elif event.key() == QtCore.Qt.Key_Right:
                self.timeScrubber.increment_time()
            
            elif event.key() == QtCore.Qt.Key_Up:
                self.probeMap.decrement_channel()
            
            elif event.key() == QtCore.Qt.Key_Down:
                self.probeMap.increment_channel()

            elif event.key() == QtCore.Qt.Key_Escape:
                self.dataSlabThread.quit()
                self.activityThread.quit()
                self.close()

            elif event.key() == QtCore.Qt.Key_Home:
                for item in self.viewPort.plotItems:
                    item.autoRange()
            elif event.key() == QtCore.Qt.Key_F11:
                if self.windowState() & QtCore.Qt.WindowFullScreen:
                    self.showNormal()
                else:
                    self.showFullScreen()

            self.event_time = clock()


if __name__=='__main__':
    if len(sys.argv)>1:
        SERVER_ADDR = sys.argv[1]
    else:
        SERVER_ADDR = 'localhost'
    if len(sys.argv)>2:
        SERVER_PORT = sys.argv[2]
    else:
        SERVER_PORT = 8000

    app = QtGui.QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
