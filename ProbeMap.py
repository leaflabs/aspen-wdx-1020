#!/usr/bin/env python2

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

import numpy as np

from CursorRect import CursorRect

from viridis import viridis as cmap

ACT_MAX = 300.
ACT_MIN = 0.

class ProbeMap(QtGui.QLabel):
    
    chanSelected = QtCore.pyqtSignal(tuple)

    def __init__(self, w, img):
        super(ProbeMap, self).__init__()
        self.setFrameStyle(QtGui.QFrame.StyledPanel)
        self.setStyleSheet("background-color: #0F0F0F")
        
        # load our background image
        pixmap = QtGui.QPixmap(img)
        
        # set our widget size, calculations sprout from this, so ensure margins are set to 0 in its layout
        self.setFixedWidth(w)
        self.setFixedHeight(self.heightForWidth(self.size().width()))
        self.setFixedWidth(int(1.25 * w))

        # scale pixmap to window size
        self.scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio,
                        transformMode=Qt.SmoothTransformation)

        # set widget aspect ratio
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                        QtGui.QSizePolicy.Preferred)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)

        # magic numbers, taken empirically from shanks image
        self.x_offset = int(63 / 1628. * self.scaled_pixmap.width())
        self.dx =       int(379.02 / 1628. * self.scaled_pixmap.width())
        self.y_offset = int(165 / 2016. * self.scaled_pixmap.height())
        self.dy =       int(23 / 2016. * self.scaled_pixmap.height())

        self.widget_offset = (self.size().width() - self.scaled_pixmap.width()) / 2
        
        # initialize cursor at first index
        self.cursor = CursorRect(
                        self.x_offset + self.widget_offset,
                        self.y_offset + 3 * self.dy,
                        int(self.size().width() * .15),
                        int(self.size().height() * .07),
                        1)
        self.index = (0, 0)
        
        # create array of pad intensities
        self.intensities = []

        # create array of cursors to make glow
        self.pads = []
        for shank in range(5):
            # correct for slight alignment error due to integer rounding
            if shank >= 2:
                offset = 1
            else:
                offset = 0

            # initialize pad arrays
            self.pads.append([])
            self.intensities.append([])
            # allocate position and intensity
            for pad in range(204):
                self.intensities[shank].append((0, 0, 0, 255))
                if pad & 0x1 == False: # shank m column 0
                    self.pads[shank].append(CursorRect(
                                        self.x_offset - 1 + self.dx * shank + offset + self.widget_offset,
                                        2 + self.y_offset + pad,
                                        2, 2,
                                        1))
                else: # shank m column 1
                    self.pads[shank].append(CursorRect(
                                        self.x_offset + 1 + self.dx * shank + offset + self.widget_offset,
                                        2 + self.y_offset + pad - 1,
                                        2, 2,
                                        1))
        self.intensities = np.array(self.intensities)        

    def set_intensities(self, activity):
        activity_scaled = (activity - ACT_MIN) / (ACT_MAX - ACT_MIN)
        intensities = np.array(map(cmap, activity_scaled), dtype=np.uint8).flatten()
        self.intensities = intensities.reshape((5, 204, 3))
        self.repaint()

    def increment_channel(self):
        if self.index[1] < 96:
            self.set_index(self.index[0], self.index[1] + 1)

        else:
            if self.index[0] < 4:
                self.set_index(self.index[0] + 1, 0)

    def decrement_channel(self):
        if self.index[1] > 0:
            self.set_index(self.index[0], self.index[1] - 1)

        else:
            if self.index[0] > 0:
                self.set_index(self.index[0] - 1, 96) 

    def set_position(self, x, y):
        x_index, y_index = self.position_to_index(x, y)

        # get array index from pixel position
        new_x, new_y = self.index_to_position(x_index, y_index)

        self.cursor.move(new_x, new_y)
        self.repaint()
       
        shank = x_index
        row = y_index
        col = 0 
        self.chanSelected.emit((shank, row, col))
        self.index = (x_index, y_index)

    def set_index(self, x, y):
        new_x, new_y = self.index_to_position(x, y)

        self.cursor.move(new_x, new_y)
        self.repaint()
        
        shank = x
        row = y
        col = 0 
        self.chanSelected.emit((shank, row, col))
        self.index = (x, y)

    def position_to_index(self, pos_x, pos_y):
        x_index = ((pos_x + self.dx) - self.x_offset - self.widget_offset - self.cursor.w / 2) / self.dx
        if x_index < 0:
            x_index = 0
        if x_index > 4:
            x_index = 4
        
        y_index = ((pos_y + self.dy) - self.y_offset - self.cursor.h / 2) / self.dy
        if y_index < 0:
            y_index = 0
        if y_index > 96:
            y_index = 96

        return (x_index, y_index)

    def index_to_position(self, ind_x, ind_y):
        # get array index from pixel position
        new_x = (ind_x * self.dx) + self.x_offset + self.widget_offset #- self.cursor.w / 2
        new_y = (ind_y * self.dy) + self.y_offset #- self.cursor.h / 2
        
        # sanitize x position
        if new_x < self.x_offset + self.widget_offset:
            new_x = self.x_offset + self.widget_offset
        if new_x > (4 * self.dx) + self.x_offset + self.widget_offset:
            new_x = (4 * self.dx) + self.x_offset + self.widget_offset

        # sanitize y position
        if new_y < (0 * self.dy) + self.y_offset:
            new_y = (0 * self.dy) + self.y_offset
        if new_y > (96 * self.dy) + self.y_offset:
            new_y = (96 * self.dy) + self.y_offset

        # correct for slight alignment error due to integer rounding
        if ind_x >= 2:
            offset = 1
        else:
            offset = 0

        return (new_x + offset, new_y + 6)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        pen = painter.pen()
        pen.setStyle(Qt.NoPen)
        painter.setPen(pen)

        # draw image centrally in the widget
        point = QtCore.QPoint(0,0)
        point.setX((self.size().width() - self.scaled_pixmap.width())/2)
        point.setY((self.size().height() - self.scaled_pixmap.height())/2)
        painter.drawPixmap(point, self.scaled_pixmap)
        
        for shank in range(5):
            for pad in range(204):
                brush = QtGui.QBrush(QtGui.QColor(*tuple(self.intensities[shank, pad])))
                painter.setBrush(brush)
                painter.drawRoundedRect(*self.pads[shank][pad].params(), mode=Qt.RelativeSize)
        
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 64))
        painter.setBrush(brush)
        pen = painter.pen()
        pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRoundedRect(*self.cursor.params(), mode=Qt.RelativeSize)

    def mousePressEvent(self, event):
        self.moved = False
        if event.button() == QtCore.Qt.LeftButton:
            # center the cursor on the mouse
            self.cursor.move(event.pos().x() , event.pos().y())
            
            self.moved = True
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.moved:
            # center cursor
            self.cursor.move(event.pos().x(), event.pos().y())
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.moved:
            self.set_position(event.pos().x(), event.pos().y())
            self.moved = False

    def heightForWidth(self, width):
        return int((1622. / 2621.) * width)


if __name__ =="__main__":
    import sys
    def printSelection(tup):
        print 'coords selected: ', tup

    app = QtGui.QApplication(sys.argv)
    probeMap = ProbeMap(410, 'shanks.jpg')
    probeMap.chanSelected.connect(printSelection)
    probeMap.show()
    sys.exit(app.exec_())
