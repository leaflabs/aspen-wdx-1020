#!/usr/bin/env python2


class CursorRect():
    def __init__(self, x, y, width, height, rounding):
        self.h = height
        self.w = width
        self.x = x
        self.y = y
        self.r = rounding
    def move(self, x, y):
        self.x = x
        self.y = y
    def resize(self, w, h):
        self.w = w
        self.h = h
    def left(self):
        return self.x
    def right(self):
        return self.x + self.w
    def top(self):
        return self.y
    def bottom(self):
        return self.y + self.h
    def params(self):
        return (self.x - self.w / 2, self.y - self.h / 2, self.w, self.h, self.r, self.r)
