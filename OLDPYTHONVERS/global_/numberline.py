from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QFontMetrics, QPainter, QColor
from PyQt5.QtCore import QRect, Qt
from global_.theme_manager import theme_manager_singleton

class NumberLine(QWidget):
    def __init__(self, editor, theme_data=None):
        super().__init__(editor)
        self.editor = editor
        self.font = editor.font()
        self.setFont(self.font)
        self.setMinimumWidth(self.calculate_width())
        self.editor.textChanged.connect(self.updateWidth)
        self.editor.verticalScrollBar().valueChanged.connect(self.update)
        self.editor.cursorPositionChanged.connect(self.update)
        self.theme_data = theme_data or {}
        self.set_theme(self.theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        self.show()

    def set_theme(self, theme_data):
        self.theme_data = theme_data
        editor_colors = theme_data.get("editor", {})
        self.bg_color = QColor(editor_colors.get("line_number_background", "#222226"))
        self.text_color = QColor(editor_colors.get("line_number_foreground", "#909090"))
        self.update()

    def setFont(self, font):
        self.font = font
        super().setFont(font)
        self.setMinimumWidth(self.calculate_width())
        self.update()

    def calculate_width(self):
        fm = QFontMetrics(self.font)
        digits = max(2, len(str(max(1, self.editor.document().blockCount()))))
        return 10 + fm.width("9" * digits)

    def updateWidth(self):
        self.setMinimumWidth(self.calculate_width())
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.fillRect(event.rect(), self.bg_color)
            painter.setFont(self.font)
            fm = QFontMetrics(self.font)
            doc = self.editor.document()
            scroll_bar = self.editor.verticalScrollBar()
            scroll_value = scroll_bar.value()
            line_height = fm.lineSpacing()
            viewport_height = self.editor.viewport().height()
            y_offset = -scroll_value
            block = doc.firstBlock()
            block_number = 1
            layout = self.editor.document().documentLayout()
            while block.isValid():
                rect = layout.blockBoundingRect(block)
                block_top = rect.translated(0, y_offset).top()
                block_bottom = rect.translated(0, y_offset).bottom()
                if block_bottom < 0:
                    block = block.next()
                    block_number += 1
                    continue
                if block_top > viewport_height:
                    break
                painter.setPen(self.text_color)
                rect_to_draw = QRect(0, int(block_top), self.width(), line_height)
                painter.drawText(rect_to_draw, Qt.AlignRight | Qt.AlignVCenter, str(block_number))
                block = block.next()
                block_number += 1
        except Exception as e:
            print("Error in NumberLine paintEvent:", e) 