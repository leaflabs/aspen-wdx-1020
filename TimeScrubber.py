#!/usr/bin/env python2

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

from CursorRect import CursorRect

class ScrubberLabel(QtGui.QLabel):
    def __init__(self, text, size):
        super(ScrubberLabel, self).__init__(text)
        self.set_colors('5F5F5F')
        self.setAlignment(Qt.AlignCenter)
        self.set_font_size(size)
        
    def resizeEvent(self, event):
        size = self.fontMetrics().boundingRect(self.text())
        self.setFixedWidth(size.width() * 1.25)
        self.setFixedHeight(size.height() * 1.25)

    def set_colors(self, color, background='0F0F0F', border='5F5F5F'):
        style_sheet = ( "color: #{0};" +
                        "background-color: #{1};" +
                        "border: 1px solid;" +
                        "border-color: #{2};").format(  color,
                                                        background,
                                                        border)
        self.setStyleSheet(style_sheet)

    def set_font_size(self, size):
        font = self.font()
        font.setPointSize(size)
        self.setFont(font)

    def set_position(self, x, tier, parent_height):
        self.move(x, tier * (self.size().height()) + parent_height / 2)


class TimeScrubber(QtGui.QLabel):

    timeSelected= QtCore.pyqtSignal(int)

    def __init__(self, num, img=None):
        super(TimeScrubber, self).__init__()
        self.setFrameStyle(QtGui.QFrame.StyledPanel)
        self.setStyleSheet("background-color: #0F0F0F")

        self.labels = []
        self.labels_pos = []

        self.num_samples = num
        
        if self.num_samples / 30000. <= 1.:
            self.time_divisor = 30.
            self.time_designator = " ms"
        elif self.num_samples / 30000. <= 60.:
            self.time_divisor = 30000.
            self.time_designator = " s"
        elif self.num_samples / 30000. <= 60 * 60.:
            self.time_divisor = (30000. * 60)
            self.time_designator = " min"
        elif self.num_samples / 30000. <= 60 * 60 * 12:
            self.time_divisor = (30000. * 60 * 60)
            self.time_designator = " hr"
        else:
            self.time_divisor = (30000. * 60 * 60 * 24)
            self.time_designator = " days"

        self.index = 0

        self.pixmap = None
        if img != None:
            self.pixmap = QtGui.QPixmap(img)
            self.scaled_pixmap = self.pixmap.scaled(self.size())

        # initialize cursor at first index
        self.cursor = CursorRect(  (60000 / float(self.num_samples) * self.size().width()) / 2,
                                    self.size().height() / 2,
                                    60000 / float(self.num_samples) * self.size().width(),
                                    self.size().height() * 1 / 2,
                                    1)

        # define range indicator
        self.ranger = CursorRect(  self.size().width() / 2, self.size().height() / 2,
                                    self.size().width(), 2,
                                    1)

        # axis marks
        self.major_ticks = []
        self.minor_ticks = []
        self.sub_m_ticks = []
        major_width = self.size().width() / 4
        minor_width = major_width / 4
        subminor_width = minor_width / 4
        y_offset = self.size().height() / 2 
        maj_height = int(self.size().height() * .1)
        min_height = int(self.size().height() * 0.05)
        sub_height = int(self.size().height() * 0.025)
        for i in range(5):
            x_offset = i * major_width
            maj_tic = CursorRect(  x_offset, y_offset,
                                    2, maj_height,
                                    1)
            if i < 4:
                for j in range(4):
                    x_min_offset = j * minor_width
                    if j > 0:
                        min_tic = CursorRect(  x_offset + x_min_offset, y_offset,
                                                2, min_height,
                                                1)
                    for k in range(3):
                        x_sub_offset = (k + 1) * subminor_width
                        sub_min_tic = CursorRect(  x_offset + x_min_offset + x_sub_offset, y_offset,
                                                    1, sub_height,
                                                    1)
                        self.sub_m_ticks.append(sub_min_tic)

                    if j > 0:
                        self.minor_ticks.append(min_tic)

            self.major_ticks.append(maj_tic)

        self.set_index(self.index)
        # self.place_label("butts", self.size().width() / 4, -1, 22, '5F5F5F')

    def place_label(self, text, position, tier, size, color):
        label = ScrubberLabel(text, size)
        label.set_colors(color)
        label.setParent(self)
        label.show()
        self.labels.append(label)
        self.labels_pos.append((position, tier))
        # self.repaint()
    
    def refresh_label_positions(self):
        for i, item in enumerate(self.labels):
            item.set_position(self.labels_pos[i][0], self.labels_pos[i][1], self.size().height())
            item.show()

    def increment_time(self):
        if self.index < self.num_samples - 60000:
            self.set_index(self.index + 60000)

        else:
            self.set_index(self.num_samples - 60000)

    def decrement_time(self):
        if self.index >= 60000:
            self.set_index(self.index - 60000)

    def set_index(self, i):
        self.index = i 
        x = int(i / float(self.num_samples) * self.size().width())
        self.set_cursor_position(x + self.cursor.w / 2)
        
        self.timeSelected.emit(self.index)
        self.repaint()

    def set_cursor_position(self, x):
        self.cursor.move(x, self.size().height() / 2)
        self.cursor_hat = [QtCore.QPoint(self.cursor.x, self.cursor.y - self.cursor.h / 2),
                QtCore.QPoint(self.cursor.x - 2.5, self.cursor.y - self.cursor.h / 2 - 5),
                QtCore.QPoint(self.cursor.x + 3.5, self.cursor.y - self.cursor.h / 2 - 5)]
        self.cursor_butt = [QtCore.QPoint(self.cursor.x, self.cursor.y + self.cursor.h / 2 - 1),
                QtCore.QPoint(self.cursor.x - 2.5, self.cursor.y + self.cursor.h / 2 + 5 - 1),
                QtCore.QPoint(self.cursor.x + 3.5, self.cursor.y + self.cursor.h / 2 + 5 - 1)]

    def resizeEvent(self, event):
        if self.pixmap != None:
            self.scaled_pixmap = self.pixmap.scaled(self.size())

        width = 1
        self.cursor.resize(width, self.size().height() / 2)
        self.set_cursor_position(self.cursor.x + self.cursor.w / 2)

        self.ranger.move(self.size().width() / 2, self.size().height() / 2)
        self.ranger.resize(self.size().width(), 2)

        major_width = self.size().width() / 4
        minor_width = major_width / 4
        subminor_width = minor_width / 4
        y_offset = self.size().height() / 2 
        maj_height = int(self.size().height() * .1)
        min_height = int(self.size().height() * 0.05)
        sub_height = int(self.size().height() * 0.025)
        for i in range(5):
            x_offset = i * major_width
            self.major_ticks[i].move(x_offset, y_offset)
            if i == 4:
                self.major_ticks[i].move(self.size().width()-1, y_offset)
            self.major_ticks[i].resize(2, maj_height)
            
            if i < 4:
                for j in range(4):
                    if  j < 3:
                        self.minor_ticks[i * 3 + j].move(x_offset + (j + 1) * minor_width, y_offset)
                        self.minor_ticks[i * 3 + j].resize(2, min_height)

                    for k in range(3):
                        self.sub_m_ticks[12 * i + 3 * j + k].move(x_offset + j * minor_width + (k + 1) * subminor_width, y_offset)
                        self.sub_m_ticks[12 * i + 3 * j + k].resize(1, sub_height)
        self.refresh_label_positions()
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if self.pixmap != None:
            point = QtCore.QPoint(0,0)
            point.setX((self.size().width() - self.scaled_pixmap.width())/2)
            point.setY((self.size().height() - self.scaled_pixmap.height())/2)
            painter.drawPixmap(point, self.scaled_pixmap)

        # draw axis line
        brush = QtGui.QBrush(QtGui.QColor(64, 64, 64, 255))
        painter.setBrush(brush)
        pen = painter.pen()
        pen.setStyle(Qt.NoPen)
        painter.setPen(pen)
        painter.drawRoundedRect(*self.ranger.params(), mode=Qt.RelativeSize)

        for i in range(5):
            # major tick
            painter.drawRoundedRect(*self.major_ticks[i].params(), mode=Qt.RelativeSize)

            painter.setFont(QtGui.QFont("Consolas", 9))
            painter.setPen(QtGui.QColor(64, 64, 64))
            if i > 0 and i < 4:
                rect = self.major_ticks[i].params()[:-2]
                rect = (rect[0] - 250, rect[1] + int(self.size().height() * 0.05), 500, 50)
                time = round(((i * self.size().width() / 4.0) / self.size().width()) * self.num_samples / self.time_divisor, 2)
                time = str(time) + self.time_designator
                painter.drawText(QtCore.QRect(*rect), Qt.AlignCenter, time)

            if i < 4:
                brush = QtGui.QBrush(QtGui.QColor(64, 64, 64, 255))
                painter.setBrush(brush)
                pen.setStyle(Qt.NoPen)
                painter.setPen(pen)
                for j in range(4):
                    if j < 3:
                        painter.drawRoundedRect(*self.minor_ticks[i * 3 + j].params(), mode=Qt.RelativeSize)
                        if j == 1:
                            painter.setFont(QtGui.QFont("Consolas", 7))
                            painter.setPen(QtGui.QColor(64, 64, 64))
                            rect = self.minor_ticks[i * 3 + j].params()[:-2]
                            rect = (rect[0] - 250, rect[1] - int(self.size().height() * 0.01), 500, 50)
                            time = round((self.minor_ticks[i * 3 + j].x / float(self.size().width())) * self.num_samples / self.time_divisor, 2)
                            time = str(time) + self.time_designator
                            painter.drawText(QtCore.QRect(*rect), Qt.AlignCenter, time)
                    pen.setStyle(Qt.NoPen)
                    painter.setPen(pen)
                    for k in range(3):
                        painter.drawRoundedRect(*self.sub_m_ticks[12 * i + 3 * j + k].params(), mode=Qt.RelativeSize)


        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255, 128))
        painter.setBrush(brush)
        pen = painter.pen()
        pen.setStyle(Qt.NoPen)
        painter.setPen(pen)
        painter.drawRoundedRect(*self.cursor.params(), mode=Qt.RelativeSize)
        painter.drawPolygon(QtGui.QPolygon(self.cursor_hat))
        painter.drawPolygon(QtGui.QPolygon(self.cursor_butt))

    def mousePressEvent(self, event):
        self.moved = False
        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            
            # center the cursor on the mouse
            self.set_cursor_position(pos.x())
            
            self.moved = True
            self.repaint()

    def mouseMoveEvent(self, event):
        if self.moved:
            pos = event.pos()
            
            # center cursor
            if pos.x() < 0:
                x = 0
            elif pos.x() > self.size().width() - 1:
                x = self.size().width() - 1
            else:
                x = pos.x()
            self.set_cursor_position(x)
            self.repaint()

    def mouseReleaseEvent(self, event):
        if self.moved:
            pos = event.pos().x()

            if pos < 0:
                pos = 0
            if pos > self.size().width():
                pos = self.size().width() - 1

            pos = int((pos / float(self.size().width())) * self.num_samples)
            self.set_index(pos)
            self.moved = False

if __name__ =="__main__":

    import sys

    app = QtGui.QApplication(sys.argv)
    widget = TimeScrubber(300000) # 10 seconds
    widget.resize(600,200)
    widget.show()
    sys.exit(app.exec_())
