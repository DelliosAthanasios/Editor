from PyQt5.QtWidgets import QWidget, QMenu, QPushButton, QApplication, QToolTip
from PyQt5.QtGui import QFont, QColor, QPainter, QFontMetrics
from PyQt5.QtCore import Qt, QTimer

class Minimap(QWidget):
    DEFAULT_WIDTH = 80
    MIN_WIDTH = 40
    MAX_WIDTH = 400
    MIN_FONT_SIZE = 2
    MAX_FONT_SIZE = 16
    MIN_LINE_SPACING = 2
    MAX_LINE_SPACING = 32
    RESIZE_HANDLE_WIDTH = 8

    def __init__(self, parent, text_widget, linenumbers=None, theme_data=None):
        super().__init__(parent)
        self.setFixedWidth(self.DEFAULT_WIDTH)
        self.setAutoFillBackground(True)
        self.text_widget = text_widget
        self.linenumbers = linenumbers

        self.font_name = "Courier New"
        self.font_size = 3
        self.line_spacing = 4
        self.max_line_length = 32
        self.last_y = 0

        self.resizing = False
        self.resize_start_pos = None
        self.resize_start_width = None
        self.setMouseTracking(True)
        self.zoom_focus_y = None

        self.plus_button = QPushButton("+", self)
        self.minus_button = QPushButton("-", self)
        self.left_button = QPushButton("←", self)
        self.right_button = QPushButton("→", self)
        self._setup_control_buttons()

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        self.text_widget.viewport().installEventFilter(self)
        self.text_widget.document().contentsChanged.connect(self.schedule_update)
        self.text_widget.verticalScrollBar().valueChanged.connect(self.schedule_update)
        self.text_widget.cursorPositionChanged.connect(self.schedule_update)

        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_minimap)

        QToolTip.setFont(QFont('SansSerif', 10))

        # THEME SUPPORT
        self.theme_data = theme_data or {}
        self.set_theme(self.theme_data)

    def set_theme(self, theme_data):
        self.theme_data = theme_data
        editor_colors = theme_data.get("editor", {})
        self.bg_color = QColor(editor_colors.get("background", "#2e2e2e"))
        self.text_color = QColor(editor_colors.get("line_number_foreground", "#909090"))
        self.indicator_color = QColor(editor_colors.get("selection_background", "#4c8aff"))
        self.update()

    def _setup_control_buttons(self):
        btn_size = 24
        btn_style = """
            QPushButton {
                background-color: #333333;
                color: #fff;
                border: 1px solid #444;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4c8aff;
            }
        """

        for btn in [self.plus_button, self.minus_button, self.left_button, self.right_button]:
            btn.setFixedSize(btn_size, btn_size)
            btn.setStyleSheet(btn_style)
            btn.setVisible(True)

        self.plus_button.setToolTip("Zoom in minimap")
        self.minus_button.setToolTip("Zoom out minimap")
        self.left_button.setToolTip("Make Minimap Narrower")
        self.right_button.setToolTip("Make Minimap Wider")

        self.plus_button.clicked.connect(self._zoom_in_button)
        self.minus_button.clicked.connect(self._zoom_out_button)
        self.left_button.clicked.connect(self._make_wider_button)
        self.right_button.clicked.connect(self._make_narrower_button)

        for btn in [self.plus_button, self.minus_button, self.left_button, self.right_button]:
            btn.raise_()

    def resizeEvent(self, event):
        btn_pad = 3
        btn_size = self.plus_button.height()
        right = self.width() - 2 * btn_size - btn_pad * 2
        top = btn_pad

        self.plus_button.move(right, top)
        self.minus_button.move(right + btn_size + btn_pad, top)
        self.left_button.move(right, top + btn_size + btn_pad)
        self.right_button.move(right + btn_size + btn_pad, top + btn_size + btn_pad)
        super().resizeEvent(event)

    def _zoom_in_button(self):
        self.zoom_at_point(self.height() // 2, zoom_in=True)

    def _zoom_out_button(self):
        self.zoom_at_point(self.height() // 2, zoom_in=False)

    def _make_wider_button(self):
        self.setFixedWidth(min(self.width() + 20, self.MAX_WIDTH))
        self.schedule_update()

    def _make_narrower_button(self):
        self.setFixedWidth(max(self.width() - 20, self.MIN_WIDTH))
        self.schedule_update()

    def zoom_at_point(self, y, zoom_in=True):
        pre_ratio = self._minimap_y_to_editor_ratio(y)
        if zoom_in and self.font_size < self.MAX_FONT_SIZE:
            self.font_size += 1
            self.line_spacing = min(self.line_spacing + 1, self.MAX_LINE_SPACING)
        elif not zoom_in and self.font_size > self.MIN_FONT_SIZE:
            self.font_size -= 1
            self.line_spacing = max(self.line_spacing - 1, self.MIN_LINE_SPACING)
        else:
            return
        self._keep_viewport_centered(y, pre_ratio)
        self.schedule_update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoom_in = event.angleDelta().y() > 0
            self.zoom_at_point(event.y(), zoom_in=zoom_in)
            return
        direction = -1 if event.angleDelta().y() > 0 else 1
        sb = self.text_widget.verticalScrollBar()
        sb.setValue(sb.value() + direction * 3)
        self.schedule_update()

    def mouseDoubleClickEvent(self, event):
        self.zoom_at_point(event.y(), zoom_in=True)

    def mouseMoveEvent(self, event):
        margin = self.RESIZE_HANDLE_WIDTH
        if self.resizing:
            delta = event.globalX() - self.resize_start_pos
            new_width = max(self.MIN_WIDTH, min(self.resize_start_width + delta, self.MAX_WIDTH))
            self.setFixedWidth(new_width)
            self.schedule_update()
            return
        if abs(event.x() - self.width()) < margin:
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        if event.buttons() & Qt.LeftButton and not self.resizing:
            self.on_drag(event.y())

    def mousePressEvent(self, event):
        margin = self.RESIZE_HANDLE_WIDTH
        if event.button() == Qt.LeftButton:
            if abs(event.x() - self.width()) < margin:
                self.resizing = True
                self.resize_start_pos = event.globalX()
                self.resize_start_width = self.width()
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.scroll_to_click(event.y())

    def mouseReleaseEvent(self, event):
        if self.resizing:
            self.resizing = False
            self.setCursor(Qt.ArrowCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        zoom_in_action = menu.addAction("Zoom In")
        zoom_out_action = menu.addAction("Zoom Out")
        menu.addSeparator()
        make_wider_action = menu.addAction("Make Minimap Wider")
        make_narrower_action = menu.addAction("Make Minimap Narrower")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == zoom_in_action:
            self._zoom_in_button()
        elif action == zoom_out_action:
            self._zoom_out_button()
        elif action == make_wider_action:
            self._make_wider_button()
        elif action == make_narrower_action:
            self._make_narrower_button()

    def schedule_update(self):
        self.update_timer.start(50)

    def update_minimap(self):
        self.update()

    def paintEvent(self, event):
        try:
            painter = QPainter(self)
            painter.fillRect(self.rect(), self.bg_color)

            widget_height = self.height()
            total_lines = self.text_widget.document().blockCount()
            if total_lines == 0:
                return

            lines_to_render = int(widget_height / self.line_spacing)
            sb = self.text_widget.verticalScrollBar()
            max_scroll = sb.maximum()
            scroll_ratio = (sb.value() / max(1, max_scroll))
            first_visible = int(scroll_ratio * (total_lines - lines_to_render))
            first_visible = max(0, first_visible)
            last_visible = min(first_visible + lines_to_render, total_lines)
            visible_lines = last_visible - first_visible

            total_content_height = visible_lines * self.line_spacing
            y_offset = (widget_height - total_content_height) // 2 if widget_height > total_content_height else 0

            font = QFont(self.font_name, self.font_size)
            painter.setFont(font)
            painter.setPen(self.text_color)
            fm = QFontMetrics(font)

            block = self.text_widget.document().findBlockByNumber(first_visible)
            for idx in range(first_visible, last_visible):
                y_pos = y_offset + (idx - first_visible) * self.line_spacing
                text = block.text().replace('\t', '    ')[:self.max_line_length]
                text_width = fm.width(text)
                x_pos = (self.width() - text_width) // 2 if self.width() > text_width else 2
                painter.drawText(x_pos, y_pos + fm.ascent(), text)
                block = block.next()

            if max_scroll > 0:
                ratio = self.text_widget.viewport().height() / max(1, self.text_widget.document().size().height() * self.text_widget.fontMetrics().height())
                indicator_height = int(ratio * widget_height)
                indicator_y = int(sb.value() / max(1, max_scroll) * (widget_height - indicator_height))
                painter.setBrush(self.indicator_color)
                painter.setPen(Qt.NoPen)
                painter.drawRect(0, indicator_y, self.width(), indicator_height)

            self._draw_resize_handle(painter)

            if self.linenumbers and self.linenumbers.isVisible():
                self.linenumbers.update()

        except Exception as e:
            print("Error in Minimap paintEvent:", e)

    def _draw_resize_handle(self, painter):
        margin = 2
        handle_w = self.RESIZE_HANDLE_WIDTH
        handle_h = self.RESIZE_HANDLE_WIDTH
        x0 = self.width() - handle_w - margin
        y0 = self.height() - handle_h - margin
        painter.setPen(QColor("#888"))
        for i in range(3):
            painter.drawLine(x0 + i*2, y0 + handle_h, x0 + handle_w, y0 + i*2)

    def scroll_to_click(self, y):
        total_lines = self.text_widget.document().blockCount()
        if total_lines == 0:
            return
        widget_height = self.height()
        rel_y = y / max(1, widget_height)
        sb = self.text_widget.verticalScrollBar()
        max_scroll = sb.maximum()
        target_scroll = int(rel_y * max_scroll)
        sb.setValue(target_scroll)
        self.last_y = y
        self.schedule_update()

    def on_drag(self, y):
        sb = self.text_widget.verticalScrollBar()
        widget_height = self.height()
        delta = (y - self.last_y)
        sb.setValue(sb.value() + int(delta * sb.maximum() / max(1, widget_height)))
        self.last_y = y
        self.schedule_update()

    def eventFilter(self, obj, event):
        self.schedule_update()
        return super().eventFilter(obj, event)

    def _minimap_y_to_editor_ratio(self, y):
        widget_height = self.height()
        return y / max(1, widget_height)

    def _keep_viewport_centered(self, y, old_ratio):
        sb = self.text_widget.verticalScrollBar()
        max_scroll = sb.maximum()
        new_scroll = int(old_ratio * max_scroll)
        sb.setValue(new_scroll)
