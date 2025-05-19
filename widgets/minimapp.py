from PyQt5.QtWidgets import QWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QFont

class Minimap(QWidget):
    def __init__(self, parent, text_widget: QTextEdit, linenumbers=None):
        super().__init__(parent)
        self.setFixedWidth(100)
        self.setAutoFillBackground(True)
        self.text_widget = text_widget
        self.linenumbers = linenumbers

        self.font_name = "Courier New"
        self.font_size = 6
        self.line_spacing = 9
        self.max_line_length = 50
        self.last_y = 0

        self.setMouseTracking(True)

        # Setup event filters
        self.text_widget.viewport().installEventFilter(self)
        self.text_widget.document().contentsChanged.connect(self.schedule_update)
        self.text_widget.verticalScrollBar().valueChanged.connect(self.schedule_update)

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_minimap)

    def schedule_update(self):
        self.update_timer.start(50)

    def update_minimap(self):
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#2e2e2e"))

        height = self.height()
        total_lines = self.text_widget.document().blockCount()
        lines_to_render = int(height / self.line_spacing)

        first_visible = self.text_widget.cursorForPosition(self.text_widget.viewport().rect().topLeft()).blockNumber()
        last_visible = min(first_visible + lines_to_render, total_lines)

        font = QFont(self.font_name, self.font_size)
        painter.setFont(font)
        painter.setPen(QColor("#909090"))

        block = self.text_widget.document().findBlockByNumber(first_visible)
        for idx in range(first_visible, last_visible):
            y_pos = (idx - first_visible) * self.line_spacing
            text = block.text().replace('\t', '    ')[:self.max_line_length]
            painter.drawText(2, y_pos + self.font_size, text)
            block = block.next()

        if self.linenumbers and self.linenumbers.isVisible():
            self.linenumbers.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.scroll_to_click(event.y())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self.on_drag(event.y())

    def wheelEvent(self, event):
        direction = -1 if event.angleDelta().y() > 0 else 1
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().value() + direction * 3
        )
        self.schedule_update()

    def scroll_to_click(self, y):
        total_lines = self.text_widget.document().blockCount()
        rel_y = y / self.height()
        target_line = max(0, min(int(rel_y * total_lines), total_lines - 1))
        cursor = self.text_widget.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, cursor.MoveAnchor, target_line)
        self.text_widget.setTextCursor(cursor)
        self.text_widget.centerCursor()
        self.last_y = y
        self.schedule_update()

    def on_drag(self, y):
        delta = (y - self.last_y) * 2
        self.text_widget.verticalScrollBar().setValue(
            self.text_widget.verticalScrollBar().value() + int(-delta)
        )
        self.last_y = y
        self.schedule_update()

    def eventFilter(self, obj, event):
        self.schedule_update()
        return super().eventFilter(obj, event)
