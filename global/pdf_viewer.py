import sys
import os
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QHBoxLayout, QScrollArea,
    QLineEdit, QListWidget, QDockWidget, QMessageBox,
    QTabWidget, QComboBox, QGridLayout, QAction, QMenuBar, QMenu, QStyle, QShortcut, QListWidgetItem,
    QDialog, QDialogButtonBox, QRadioButton, QButtonGroup, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QFont, QColor, QPalette
from PyQt5.QtCore import Qt, QSize, QEvent, QStandardPaths, QTimer, pyqtSignal, QObject
from theme_manager import theme_manager_singleton, get_editor_styles

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

class PDFPageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self._zoom = 1.0
        self._pdf_index = 0

    def set_zoom(self, zoom):
        self._zoom = zoom

    def set_pdf_index(self, pdf_index):
        self._pdf_index = pdf_index

class SearchScopeDialog(QDialog):
    def __init__(self, parent, last_pages=None):
        super().__init__(parent)
        self.setWindowTitle("Search options")
        self.setModal(True)
        layout = QVBoxLayout(self)

        self.scope_group = QButtonGroup(self)
        self.radio_whole = QRadioButton('Search in whole document (this process may take some time)')
        self.radio_current = QRadioButton('Search on current page')
        self.radio_range = QRadioButton('Search on specific page/pages')
        self.scope_group.addButton(self.radio_whole)
        self.scope_group.addButton(self.radio_current)
        self.scope_group.addButton(self.radio_range)

        layout.addWidget(self.radio_whole)
        layout.addWidget(self.radio_current)
        layout.addWidget(self.radio_range)

        self.range_input = QLineEdit()
        self.range_input.setPlaceholderText("e.g. 1-6, 3, 5-7,10")
        self.range_input.setEnabled(False)
        layout.addWidget(self.range_input)
        self.radio_range.toggled.connect(self.range_input.setEnabled)

        self.radio_whole.setChecked(True)
        if last_pages:
            self.range_input.setText(last_pages)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_scope(self):
        if self.radio_whole.isChecked():
            return 'whole', None
        if self.radio_current.isChecked():
            return 'current', None
        if self.radio_range.isChecked():
            return 'range', self.range_input.text().strip()
        return None, None

class ImprovedOverview(QWidget):
    def __init__(self, tab, window_size=7):
        super().__init__()
        self.tab = tab
        self.window_size = window_size
        self.layout = QGridLayout()  # Only create, do not set as widget layout
        self.thumb_cache = {}
        self.page_count = 0
        self.cols = 1
        self.thumb_size = QSize(180, 250)
        self.scroll_area = None

        # Navigation arrows for overview panel
        self.prev_button = QPushButton("◀")
        self.prev_button.setFixedWidth(28)
        self.prev_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.next_button = QPushButton("▶")
        self.next_button.setFixedWidth(28)
        self.next_button.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.prev_button.clicked.connect(self.prev_window)
        self.next_button.clicked.connect(self.next_window)
        self.arrow_layout = QHBoxLayout()
        self.arrow_layout.setContentsMargins(0,0,0,0)
        self.arrow_layout.setSpacing(2)
        self.arrow_layout.addWidget(self.prev_button)
        self.arrow_layout.addStretch()
        self.arrow_layout.addWidget(self.next_button)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(2)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_layout.addLayout(self.arrow_layout)
        self.main_layout.addLayout(self.layout)
        self.current_center = 0

    def set_tab(self, tab):
        self.tab = tab
        self.refresh()

    def set_scroll_area(self, scroll_area):
        self.scroll_area = scroll_area

    def update_layout_params(self, cols, thumb_size):
        self.cols = cols
        self.thumb_size = thumb_size
        self.refresh()

    def center_on_page(self, center_page):
        self.refresh(center_page)

    def prev_window(self):
        if not self.tab: return
        center = max(self.current_center - self.window_size, 0)
        self.refresh(center)

    def next_window(self):
        if not self.tab: return
        if not self.tab.doc: return
        lastpage = self.tab.doc.page_count-1
        center = min(self.current_center + self.window_size, lastpage)
        self.refresh(center)

    def refresh(self, center_page=None):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                self.layout.removeWidget(widget)
                widget.deleteLater()
        self.thumb_cache.clear()
        if not self.tab or not self.tab.doc:
            return
        self.page_count = self.tab.doc.page_count
        if center_page is None:
            center_page = self.tab.current_page
        self.current_center = center_page
        window_radius = self.window_size // 2
        start_page = max(center_page - window_radius, 0)
        end_page = min(center_page + window_radius + 1, self.page_count)
        # If at start or end, always fill window
        if end_page - start_page < self.window_size:
            if start_page == 0:
                end_page = min(self.window_size, self.page_count)
            elif end_page == self.page_count:
                start_page = max(self.page_count - self.window_size, 0)
        row, col = 0, 0
        for page_num in range(start_page, end_page):
            preview_label = QLabel()
            preview_label.setFixedSize(self.thumb_size)
            preview_label.setAlignment(Qt.AlignCenter)
            preview_label.setText("Loading...")
            def load_thumb(page_num=page_num, label=preview_label):
                pix = self.tab.get_page_preview(page_num, self.thumb_size)
                if pix:
                    label.setPixmap(pix)
                    label.setText("")
                    if page_num == center_page:
                        label.setStyleSheet("border: 3px solid #81a1c1; border-radius: 7px;")
                    else:
                        label.setStyleSheet("border: 1px solid #444; border-radius: 7px;")
            QTimer.singleShot(0, load_thumb)
            page_label = QLabel(f"Page {page_num+1}")
            page_label.setAlignment(Qt.AlignCenter)
            container = QWidget()
            container_layout = QVBoxLayout()
            container_layout.setContentsMargins(2, 2, 2, 2)
            container_layout.setSpacing(2)
            container_layout.addWidget(preview_label)
            container_layout.addWidget(page_label)
            container.setLayout(container_layout)
            def make_press_event(page):
                return lambda event: self.tab.parent_viewer.overview_navigate(page)
            container.mousePressEvent = make_press_event(page_num)
            self.layout.addWidget(container, row, col)
            col += 1
            if col >= self.cols:
                col = 0
                row += 1

