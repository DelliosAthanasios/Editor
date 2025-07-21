import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QColorDialog, QLabel, QComboBox, QTabWidget
)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QMouseEvent
from PyQt5.QtCore import Qt, QPoint, QRect

BASIC_COLORS = [
    '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF',
    '#808080', '#800000', '#808000', '#008000', '#800080', '#008080', '#000080', '#C0C0C0'
]

SHAPES = ['Freehand', 'Line', 'Rectangle', 'Ellipse']

class DiagrammSketchCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.current_color = QColor(BASIC_COLORS[0])
        self.current_shape = 'Freehand'
        self.drawing = False
        self.last_point = QPoint()
        self.shapes = []  # List of (shape, color, start, end, [points])
        self.temp_shape = None
        self.setMouseTracking(True)

    def set_color(self, color):
        self.current_color = QColor(color)

    def set_shape(self, shape):
        self.current_shape = shape

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = event.pos()
            self.last_point = event.pos()
            if self.current_shape == 'Freehand':
                self.temp_points = [event.pos()]
            else:
                self.temp_shape = (self.current_shape, self.current_color, self.start_point, self.start_point)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.drawing:
            if self.current_shape == 'Freehand':
                self.temp_points.append(event.pos())
                self.update()
            else:
                self.temp_shape = (self.current_shape, self.current_color, self.start_point, event.pos())
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.drawing:
            if self.current_shape == 'Freehand':
                self.shapes.append(('Freehand', self.current_color, list(self.temp_points)))
            else:
                self.shapes.append((self.current_shape, self.current_color, self.start_point, event.pos()))
            self.drawing = False
            self.temp_shape = None
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for shape in self.shapes:
            self.draw_shape(painter, shape)
        if self.drawing:
            if self.current_shape == 'Freehand' and hasattr(self, 'temp_points'):
                self.draw_shape(painter, ('Freehand', self.current_color, self.temp_points))
            elif self.temp_shape:
                self.draw_shape(painter, self.temp_shape)

    def draw_shape(self, painter, shape):
        if shape[0] == 'Freehand':
            points = shape[2]
            if len(points) > 1:
                pen = QPen(shape[1], 2)
                painter.setPen(pen)
                for i in range(1, len(points)):
                    painter.drawLine(points[i-1], points[i])
        elif shape[0] == 'Line':
            pen = QPen(shape[1], 2)
            painter.setPen(pen)
            painter.drawLine(shape[2], shape[3])
        elif shape[0] == 'Rectangle':
            pen = QPen(shape[1], 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0,0,0,0)))
            rect = self.rect_from_points(shape[2], shape[3])
            painter.drawRect(QRect(*rect))
        elif shape[0] == 'Ellipse':
            pen = QPen(shape[1], 2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0,0,0,0)))
            rect = self.rect_from_points(shape[2], shape[3])
            painter.drawEllipse(QRect(*rect))

    def rect_from_points(self, p1, p2):
        return min(p1.x(), p2.x()), min(p1.y(), p2.y()), abs(p1.x()-p2.x()), abs(p1.y()-p2.y())

class DiagrammSketchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        controls.addWidget(QLabel('Color:'))
        self.color_combo = QComboBox()
        for color in BASIC_COLORS:
            self.color_combo.addItem('', QColor(color))
            self.color_combo.setItemData(self.color_combo.count()-1, QColor(color), 8)
        self.color_combo.currentIndexChanged.connect(self.change_color)
        controls.addWidget(self.color_combo)
        controls.addWidget(QLabel('Shape:'))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(SHAPES)
        self.shape_combo.currentIndexChanged.connect(self.change_shape)
        controls.addWidget(self.shape_combo)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.canvas = DiagrammSketchCanvas()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.color_combo.setCurrentIndex(0)
        self.shape_combo.setCurrentIndex(0)

    def change_color(self, idx):
        color = BASIC_COLORS[idx]
        self.canvas.set_color(color)

    def change_shape(self, idx):
        shape = SHAPES[idx]
        self.canvas.set_shape(shape) 