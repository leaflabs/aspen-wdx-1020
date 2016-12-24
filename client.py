#!/usr/bin/env python2

import os, sys
if sys.platform == "win32":
    from time import sleep, clock
else:
    from time import sleep
    from time import time as clock

from PyQt4 import QtCore, QtGui

import numpy as np

import socket, Queue, threading

from ViewPort import ViewPort
from ProbeMap import ProbeMap
from TimeScrubber import TimeScrubber

def socket_recv(socket, num_bytes):
    buf = bytearray(num_bytes)
    view = memoryview(buf)
    while num_bytes:
        nbytes = socket.recv_into(view, num_bytes)
        view = view[nbytes:] # slicing views is cheap
        num_bytes -= nbytes
    return str(buf)

####

class DataRequest():

    def __init__(self, chan, time, filt):
        self.chan = chan
        self.time = time
        self.filt = filt

class DataThread(QtCore.QThread):

    dataReceived = QtCore.pyqtSignal(object)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.q = Queue.Queue()
        self.alive = threading.Event()
        self.alive.set()

        self.connect()

    def run(self):
        while self.alive.isSet():
            try:
                # Queue.get with timeout to allow checking self.alive
                req = self.q.get(True, 0.1)
                self._handleRequest(req)
            except Queue.Empty as e:
                continue

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(2)
        self.socket.connect((SERVER_ADDR, SERVER_PORT))

    def closeConnection(self):
        self.socket.close()

    def postRequest(self, chan, time, filt):
        req = DataRequest(chan, time, filt)
        self.q.put(req)
        print '\nrequest posted: ', req
        print 'queue length is: ', self.q.qsize()

    def _handleRequest(self, req):
        chan, time, filt = req.chan, req.time, req.filt
        payload = 'dataSlab,%d,%d,%r' % (chan, time, filt)
        self.socket.send(payload)
        try:
            chans = np.fromstring(socket_recv(self.socket, 12*2), dtype=np.uint16) # TODO: really need this?
            dataSlab = np.fromstring(socket_recv(self.socket, 12*60000*2), dtype=np.float16).reshape((12,60000))
            print '\nReceived:', dataSlab.shape, dataSlab.dtype, dataSlab[0,:10], '\n'
            colors = 255*np.ones((12,4), dtype=np.uint8) # white for now
            self.dataReceived.emit((dataSlab, chans, time, colors))
            print 'request handled: ', req
            print 'queue length is: %d\n' % self.q.qsize()
        except socket.timeout:
            print 'timeout!'


class MainWindow(QtGui.QWidget):

    def __init__(self):
        QtGui.QWidget.__init__(self)


        self.event_time = clock()

        # IO structure
        self.dataThread = DataThread()
        self.dataThread.start()

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
        #self.setWindowIcon(QtGui.QIcon('aspen_logo_400x400.jpeg'))
        #self.setWindowIcon(QtGui.QIcon('shanks.jpg'))
        self.resize(1400,800)

        # signals/slots
        self.dataThread.dataReceived.connect(self.viewPort.updateSlab)

        # initialization
        self.slab_sample_index = 0
        self.slab_channel_index = 0
        self.filtered = True
        self.dataThread.connect()

    def handleChannelSelection(self, probeCoords):
        shank, row, col = probeCoords
        self.slab_channel_index = 204 * shank + row * 2
        self.dataThread.postRequest(self.slab_channel_index, self.slab_sample_index, self.filtered)
    
    def handleTimeSelection(self, time):
        self.slab_sample_index = int(time)
        self.dataThread.postRequest(self.slab_channel_index, self.slab_sample_index, self.filtered)
        
    def keyPressEvent(self, event):
        if clock() - self.event_time > 0.33:
            if event.key() == QtCore.Qt.Key_F:
                self.filtered = not self.filtered
                self.dataThread.postRequest(self.slab_channel_index, self.slab_sample_index, self.filtered)
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
                self.dataThread.quit()
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