class PDFTab(QWidget):
    def __init__(self, parent=None, file_path=None, settings=None, signal_proxy=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.doc = None
        self.current_page = 0
        self.zoom = 1.5
        self.bookmarks = {}
        self.page_labels = []
        self.page_cache = {}
        self._preview_cache = {}
        self.search_results = []
        self.current_search_index = -1
        self.file_path = file_path
        self.settings = settings or {}
        self.persist_key = self.file_path if self.file_path else ""
        self.signal_proxy = signal_proxy or SignalProxy()
        self.mode = 1
        self.animating = False
        self.last_search_pages = ""
        self.init_ui()
        self.restore_settings()

    def init_ui(self):
        font_button = QFont("Segoe UI", 10, QFont.Bold)
        font_label = QFont("Segoe UI", 11, QFont.Bold)
        font_input = QFont("Segoe UI", 10)

        self.label1 = PDFPageLabel()
        self.label2 = PDFPageLabel()
        self.page_labels = [self.label1, self.label2]
        for idx, label in enumerate(self.page_labels):
            label.hide()
            label.set_pdf_index(idx)
            label.setFont(font_label)
        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setFont(font_label)
        self.page_label.setStyleSheet("padding: 0 8px;")

        # Compact navigation bar
        self.prev_button = QPushButton("◀")
        self.prev_button.setFont(font_button)
        self.prev_button.setFixedSize(36, 28)
        self.next_button = QPushButton("▶")
        self.next_button.setFont(font_button)
        self.next_button.setFixedSize(36, 28)
        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFont(font_button)
        self.zoom_out_btn.setFixedSize(32, 28)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFont(font_button)
        self.zoom_in_btn.setFixedSize(32, 28)
        self.pages_combo = QComboBox()
        self.pages_combo.setFont(font_button)
        self.pages_combo.addItems(["1 page", "2 pages"])
        self.pages_combo.setFixedSize(80, 28)
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("Go to page")
        self.page_input.setFixedSize(70, 28)
        self.page_input.setFont(font_input)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search text")
        self.search_input.setFixedSize(90, 28)
        self.search_input.setFont(font_input)
        self.bookmark_button = QPushButton("Bookmark")
        self.bookmark_button.setFont(font_button)
        self.bookmark_button.setFixedSize(90, 28)
        self.overview_button = QPushButton("Overview")
        self.overview_button.setFont(font_button)
        self.overview_button.setFixedSize(90, 28)

        self.pages_combo.currentIndexChanged.connect(self.change_page_count)
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.page_input.returnPressed.connect(self.goto_page)
        self.search_input.returnPressed.connect(self.search_with_menu)
        self.bookmark_button.clicked.connect(self.add_bookmark)
        self.overview_button.clicked.connect(self.toggle_overview)

        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(6)
        nav_layout.setContentsMargins(4, 2, 4, 2)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.zoom_out_btn)
        nav_layout.addWidget(self.zoom_in_btn)
        nav_layout.addWidget(self.pages_combo)
        nav_layout.addWidget(self.page_input)
        nav_layout.addWidget(self.search_input)
        nav_layout.addWidget(self.bookmark_button)
        nav_layout.addWidget(self.overview_button)
        nav_layout.addStretch(1)

        self.image_layout = QHBoxLayout()
        self.image_layout.setSpacing(2)
        for label in self.page_labels:
            self.image_layout.addWidget(label)
        self.scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.image_layout)
        self.scroll_area.setWidget(scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setContentsMargins(0,0,0,0)
        self.search_results_list = QListWidget()
        self.search_results_list.setMaximumWidth(180)
        self.search_results_list.itemClicked.connect(self.search_result_clicked)
        self.search_results_list.hide()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addLayout(nav_layout)
        scroll_and_results = QHBoxLayout()
        scroll_and_results.setSpacing(2)
        scroll_and_results.addWidget(self.scroll_area)
        scroll_and_results.addWidget(self.search_results_list)
        main_layout.addLayout(scroll_and_results)
        self.setLayout(main_layout)
        self.setStyleSheet("background: #23272e;")

    def eventFilter(self, source, event):
        if event.type() == QEvent.Wheel and source is self.scroll_area:
            delta = event.angleDelta().y()
            if delta > 0:
                self.prev_page()
            else:
                self.next_page()
            if self.parent_viewer:
                self.parent_viewer.sync_overview_to_pdf()
            return True
        return super().eventFilter(source, event)

    def change_page_count(self, index):
        self.mode = index + 1
        self.display_pages()
        self.save_settings()
        if self.parent_viewer:
            self.parent_viewer.update_overview_layout()

    def get_page_count(self):
        return self.mode

    def open_pdf(self, file_name):
        try:
            self.doc = fitz.open(file_name)
            self.current_page = 0
            self.bookmarks = {}
            self.file_path = file_name
            self.persist_key = file_name
            self.page_cache = {}
            self._preview_cache = {}
            self.restore_settings()
            if self.parent_viewer:
                self.parent_viewer.bookmark_list.clear()
                self.parent_viewer.refresh_bookmark_preview()
                self.parent_viewer.set_overview_tab(self)
            self.display_pages()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {str(e)}")
            return False

    def display_pages(self, direction=0):
        if not self.doc:
            return
        page_count = self.get_page_count()
        total_pages = len(self.doc)
        self.page_label.setText(f"{self.current_page + 1}-{min(self.current_page + page_count, total_pages)} / {total_pages}")
        for i in range(2):
            idx = self.current_page + i
            if i < page_count and idx < total_pages:
                self.smooth_show_page(self.page_labels[i], idx, direction)
                self.page_labels[i].show()
                self.page_labels[i].set_zoom(self.zoom)
                self.page_labels[i].set_pdf_index(idx)
            else:
                self.page_labels[i].clear()
                self.page_labels[i].hide()
        self.save_settings()
        if self.parent_viewer:
            self.parent_viewer.sync_overview_to_pdf()

    def smooth_show_page(self, label, index, direction=0):
        page = self.doc.load_page(index)
        matrix = fitz.Matrix(self.zoom, self.zoom)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        label.setPixmap(pixmap)
        label.setStyleSheet("background: #222; border-radius: 7px;")

    def next_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page + page_count < len(self.doc):
                self.current_page += page_count
                self.display_pages(direction=1)
            else:
                self.current_page = len(self.doc) - page_count
                if self.current_page < 0:
                    self.current_page = 0
                self.display_pages(direction=1)

    def prev_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page - page_count >= 0:
                self.current_page -= page_count
                self.display_pages(direction=-1)
            else:
                self.current_page = 0
                self.display_pages(direction=-1)

    def zoom_in(self):
        self.zoom += 0.1
        if self.zoom > 5.0:
            self.zoom = 5.0
        self.display_pages()
        if self.parent_viewer:
            self.parent_viewer.update_overview_layout()

    def zoom_out(self):
        self.zoom -= 0.1
        if self.zoom < 0.2:
            self.zoom = 0.2
        self.display_pages()
        if self.parent_viewer:
            self.parent_viewer.update_overview_layout()

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

    def search_with_menu(self):
        dlg = SearchScopeDialog(self, last_pages=self.last_search_pages)
        if dlg.exec_() == QDialog.Accepted:
            scope, value = dlg.get_scope()
            if scope == 'whole':
                self.search_text(mode='all')
            elif scope == 'current':
                self.search_text(mode='current')
            elif scope == 'range':
                self.last_search_pages = value
                self.search_text(mode='range', pages_input=value)

    def search_text(self, mode='all', pages_input=None):
        if self.doc:
            query = self.search_input.text()
            if not query:
                return
            self.search_results = []
            self.search_results_list.clear()
            if mode == 'current':
                pages = [self.current_page]
            elif mode == 'range' and pages_input:
                pages = []
                for part in pages_input.split(','):
                    part = part.strip()
                    if '-' in part:
                        try:
                            a, b = map(int, part.split('-'))
                            pages.extend(list(range(a-1, b)))
                        except Exception:
                            pass
                    elif part.isdigit():
                        pages.append(int(part) - 1)
                pages = [p for p in pages if 0 <= p < len(self.doc)]
                pages = sorted(set(pages))
            else:
                pages = range(len(self.doc))
            for page_num in pages:
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

    def highlight_search_result(self):
        if not self.search_results or self.current_search_index < 0:
            return
        page_num, rect = self.search_results[self.current_search_index]
        self.current_page = page_num
        self.display_pages()
        self.search_results_list.setCurrentRow(self.current_search_index)

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

    def get_page_preview(self, page_num, size=QSize(100, 140)):
        key = (page_num, size.width(), size.height(), round(self.zoom, 2))
        if key in self._preview_cache:
            return self._preview_cache[key]
        if not self.doc or page_num >= len(self.doc):
            return None
        try:
            page = self.doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(size.width()/page.rect.width, size.height()/page.rect.height))
            mode = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, mode).copy()
            pixmap = QPixmap.fromImage(img)
            pixmap = pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._preview_cache[key] = pixmap
            return pixmap
        except Exception:
            return None

    def save_settings(self):
        if not self.file_path:
            return
        doc_settings = self.settings.get("documents", {})
        doc_settings[self.file_path] = {
            "zoom": self.zoom,
            "current_page": self.current_page,
            "pages_layout": self.mode - 1
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
            pages_layout = doc_settings.get("pages_layout", 0)
            self.pages_combo.setCurrentIndex(pages_layout)
            self.mode = pages_layout + 1
        else:
            self.pages_combo.setCurrentIndex(0)
            self.mode = 1

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minimalist PDF Viewer")
        self.setGeometry(100, 100, 1000, 700)
        # Theme integration
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
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
        self.bookmark_list.setMaximumWidth(160)
        self.bookmark_list.itemClicked.connect(self.bookmark_navigate)
        self.bookmark_preview = QLabel("No bookmarks")
        dock_widget = QWidget()
        vbox = QVBoxLayout()
        vbox.setContentsMargins(3, 3, 3, 3)
        vbox.setSpacing(4)
        vbox.addWidget(self.bookmark_list)
        vbox.addWidget(self.bookmark_preview)
        dock_widget.setLayout(vbox)
        self.bookmark_dock.setWidget(dock_widget)
        self.bookmark_dock.setMinimumWidth(160)
        self.bookmark_dock.setMaximumWidth(200)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bookmark_dock)
        self.overview_dock = QDockWidget("Overview", self)
        self.overview_tab = None
        self.overview_scroll = QScrollArea()
        self.overview_widget = ImprovedOverview(None, window_size=7)
        self.overview_scroll.setWidget(self.overview_widget)
        self.overview_scroll.setWidgetResizable(True)
        self.overview_dock.setWidget(self.overview_scroll)
        self.overview_dock.setMinimumWidth(220)
        self.overview_dock.setMaximumWidth(800)
        self.addDockWidget(Qt.RightDockWidgetArea, self.overview_dock)
        self.overview_dock.hide()
        self.fullscreen = False
        self.setup_shortcuts()

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        app = QApplication.instance()
        from theme_manager import apply_theme_palette
        apply_theme_palette(app, theme_data)
        self.setStyleSheet(f"""
            QMainWindow {{ background: {palette['window']}; color: {palette['window_text']}; }}
            QWidget {{ background-color: {palette['window']}; color: {palette['window_text']}; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }}
            QPushButton {{ background: {palette['button']}; border: none; color: {palette['button_text']}; padding: 6px 14px; border-radius: 7px; min-width: 34px; min-height: 28px; font-weight: bold; }}
            QPushButton:pressed {{ background: {palette['mid']}; }}
            QPushButton:hover {{ background: {palette['highlight']}; color: {palette['highlight_text']}; }}
            QLabel {{ color: {palette['window_text']}; }}
            QLineEdit {{ background: {palette['base']}; border: 1px solid {palette['mid']}; color: {palette['text']}; padding: 5px; border-radius: 7px; min-height: 26px; font-size: 11pt; }}
            QSlider::groove:horizontal {{ border: 1px solid {palette['mid']}; height: 8px; background: {palette['alternate_base']}; margin: 2px 0; border-radius: 4px; }}
            QSlider::handle:horizontal {{ background: {palette['highlight']}; border: 1px solid {palette['mid']}; width: 14px; margin: -4px 0; border-radius: 8px; }}
            QListWidget {{ background-color: {palette['base']}; border: none; color: {palette['text']}; }}
            QListWidget::item {{ padding: 5px; border-bottom: 1px solid {palette['mid']}; }}
            QListWidget::item:hover {{ background-color: {palette['highlight']}; color: {palette['highlight_text']}; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ background: {palette['base']}; color: {palette['text']}; padding: 8px; border: none; border-top-left-radius: 8px; border-top-right-radius: 8px; font-weight: bold; font-size: 11pt; }}
            QTabBar::tab:selected {{ background: {palette['highlight']}; color: {palette['highlight_text']}; }}
            QTabBar::tab:hover {{ background: {palette['mid']}; }}
            QScrollArea {{ background: {palette['base']}; }}
        """)

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

    def create_toolbar(self):
        toolbar = self.addToolBar("Toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        self.open_button = QPushButton("Open PDF")
        self.open_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.open_button.setFixedSize(120, 36)
        self.open_button.setStyleSheet("QPushButton {background: #3a6df0; border-radius: 8px; color: #fff; font-weight: bold; border: none;} QPushButton:pressed {background: #3457b1;}")
        self.open_button.clicked.connect(self.open_pdf)
        toolbar.addWidget(self.open_button)
        self.fullscreen_button = QPushButton("Full Screen")
        self.fullscreen_button.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.fullscreen_button.setFixedSize(120, 36)
        self.fullscreen_button.setStyleSheet("QPushButton {background: #444a58; border-radius: 8px; color: #fff; font-weight: bold; border: none;} QPushButton:pressed {background: #2d3340;}")
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
            self.set_overview_tab(tab)
            self.refresh_bookmark_preview()

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.bookmark_list.clear()
            self.overview_widget.set_tab(None)
            self.overview_widget.refresh()
            self.bookmark_preview.setText("No bookmarks")

    def get_current_tab(self):
        return self.tab_widget.currentWidget()

    def bookmark_navigate(self, item):
        tab = self.get_current_tab()
        if tab and tab.doc:
            page_num = tab.bookmarks.get(item.text(), 0)
            tab.current_page = page_num
            tab.display_pages()
            self.sync_overview_to_pdf()

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
                self.set_overview_tab(tab)

    def set_overview_tab(self, tab):
        self.overview_tab = tab
        cols = 1 if tab.mode == 1 else 2
        thumb_size = QSize(180, 250) if cols == 1 else QSize(120, 160)
        self.overview_widget.set_tab(tab)
        self.overview_widget.update_layout_params(cols, thumb_size)
        self.overview_widget.set_scroll_area(self.overview_scroll)
        self.sync_overview_to_pdf()

    def update_overview_layout(self):
        tab = self.get_current_tab()
        if tab:
            self.set_overview_tab(tab)

    def sync_overview_to_pdf(self):
        tab = self.get_current_tab()
        if not tab or not tab.doc or not self.overview_tab:
            return
        self.overview_widget.center_on_page(tab.current_page)

    def overview_navigate(self, page_num):
        tab = self.get_current_tab()
        if tab and tab.doc:
            tab.current_page = page_num
            tab.display_pages()

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
            tab.zoom_in()

    def zoom_out(self):
        tab = self.get_current_tab()
        if tab:
            tab.zoom_out()

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

    def refresh_bookmark_preview(self):
        tab = self.get_current_tab()
        if tab and tab.bookmarks:
            bookmarks = "\n".join([f"{t}: p{p+1}" for t, p in tab.bookmarks.items()])
            self.bookmark_preview.setText(bookmarks)
        else:
            self.bookmark_preview.setText("No bookmarks")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec_())