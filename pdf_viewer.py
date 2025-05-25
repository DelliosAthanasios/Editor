import sys
import os
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QHBoxLayout, QSlider, QScrollArea,
    QLineEdit, QListWidget, QDockWidget, QMessageBox,
    QTabWidget, QComboBox, QGridLayout, QAction, QMenu, QMenuBar, QStyle,
    QInputDialog, QShortcut, QFormLayout, QListWidgetItem, QColorDialog, QDialog, QFontDialog, QTextEdit, QSpinBox
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon, QKeySequence, QMouseEvent, QFont
from PyQt5.QtCore import Qt, QSize, QEvent, QStandardPaths, QTimer, pyqtSignal, QObject, QPoint, QRectF

SETTINGS_FILE = os.path.join(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation), "pdf_viewer_settings.json")

DEFAULT_SHORTCUTS = {
    "Next Page": "Right",
    "Previous Page": "Left",
    "Search": "Ctrl+F",
    "Zoom In": "Ctrl++",
    "Zoom Out": "Ctrl+-",
    "Open PDF": "Ctrl+O",
    "Close Tab": "Ctrl+W",
    "Fullscreen": "F11",
    "Next Tab": "Ctrl+Tab",
    "Previous Tab": "Ctrl+Shift+Tab",
    "Scroll Up": "Up",
    "Scroll Down": "Down"
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception:
        pass

def update_recent_files(settings, file_path):
    if "recent_files" not in settings:
        settings["recent_files"] = []
    if file_path in settings["recent_files"]:
        settings["recent_files"].remove(file_path)
    settings["recent_files"].insert(0, file_path)
    settings["recent_files"] = settings["recent_files"][:10]
    save_settings(settings)

def get_shortcuts(settings):
    return settings.get("shortcuts", DEFAULT_SHORTCUTS.copy())

def set_shortcut(settings, name, keyseq):
    shortcuts = settings.get("shortcuts", DEFAULT_SHORTCUTS.copy())
    shortcuts[name] = keyseq
    settings["shortcuts"] = shortcuts
    save_settings(settings)

class SignalProxy(QObject):
    page_changed = pyqtSignal(int)

class Annotation:
    def __init__(self, annot_type, page, geometry, color="#FFFF00", text="", points=None, font_family="Arial", font_size=12):
        self.annot_type = annot_type  # highlight, underline, pen, sticky_note
        self.page = page
        self.geometry = geometry  # QRectF for highlight/underline/sticky_note, list of QPoint for pen
        self.color = color
        self.text = text
        self.points = points if points else []  # For pen
        self.font_family = font_family
        self.font_size = font_size

class StickyNoteDialog(QDialog):
    def __init__(self, color=QColor(255,255,200), font=QFont("Arial", 12), size=60, text=""):
        super().__init__()
        self.setWindowTitle("Sticky Note Settings")
        self.setModal(True)
        self.selected_color = color
        self.selected_font = font
        self.selected_size = size
        self.selected_text = text

        layout = QFormLayout(self)
        self.size_box = QSpinBox()
        self.size_box.setRange(20, 400)
        self.size_box.setValue(self.selected_size)
        layout.addRow("Size (px):", self.size_box)

        self.color_btn = QPushButton()
        self.color_btn.setStyleSheet(f"background-color: {self.selected_color.name()}")
        self.color_btn.clicked.connect(self.select_color)
        layout.addRow("Color:", self.color_btn)

        self.font_btn = QPushButton(f"{self.selected_font.family()}, {self.selected_font.pointSize()}pt")
        self.font_btn.clicked.connect(self.select_font)
        layout.addRow("Font:", self.font_btn)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.selected_text)
        layout.addRow("Message:", self.text_edit)

        btn_box = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.ok_btn)
        btn_box.addWidget(self.cancel_btn)
        layout.addRow(btn_box)

    def select_color(self):
        color = QColorDialog.getColor(self.selected_color, self)
        if color.isValid():
            self.selected_color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()}")

    def select_font(self):
        font, ok = QFontDialog.getFont(self.selected_font, self)
        if ok:
            self.selected_font = font
            self.font_btn.setText(f"{font.family()}, {font.pointSize()}pt")

    def get_values(self):
        return (self.size_box.value(), self.selected_color, self.selected_font, self.text_edit.toPlainText())

class PDFPageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.highlights = []
        self.underlines = []
        self.pen_drawings = []
        self.sticky_notes = []
        self.mouse_mode = None  # None, "highlight", "underline", "pen", "sticky_note"
        self._draw_color = QColor(255, 255, 0, 120)
        self._current_pen = []
        self._current_rect = None
        self._pdf_index = 0
        self._zoom = 1.0
        self.annotation_callback = None
        self.sticky_note_temp = None  # for placing new sticky note

    def set_zoom(self, zoom):
        self._zoom = zoom

    def set_pdf_index(self, pdf_index):
        self._pdf_index = pdf_index

    def set_annotations(self, highlights, underlines, pen_drawings, sticky_notes):
        self.highlights = highlights
        self.underlines = underlines
        self.pen_drawings = pen_drawings
        self.sticky_notes = sticky_notes
        self.update()

    def set_mouse_mode(self, mode, color=QColor(255,255,0,120)):
        self.mouse_mode = mode
        self._draw_color = color

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            # Highlights
            painter.setBrush(QColor(255, 255, 0, 120))
            painter.setPen(Qt.NoPen)
            for rect in self.highlights:
                painter.drawRect(rect)
            # Underlines
            painter.setPen(QPen(QColor(0, 128, 255, 180), 3))
            for rect in self.underlines:
                painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            # Pen drawings
            painter.setPen(QPen(QColor(255, 0, 0, 180), 2))
            for points in self.pen_drawings:
                if len(points) > 1:
                    for i in range(len(points)-1):
                        painter.drawLine(points[i], points[i+1])
            # Sticky notes
            for note in self.sticky_notes:
                rect = note['rect']
                color = note.get('color', QColor(255,255,200,220))
                font = note.get('font', QFont("Arial", 12))
                text = note['text']
                painter.setPen(QPen(QColor(0, 128, 0, 180), 1))
                painter.setBrush(color)
                painter.drawEllipse(rect)
                painter.setFont(font)
                painter.setPen(QColor(64, 64, 64))
                painter.drawText(rect, Qt.AlignCenter, "🗒")
            # Temp sticky note
            if self.sticky_note_temp:
                rect, color, font, text = self.sticky_note_temp
                painter.setPen(QPen(QColor(0, 128, 0, 180), 1))
                painter.setBrush(color)
                painter.drawEllipse(rect)
                painter.setFont(font)
                painter.setPen(QColor(64, 64, 64))
                painter.drawText(rect, Qt.AlignCenter, "🗒")

            # Current drawing
            painter.setPen(QPen(self._draw_color, 2, Qt.DashLine))
            if self.mouse_mode in ("highlight", "underline") and self._current_rect:
                painter.drawRect(self._current_rect)
            if self.mouse_mode == "pen" and len(self._current_pen) > 1:
                painter.setPen(QPen(self._draw_color, 2, Qt.SolidLine))
                for i in range(len(self._current_pen)-1):
                    painter.drawLine(self._current_pen[i], self._current_pen[i+1])

    def mousePressEvent(self, event):
        if self.mouse_mode in ("highlight", "underline"):
            self._current_rect = QRectF(event.pos(), event.pos())
            self.update()
        elif self.mouse_mode == "pen":
            self._current_pen = [event.pos()]
            self.update()
        elif self.mouse_mode == "sticky_note" and self.sticky_note_temp:
            rect, color, font, text = self.sticky_note_temp
            center = event.pos()
            rect = QRectF(center.x()-rect.width()/2, center.y()-rect.height()/2, rect.width(), rect.height())
            if self.annotation_callback:
                self.annotation_callback("sticky_note", self._pdf_index, rect, text, color, font)
            self.sticky_note_temp = None
            self.update()
        else:
            # Right click for sticky note context menu
            for note in self.sticky_notes:
                rect = note['rect']
                if rect.contains(event.pos()):
                    if event.button() == Qt.RightButton:
                        self.show_sticky_note_menu(event.pos(), note)
                        return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.mouse_mode in ("highlight", "underline") and self._current_rect:
            self._current_rect.setBottomRight(event.pos())
            self.update()
        elif self.mouse_mode == "pen" and len(self._current_pen) > 0:
            self._current_pen.append(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.mouse_mode in ("highlight", "underline") and self._current_rect:
            rect = self._current_rect.normalized()
            if rect.width() > 5 and rect.height() > 5:
                if self.annotation_callback:
                    self.annotation_callback(self.mouse_mode, self._pdf_index, rect)
            self._current_rect = None
            self.update()
        elif self.mouse_mode == "pen" and len(self._current_pen) > 1:
            if self.annotation_callback:
                self.annotation_callback("pen", self._pdf_index, self._current_pen.copy())
            self._current_pen = []
            self.update()

    def set_sticky_note_temp(self, rect, color, font, text):
        self.sticky_note_temp = (rect, color, font, text)
        self.mouse_mode = "sticky_note"
        self.update()

    def clear_sticky_note_temp(self):
        self.sticky_note_temp = None
        self.mouse_mode = None
        self.update()

    def show_sticky_note_menu(self, pos, note):
        menu = QMenu(self)
        edit_action = menu.addAction("Edit Sticky Note")
        remove_action = menu.addAction("Remove Sticky Note")
        action = menu.exec_(self.mapToGlobal(pos))
        if action == edit_action:
            # Open dialog to edit
            dialog = StickyNoteDialog(note.get('color', QColor(255,255,200)),
                                     note.get('font', QFont("Arial", 12)),
                                     int(note['rect'].width()),
                                     note['text'])
            if dialog.exec_() == QDialog.Accepted:
                size, color, font, text = dialog.get_values()
                center = note['rect'].center()
                rect = QRectF(center.x()-size/2, center.y()-size/2, size, size)
                note['rect'] = rect
                note['color'] = color
                note['font'] = font
                note['text'] = text
                self.update()
                if self.annotation_callback:
                    self.annotation_callback("edit_sticky_note", self._pdf_index, note)
        elif action == remove_action:
            if self.annotation_callback:
                self.annotation_callback("remove_sticky_note", self._pdf_index, note)

class BookmarkPreviewWidget(QWidget):
    def __init__(self, tab, bookmarks):
        super().__init__()
        self.tab = tab
        self.bookmarks = bookmarks
        self.layout = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.layout.addLayout(self.grid)
        self.layout.addStretch(1)
        self.page_labels = []
        self.refresh()

    def refresh(self):
        for i in reversed(range(self.grid.count())):
            widget = self.grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self.page_labels = []
        cols = 2
        row, col = 0, 0
        sorted_bms = sorted(self.bookmarks.items(), key=lambda x: x[1])
        for title, page_num in sorted_bms:
            preview_label = QLabel()
            preview_label.setFixedSize(180, 270)
            preview_label.setAlignment(Qt.AlignCenter)
            preview = self.tab.get_page_preview(page_num, QSize(160, 240))
            if preview:
                preview_label.setPixmap(preview)
            page_label = QLabel(f"{title} (Page {page_num+1})")
            page_label.setAlignment(Qt.AlignCenter)
            container = QWidget()
            container_layout = QVBoxLayout()
            container_layout.addWidget(preview_label)
            container_layout.addWidget(page_label)
            container.setLayout(container_layout)
            def make_press_event(page):
                return lambda event: self.tab.parent_viewer.overview_navigate(page)
            container.mousePressEvent = make_press_event(page_num)
            self.grid.addWidget(container, row, col)
            self.page_labels.append(container)
            col += 1
            if col >= cols:
                col = 0
                row += 1

class ShortcutPanel(QDockWidget):
    def __init__(self, settings, update_callback):
        super().__init__("Shortcuts")
        self.settings = settings
        self.update_callback = update_callback
        self.widget = QWidget()
        self.form = QFormLayout()
        self.inputs = {}
        self.shortcuts = get_shortcuts(settings)
        for name, seq in self.shortcuts.items():
            btn = QPushButton(seq)
            btn.clicked.connect(lambda _, n=name: self.remap_shortcut(n))
            self.inputs[name] = btn
            self.form.addRow(QLabel(name), btn)
        self.widget.setLayout(self.form)
        self.setWidget(self.widget)

    def remap_shortcut(self, name):
        key, ok = QInputDialog.getText(self, "Remap Shortcut", f"Enter new shortcut for {name}:", text=self.shortcuts[name])
        if ok and key:
            set_shortcut(self.settings, name, key)
            self.inputs[name].setText(key)
            self.shortcuts[name] = key
            self.update_callback()

class PDFTab(QWidget):
    def __init__(self, parent=None, file_path=None, settings=None, signal_proxy=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.doc = None
        self.current_page = 0
        self.zoom = 1.5
        self.bookmarks = {}
        self.page_labels = []
        self.search_results = []
        self.current_search_index = -1
        self.file_path = file_path
        self.settings = settings or {}
        self.persist_key = self.file_path if self.file_path else ""
        self.signal_proxy = signal_proxy or SignalProxy()
        self.annotations = {}  # page_num -> [Annotation, ...]
        self.init_ui()
        self.restore_settings()

    def init_ui(self):
        self.label1 = PDFPageLabel()
        self.label2 = PDFPageLabel()
        self.label3 = PDFPageLabel()
        self.label4 = PDFPageLabel()
        self.page_labels = [self.label1, self.label2, self.label3, self.label4]
        for idx, label in enumerate(self.page_labels):
            label.hide()
            label.set_pdf_index(idx)
            label.annotation_callback = self.add_annotation_from_label
        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.prev_button = QPushButton("◀")
        self.next_button = QPushButton("▶")
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(5)
        self.zoom_slider.setMaximum(50)
        self.zoom_slider.setValue(int(self.zoom * 10))
        self.zoom_slider.setTickInterval(1)
        self.zoom_slider.setSingleStep(1)
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("Go to page")
        self.page_input.setFixedWidth(100)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text")
        self.search_input.setFixedWidth(200)
        self.search_prev_button = QPushButton("▲")
        self.search_prev_button.setFixedWidth(30)
        self.search_next_button = QPushButton("▼")
        self.search_next_button.setFixedWidth(30)
        self.bookmark_button = QPushButton("Add Bookmark")
        self.overview_button = QPushButton("Overview")

        self.annotation_mode_combo = QComboBox()
        self.annotation_mode_combo.addItems(["Select", "Highlight", "Underline", "Pen"])
        self.annotation_mode_combo.currentTextChanged.connect(self.annotation_mode_changed)
        self.annotation_color_btn = QPushButton("Color")
        self.annotation_color_btn.clicked.connect(self.choose_annotation_color)
        self.annotation_color = QColor(255, 255, 0, 120)

        # Sticky Note Button
        self.sticky_note_btn = QPushButton("Add Sticky Note")
        self.sticky_note_btn.clicked.connect(self.start_sticky_note_add)

        self.pages_combo = QComboBox()
        self.pages_combo.addItems(["1 page", "2 pages", "3 pages", "4 pages"])
        self.pages_combo.setCurrentIndex(1)
        self.pages_combo.currentIndexChanged.connect(self.change_page_count)
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        self.page_input.returnPressed.connect(self.goto_page)
        self.search_input.returnPressed.connect(self.search_text)
        self.search_prev_button.clicked.connect(self.prev_search_result)
        self.search_next_button.clicked.connect(self.next_search_result)
        self.bookmark_button.clicked.connect(self.add_bookmark)
        self.overview_button.clicked.connect(self.toggle_overview)

        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(QLabel("Zoom:"))
        nav_layout.addWidget(self.zoom_slider)
        nav_layout.addWidget(QLabel("Pages:"))
        nav_layout.addWidget(self.pages_combo)
        nav_layout.addWidget(self.page_input)
        nav_layout.addWidget(self.search_input)
        nav_layout.addWidget(self.search_prev_button)
        nav_layout.addWidget(self.search_next_button)
        nav_layout.addWidget(self.bookmark_button)
        nav_layout.addWidget(self.overview_button)
        nav_layout.addWidget(self.annotation_mode_combo)
        nav_layout.addWidget(self.annotation_color_btn)
        nav_layout.addWidget(self.sticky_note_btn)

        self.image_layout = QHBoxLayout()
        for label in self.page_labels:
            self.image_layout.addWidget(label)
        self.scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.image_layout)
        self.scroll_area.setWidget(scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.installEventFilter(self)
        # Search results panel
        self.search_results_list = QListWidget()
        self.search_results_list.setMaximumWidth(300)
        self.search_results_list.itemClicked.connect(self.search_result_clicked)
        self.search_results_list.hide()

        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        scroll_and_results = QHBoxLayout()
        scroll_and_results.addWidget(self.scroll_area)
        scroll_and_results.addWidget(self.search_results_list)
        main_layout.addLayout(scroll_and_results)
        self.setLayout(main_layout)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Wheel and source is self.scroll_area:
            delta = event.angleDelta().y()
            if delta > 0:
                self.prev_page()
            else:
                self.next_page()
            return True
        return super().eventFilter(source, event)

    def change_page_count(self, index):
        self.display_pages()
        self.save_settings()

    def get_page_count(self):
        return self.pages_combo.currentIndex() + 1

    def open_pdf(self, file_name):
        try:
            self.doc = fitz.open(file_name)
            self.current_page = 0
            self.bookmarks = {}
            self.file_path = file_name
            self.persist_key = file_name
            self.restore_settings()
            if self.parent_viewer:
                self.parent_viewer.bookmark_list.clear()
                self.parent_viewer.populate_overview_for_tab(self)
                self.parent_viewer.refresh_bookmark_preview()
            self.display_pages()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {str(e)}")
            return False

    def display_pages(self):
        if not self.doc:
            return
        page_count = self.get_page_count()
        total_pages = len(self.doc)
        self.page_label.setText(f"Page: {self.current_page + 1}-{min(self.current_page + page_count, total_pages)} / {total_pages}")
        for i in range(4):
            idx = self.current_page + i
            if i < page_count and idx < total_pages:
                self.show_page(self.page_labels[i], idx)
                self.page_labels[i].show()
                self.page_labels[i].set_zoom(self.zoom)
                self.page_labels[i].set_pdf_index(idx)
                highlights, underlines, pen_drawings, sticky_notes = self.get_annotations_for_label(idx)
                self.page_labels[i].set_annotations(highlights, underlines, pen_drawings, sticky_notes)
            else:
                self.page_labels[i].clear()
                self.page_labels[i].hide()
        self.save_settings()
        if self.parent_viewer:
            self.signal_page_changed()

    def show_page(self, label, index):
        page = self.doc.load_page(index)
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix)
        mode = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, mode).copy()
        pixmap = QPixmap.fromImage(img)
        label.setPixmap(pixmap)
        label.highlights = []
        label.update()

    def get_annotations_for_label(self, page_index):
        highlights, underlines, pen_drawings, sticky_notes = [], [], [], []
        for annot in self.annotations.get(page_index, []):
            if annot.annot_type == "highlight":
                highlights.append(annot.geometry)
            elif annot.annot_type == "underline":
                underlines.append(annot.geometry)
            elif annot.annot_type == "pen":
                pen_drawings.append(annot.points)
            elif annot.annot_type == "sticky_note":
                sticky_notes.append({
                    'rect': annot.geometry,
                    'text': annot.text,
                    'color': annot.color if isinstance(annot.color, QColor) else QColor(annot.color),
                    'font': QFont(annot.font_family, annot.font_size)
                })
        return highlights, underlines, pen_drawings, sticky_notes

    def annotation_mode_changed(self, mode):
        for label in self.page_labels:
            if mode == "Highlight":
                label.set_mouse_mode("highlight", self.annotation_color)
            elif mode == "Underline":
                label.set_mouse_mode("underline", self.annotation_color)
            elif mode == "Pen":
                label.set_mouse_mode("pen", self.annotation_color)
            else:
                label.set_mouse_mode(None)

    def choose_annotation_color(self):
        color = QColorDialog.getColor(self.annotation_color, self)
        if color.isValid():
            self.annotation_color = color
            self.annotation_mode_changed(self.annotation_mode_combo.currentText())

    def add_annotation_from_label(self, annot_type, pdf_index, geometry_or_points, text=None, color=None, font=None):
        if annot_type == "pen":
            annotation = Annotation("pen", pdf_index, None, color=self.annotation_color.name(), points=geometry_or_points)
        elif annot_type == "sticky_note":
            # geometry_or_points is rect, text, color, font
            annotation = Annotation("sticky_note", pdf_index, geometry_or_points, color=color, text=text,
                                    font_family=font.family(), font_size=font.pointSize())
        elif annot_type == "edit_sticky_note":
            # geometry_or_points is the note dict
            note = geometry_or_points
            for annot in self.annotations.get(pdf_index, []):
                if annot.annot_type == "sticky_note" and annot.geometry == note['rect']:
                    annot.geometry = note['rect']
                    annot.color = note['color']
                    annot.font_family = note['font'].family()
                    annot.font_size = note['font'].pointSize()
                    annot.text = note['text']
        elif annot_type == "remove_sticky_note":
            note = geometry_or_points
            new_annots = []
            for annot in self.annotations.get(pdf_index, []):
                if annot.annot_type == "sticky_note" and annot.geometry == note['rect']:
                    continue
                new_annots.append(annot)
            self.annotations[pdf_index] = new_annots
        else:
            annotation = Annotation(annot_type, pdf_index, geometry_or_points, color=self.annotation_color.name())
        if annot_type in ("pen", "highlight", "underline", "sticky_note"):
            self.annotations.setdefault(pdf_index, []).append(annotation)
        self.display_pages()

    def start_sticky_note_add(self):
        # Show dialog to set sticky note settings
        dialog = StickyNoteDialog()
        if dialog.exec_() == QDialog.Accepted:
            size, color, font, text = dialog.get_values()
            # Activate sticky note placement mode for all visible labels
            for label in self.page_labels:
                label.set_sticky_note_temp(QRectF(0,0,size,size), color, font, text)
            self._sticky_note_add_info = (size, color, font, text)
        else:
            for label in self.page_labels:
                label.clear_sticky_note_temp()
            self._sticky_note_add_info = None

    def next_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page + page_count < len(self.doc):
                self.current_page += page_count
                self.display_pages()
            else:
                self.current_page = len(self.doc) - page_count
                if self.current_page < 0:
                    self.current_page = 0
                self.display_pages()

    def prev_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page - page_count >= 0:
                self.current_page -= page_count
                self.display_pages()
            else:
                self.current_page = 0
                self.display_pages()

    def zoom_changed(self, value):
        self.zoom = value / 10.0
        self.display_pages()
        self.save_settings()

    def goto_page(self):
        if self.doc:
            try:
                page_num = int(self.page_input.text()) - 1
                if 0 <= page_num < len(self.doc):
                    self.current_page = page_num
                    self.display_pages()
                else:
                    QMessageBox.warning(self, "Invalid Page", "Page number out of range.")
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter a valid page number.")

    def search_text(self):
        if self.doc:
            query = self.search_input.text()
            if not query:
                return
            self.search_results = []
            self.search_results_list.clear()
            for page_num in range(len(self.doc)):
                page = self.doc.load_page(page_num)
                text_instances = page.search_for(query)
                for inst in text_instances:
                    snippet = self._get_text_snippet(page, inst, query)
                    item = QListWidgetItem(f"Page {page_num+1}: {snippet}")
                    item.setData(Qt.UserRole, (page_num, inst))
                    self.search_results_list.addItem(item)
                    self.search_results.append((page_num, inst))
            if self.search_results:
                self.current_search_index = 0
                self.highlight_search_result()
                self.search_results_list.show()
            else:
                QMessageBox.information(self, "Search", "Text not found.")
                self.search_results_list.hide()

    def _get_text_snippet(self, page, rect, query):
        text = page.get_textbox(rect)
        if not text:
            text = page.get_text()
        idx = text.lower().find(query.lower())
        if idx != -1:
            start = max(0, idx-20)
            end = min(len(text), idx+len(query)+20)
            return text[start:end].replace('\n', ' ')
        return text.strip()[:50]

    def search_result_clicked(self, item):
        page_num, rect = item.data(Qt.UserRole)
        self.current_page = page_num
        self.display_pages()
        self.highlight_search_result_for_rect(page_num, rect)

    def highlight_search_result_for_rect(self, page_num, rect):
        page_count = self.get_page_count()
        label_index = page_num - self.current_page
        if 0 <= label_index < page_count:
            label = self.page_labels[label_index]
            label.highlights = [(rect.x0 * self.zoom, rect.y0 * self.zoom,
                               rect.width * self.zoom, rect.height * self.zoom)]
            label.update()
        self.page_label.setText(f"Page: {self.current_page+1} / {len(self.doc)}")

    def highlight_search_result(self):
        if not self.search_results or self.current_search_index < 0:
            return
        page_num, rect = self.search_results[self.current_search_index]
        self.current_page = page_num
        self.display_pages()
        self.highlight_search_result_for_rect(page_num, rect)
        self.search_results_list.setCurrentRow(self.current_search_index)

    def next_search_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            self.highlight_search_result()

    def prev_search_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            self.highlight_search_result()

    def add_bookmark(self):
        if self.doc and self.parent_viewer:
            page_num = self.current_page
            title = f"Page {page_num + 1}"
            if title not in self.bookmarks:
                self.bookmarks[title] = page_num
                self.parent_viewer.bookmark_list.addItem(title)
                self.parent_viewer.refresh_bookmark_preview()

    def toggle_overview(self):
        if self.parent_viewer:
            self.parent_viewer.toggle_overview(tab=self)

    def get_page_preview(self, page_num, size=QSize(180, 270)):
        if not self.doc or page_num >= len(self.doc):
            return None
        page = self.doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(size.width()/page.rect.width, size.height()/page.rect.height))
        mode = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, mode).copy()
        pixmap = QPixmap.fromImage(img)
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def save_settings(self):
        if not self.file_path:
            return
        doc_settings = self.settings.get("documents", {})
        doc_settings[self.file_path] = {
            "zoom": self.zoom,
            "current_page": self.current_page,
            "pages_layout": self.pages_combo.currentIndex()
        }
        self.settings["documents"] = doc_settings
        save_settings(self.settings)

    def restore_settings(self):
        if not self.file_path:
            return
        doc_settings = self.settings.get("documents", {}).get(self.file_path, {})
        if doc_settings:
            self.zoom = doc_settings.get("zoom", 1.5)
            self.current_page = doc_settings.get("current_page", 0)
            pages_layout = doc_settings.get("pages_layout", 1)
            self.zoom_slider.setValue(int(self.zoom * 10))
            self.pages_combo.setCurrentIndex(pages_layout)
        else:
            self.zoom_slider.setValue(int(self.zoom * 10))
            self.pages_combo.setCurrentIndex(1)

    def signal_page_changed(self):
        if hasattr(self.parent_viewer, "_sync_overview_scroll"):
            self.parent_viewer._sync_overview_scroll(self.current_page)

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced PDF Viewer")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet(self.get_stylesheet())
        self.settings = load_settings()
        self.signal_proxy = SignalProxy()
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)
        self.create_menus()
        self.create_toolbar()
        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self.bookmark_navigate)
        self.bookmark_preview = BookmarkPreviewWidget(self.get_current_tab(), {})
        dock_widget = QWidget()
        vbox = QVBoxLayout()
        vbox.addWidget(self.bookmark_list)
        vbox.addWidget(self.bookmark_preview)
        dock_widget.setLayout(vbox)
        self.bookmark_dock.setWidget(dock_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bookmark_dock)
        self.overview_dock = QDockWidget("Overview", self)
        self.overview_widget = QWidget()
        self.overview_layout = QGridLayout()
        self.overview_widget.setLayout(self.overview_layout)
        self.overview_scroll = QScrollArea()
        self.overview_scroll.setWidget(self.overview_widget)
        self.overview_scroll.setWidgetResizable(True)
        self.overview_dock.setWidget(self.overview_scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.overview_dock)
        self.overview_dock.hide()
        self._overview_widgets = {}
        self.shortcuts_panel = ShortcutPanel(self.settings, self.rebind_shortcuts)
        self.addDockWidget(Qt.RightDockWidgetArea, self.shortcuts_panel)
        self.shortcuts_panel.hide()
        self.fullscreen = False
        self.setup_shortcuts()

    def get_stylesheet(self):
        return """
        QWidget {
            background-color: #1e1e1e;
            color: #f0f0f0;
            font-family: Arial;
            font-size: 14px;
        }
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #555;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #3c3c3c;
        }
        QLabel {
            color: #ffffff;
        }
        QLineEdit {
            background-color: #2d2d2d;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 4px;
            color: #ffffff;
        }
        QSlider::groove:horizontal {
            border: 1px solid #444;
            height: 8px;
            background: #333;
            margin: 2px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #888;
            border: 1px solid #444;
            width: 14px;
            margin: -4px 0;
            border-radius: 7px;
        }
        QListWidget {
            background-color: #2d2d2d;
            border: none;
            color: #ffffff;
        }
        QListWidget::item {
            padding: 5px;
            border-bottom: 1px solid #444;
        }
        QListWidget::item:hover {
            background-color: #3c3c3c;
        }
        QTabWidget::pane {
            border: none;
        }
        QTabBar::tab {
            background: #2d2d2d;
            color: #f0f0f0;
            padding: 8px;
            border: 1px solid #444;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background: #3c3c3c;
            border-bottom: 1px solid #3c3c3c;
        }
        QTabBar::tab:hover {
            background: #3c3c3c;
        }
        """

    def create_menus(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        file_menu = menubar.addMenu("&File")
        open_action = QAction("Open PDF...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self.open_pdf)
        file_menu.addAction(open_action)
        self.recent_menu = QMenu("Open Recent", self)
        file_menu.addMenu(self.recent_menu)
        self.update_recent_files_menu()
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menubar.addMenu("&View")
        self.toggle_bookmarks_action = QAction("Show/Hide Bookmarks", self, checkable=True)
        self.toggle_bookmarks_action.setChecked(True)
        self.toggle_bookmarks_action.triggered.connect(self._toggle_bookmarks)
        view_menu.addAction(self.toggle_bookmarks_action)
        self.toggle_overview_action = QAction("Show/Hide Overview", self, checkable=True)
        self.toggle_overview_action.triggered.connect(lambda: self.toggle_overview())
        view_menu.addAction(self.toggle_overview_action)
        self.fullscreen_action = QAction("Toggle Full Screen", self)
        self.fullscreen_action.setShortcut(QKeySequence("F11"))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(self.fullscreen_action)
        self.toggle_shortcuts_action = QAction("Show/Hide Shortcuts", self, checkable=True)
        self.toggle_shortcuts_action.setChecked(False)
        self.toggle_shortcuts_action.triggered.connect(self._toggle_shortcuts_panel)
        view_menu.addAction(self.toggle_shortcuts_action)
        settings_menu = menubar.addMenu("&Settings")
        settings_action = QAction("Preferences...", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

    def create_toolbar(self):
        toolbar = self.addToolBar("Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        open_icon = self.style().standardIcon(QStyle.SP_DialogOpenButton)
        self.open_button = QPushButton(open_icon, "Open PDF")
        self.open_button.clicked.connect(self.open_pdf)
        toolbar.addWidget(self.open_button)
        self.fullscreen_button = QPushButton("Full Screen")
        self.fullscreen_button.clicked.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_button)

    def open_pdf(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open PDF", "", "PDF Files (*.pdf)")
        for file_name in file_names:
            self.add_pdf_tab(file_name)
            update_recent_files(self.settings, file_name)
        self.update_recent_files_menu()

    def add_pdf_tab(self, file_name):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, "file_path") and tab.file_path == file_name:
                self.tab_widget.setCurrentWidget(tab)
                return
        tab = PDFTab(self, file_path=file_name, settings=self.settings, signal_proxy=self.signal_proxy)
        if tab.open_pdf(file_name):
            self.tab_widget.addTab(tab, os.path.basename(file_name))
            self.tab_widget.setCurrentWidget(tab)
            self.populate_overview_for_tab(tab)
            self.refresh_bookmark_preview()

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.bookmark_list.clear()
            self.clear_overview()
            self.refresh_bookmark_preview()

    def clear_overview(self):
        for i in reversed(range(self.overview_layout.count())):
            widget = self.overview_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        self._overview_widgets = {}

    def get_current_tab(self):
        return self.tab_widget.currentWidget()

    def bookmark_navigate(self, item):
        tab = self.get_current_tab()
        if tab and tab.doc:
            page_num = tab.bookmarks.get(item.text(), 0)
            tab.current_page = page_num
            tab.display_pages()
            self.populate_overview_for_tab(tab, center_page=page_num)

    def toggle_overview(self, tab=None):
        if self.overview_dock.isVisible():
            self.overview_dock.hide()
            self.toggle_overview_action.setChecked(False)
        else:
            self.overview_dock.show()
            self.toggle_overview_action.setChecked(True)
            if tab is None:
                tab = self.get_current_tab()
            if tab:
                self.populate_overview_for_tab(tab, center_page=tab.current_page)

    def populate_overview_for_tab(self, tab, center_page=0):
        self.clear_overview()
        if tab and tab.doc:
            cols = 3
            row = 0
            col = 0
            n = len(tab.doc)
            page_size = QSize(240, 360)
            start = max(0, center_page - 4)
            end = min(n, start + 12)
            if end - start < 12:
                start = max(0, end - 12)
            self._overview_widgets = {}
            for i in range(start, end):
                preview_label = QLabel()
                preview_label.setFixedSize(page_size)
                preview_label.setAlignment(Qt.AlignCenter)
                preview = tab.get_page_preview(i, page_size)
                if preview:
                    preview_label.setPixmap(preview)
                page_label = QLabel(f"Page {i + 1}")
                page_label.setAlignment(Qt.AlignCenter)
                container = QWidget()
                container_layout = QVBoxLayout()
                container_layout.addWidget(preview_label)
                container_layout.addWidget(page_label)
                container.setLayout(container_layout)
                def make_press_event(page):
                    return lambda event: self.overview_navigate(page)
                container.mousePressEvent = make_press_event(i)
                self.overview_layout.addWidget(container, row, col)
                self._overview_widgets[i] = container
                col += 1
                if col >= cols:
                    col = 0
                    row += 1
            QTimer.singleShot(200, lambda: self._sync_overview_scroll(center_page))

    def _sync_overview_scroll(self, page_num):
        if page_num in self._overview_widgets:
            widget = self._overview_widgets[page_num]
            y = widget.y()
            self.overview_scroll.verticalScrollBar().setValue(y)

    def overview_navigate(self, page_num):
        tab = self.get_current_tab()
        if tab and tab.doc:
            tab.current_page = page_num
            tab.display_pages()
            self.populate_overview_for_tab(tab, center_page=page_num)

    def update_recent_files_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.get("recent_files", [])
        for path in recent_files:
            if os.path.isfile(path):
                action = QAction(os.path.basename(path), self)
                action.setToolTip(path)
                action.triggered.connect(lambda checked, p=path: self.add_pdf_tab(p))
                self.recent_menu.addAction(action)
        self.recent_menu.setEnabled(bool(recent_files))

    def show_settings_dialog(self):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Settings")
        dlg.setText("Settings are persisted per document and overall for recent files.\n"
                    "You can clear recent files from here.")
        clear_button = dlg.addButton("Clear Recent Files", QMessageBox.ActionRole)
        dlg.addButton("Close", QMessageBox.RejectRole)
        dlg.exec_()
        if dlg.clickedButton() == clear_button:
            self.settings["recent_files"] = []
            save_settings(self.settings)
            self.update_recent_files_menu()
            QMessageBox.information(self, "Cleared", "Recent files list cleared.")

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.showFullScreen()
            self.fullscreen = True
            self.fullscreen_button.setText("Exit Full Screen")
        else:
            self.showNormal()
            self.fullscreen = False
            self.fullscreen_button.setText("Full Screen")

    def setup_shortcuts(self):
        self.shortcuts = {}
        self.shortcut_name_map = {
            "Next Page": self.next_page_shortcut,
            "Previous Page": self.prev_page_shortcut,
            "Search": self.focus_search,
            "Zoom In": self.zoom_in,
            "Zoom Out": self.zoom_out,
            "Open PDF": self.open_pdf,
            "Close Tab": self.close_current_tab,
            "Fullscreen": self.toggle_fullscreen,
            "Next Tab": self.next_tab,
            "Previous Tab": self.prev_tab,
            "Scroll Up": self.scroll_up,
            "Scroll Down": self.scroll_down
        }
        self.rebind_shortcuts()

    def rebind_shortcuts(self):
        for sc in getattr(self, 'shortcuts', {}).values():
            try: sc.setParent(None)
            except Exception: pass
        self.shortcuts = {}
        mappings = get_shortcuts(self.settings)
        for name, func in self.shortcut_name_map.items():
            keyseq = mappings.get(name, DEFAULT_SHORTCUTS.get(name))
            if keyseq:
                shortcut = QShortcut(QKeySequence(keyseq), self)
                shortcut.activated.connect(func)
                self.shortcuts[name] = shortcut

    def prev_page_shortcut(self):
        tab = self.get_current_tab()
        if tab:
            tab.prev_page()

    def next_page_shortcut(self):
        tab = self.get_current_tab()
        if tab:
            tab.next_page()

    def focus_search(self):
        tab = self.get_current_tab()
        if tab:
            tab.search_input.setFocus()

    def zoom_in(self):
        tab = self.get_current_tab()
        if tab:
            v = tab.zoom_slider.value()
            if v < tab.zoom_slider.maximum():
                tab.zoom_slider.setValue(v + 1)

    def zoom_out(self):
        tab = self.get_current_tab()
        if tab:
            v = tab.zoom_slider.value()
            if v > tab.zoom_slider.minimum():
                tab.zoom_slider.setValue(v - 1)

    def close_current_tab(self):
        i = self.tab_widget.currentIndex()
        if i >= 0:
            self.close_tab(i)

    def next_tab(self):
        idx = self.tab_widget.currentIndex()
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((idx + 1) % count)

    def prev_tab(self):
        idx = self.tab_widget.currentIndex()
        count = self.tab_widget.count()
        if count > 1:
            self.tab_widget.setCurrentIndex((idx - 1 + count) % count)

    def scroll_up(self):
        tab = self.get_current_tab()
        if tab:
            tab.prev_page()

    def scroll_down(self):
        tab = self.get_current_tab()
        if tab:
            tab.next_page()

    def _toggle_bookmarks(self):
        if self.bookmark_dock.isVisible():
            self.bookmark_dock.hide()
            self.toggle_bookmarks_action.setChecked(False)
        else:
            self.bookmark_dock.show()
            self.toggle_bookmarks_action.setChecked(True)
            self.refresh_bookmark_preview()

    def _toggle_shortcuts_panel(self):
        if self.shortcuts_panel.isVisible():
            self.shortcuts_panel.hide()
            self.toggle_shortcuts_action.setChecked(False)
        else:
            self.shortcuts_panel.show()
            self.toggle_shortcuts_action.setChecked(True)

    def refresh_bookmark_preview(self):
        tab = self.get_current_tab()
        if tab:
            self.bookmark_preview.tab = tab
            self.bookmark_preview.bookmarks = tab.bookmarks
            self.bookmark_preview.refresh()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec_())