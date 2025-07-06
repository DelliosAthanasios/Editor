import sys
import os
import json
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QHBoxLayout, QScrollArea,
    QLineEdit, QListWidget, QDockWidget, QMessageBox,
    QTabWidget, QComboBox, QGridLayout, QAction, QMenuBar, QMenu, QStyle, QShortcut, QListWidgetItem,
    QDialog, QDialogButtonBox, QRadioButton, QButtonGroup, QSizePolicy, QToolButton
)
from PyQt5.QtGui import QPixmap, QImage, QKeySequence, QFont, QColor, QPalette, QIcon
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

class LazyPDFPageLabel(QLabel):
    def __init__(self, pdf_tab, page_index, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pdf_tab = pdf_tab
        self.page_index = page_index
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setText(f"Page {page_index+1}")
        self._pixmap = None
        self._zoom = 1.5
        self._loaded = False

    def set_zoom(self, zoom):
        self._zoom = zoom
        self._loaded = False
        self.clear()
        self.setText(f"Page {self.page_index+1}")
        self.load_if_visible()

    def load_if_visible(self):
        if self._loaded:
            return
        if not self.isVisible():
            return
        try:
            page = self.pdf_tab.doc.load_page(self.page_index)
            # Render to fit scroll area width
            target_width = self.pdf_tab.scroll_area.viewport().width() - 20
            matrix = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            scale = target_width / pix.width if pix.width > 0 else 1.0
            if scale != 1.0:
                matrix = fitz.Matrix(self._zoom * scale, self._zoom * scale)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            self.setPixmap(pixmap)
            self.setFixedHeight(pixmap.height())
            self._pixmap = pixmap
            self._loaded = True
        except Exception as e:
            self.setText(f"Error loading page {self.page_index+1}")

    def unload(self):
        self._pixmap = None
        self.clear()
        self.setText(f"Page {self.page_index+1}")
        self._loaded = False

    def showEvent(self, event):
        self.load_if_visible()
        super().showEvent(event)

    def hideEvent(self, event):
        self.unload()
        super().hideEvent(event)

class PDFTab(QWidget):
    def __init__(self, parent=None, file_path=None, settings=None, signal_proxy=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.doc = None
        self.current_page = 0
        self.zoom = 1.5
        self.bookmarks = {}
        self.file_path = file_path
        self.settings = settings or {}
        self.persist_key = self.file_path if self.file_path else ""
        self.signal_proxy = signal_proxy or SignalProxy()
        self.page_labels = []
        self._scroll_timer = QTimer(self)
        self._scroll_timer.setSingleShot(True)
        self._scroll_timer.timeout.connect(self.lazy_load_visible_pages)
        self.init_ui()
        self.restore_settings()

    def init_ui(self):
        # Minimal top toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(2)
        toolbar.setContentsMargins(2, 2, 2, 2)
        def make_btn(icon, tooltip, slot, text=None):
            btn = QToolButton()
            if icon:
                btn.setIcon(QIcon(icon))
            if text:
                btn.setText(text)
            btn.setToolTip(tooltip)
            btn.setFixedSize(28, 28)
            btn.clicked.connect(slot)
            return btn
        open_btn = make_btn(self.style().standardIcon(QStyle.SP_DialogOpenButton), "Open PDF", self.parent_viewer.open_pdf)
        prev_btn = make_btn(self.style().standardIcon(QStyle.SP_ArrowLeft), "Previous Page", self.prev_page)
        next_btn = make_btn(self.style().standardIcon(QStyle.SP_ArrowRight), "Next Page", self.next_page)
        zoom_out_btn = make_btn(None, "Zoom Out", self.zoom_out, text="−")
        zoom_in_btn = make_btn(None, "Zoom In", self.zoom_in, text="+")
        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setFixedWidth(80)
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_input = QLineEdit()
        self.page_input.setPlaceholderText("Go to page")
        self.page_input.setFixedWidth(60)
        self.page_input.returnPressed.connect(self.goto_page)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search")
        self.search_input.setFixedWidth(90)
        # (Search logic can be added here)
        toolbar.addWidget(open_btn)
        toolbar.addWidget(prev_btn)
        toolbar.addWidget(next_btn)
        toolbar.addWidget(self.page_label)
        toolbar.addWidget(self.page_input)
        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(zoom_in_btn)
        toolbar.addWidget(self.search_input)
        toolbar.addStretch(1)

        # Scrollable area for all pages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_widget = QWidget()
        self.vbox = QVBoxLayout(self.scroll_widget)
        self.vbox.setSpacing(10)
        self.vbox.setContentsMargins(10, 10, 10, 10)
        self.scroll_area.setWidget(self.scroll_widget)
        self.vbox.addStretch(1)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addLayout(toolbar)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)
        self.setStyleSheet("background: #23272e;")

        # Connect scroll event for lazy loading
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.scroll_area.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.scroll_area.viewport() and event.type() == QEvent.Resize:
            for label in self.page_labels:
                label._loaded = False
            self.lazy_load_visible_pages()
        return super().eventFilter(obj, event)

    def open_pdf(self, file_name):
        try:
            self.doc = fitz.open(file_name)
            self.current_page = 0
            self.bookmarks = {}
            self.file_path = file_name
            self.persist_key = file_name
            self.page_labels = []
            # Remove old widgets
            while self.vbox.count():
                item = self.vbox.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            # Add lazy page labels
            for i in range(len(self.doc)):
                label = LazyPDFPageLabel(self, i)
                label.set_zoom(self.zoom)
                self.vbox.insertWidget(self.vbox.count()-1, label)
                self.page_labels.append(label)
            self.page_label.setText(f"Page: 1 / {len(self.doc)}")
            self.lazy_load_visible_pages()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {str(e)}")
            return False

    def _on_scroll(self):
        self._scroll_timer.start(100)  # Defer rendering until scrolling stops

    def lazy_load_visible_pages(self):
        if not self.page_labels:
            return
        scroll_value = self.scroll_area.verticalScrollBar().value()
        viewport_height = self.scroll_area.viewport().height()
        # Find which pages are visible
        visible_pages = []
        for i, label in enumerate(self.page_labels):
            y = label.pos().y()
            if (y + label.height() > scroll_value - 200) and (y < scroll_value + viewport_height + 200):
                visible_pages.append(i)
        # Only load ±2 pages around visible
        to_load = set()
        for i in visible_pages:
            for j in range(max(0, i-2), min(len(self.page_labels), i+3)):
                to_load.add(j)
        for i, label in enumerate(self.page_labels):
            if i in to_load:
                label.load_if_visible()
            else:
                label.unload()
        # Update current page label
        if visible_pages:
            self.current_page = visible_pages[0]
            self.page_label.setText(f"Page: {self.current_page+1} / {len(self.doc)}")

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.scroll_to_page(self.current_page)

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.scroll_to_page(self.current_page)

    def scroll_to_page(self, page_index):
        if 0 <= page_index < len(self.page_labels):
            label = self.page_labels[page_index]
            self.scroll_area.ensureWidgetVisible(label)
            self.page_label.setText(f"Page: {page_index+1} / {len(self.doc)}")

    def zoom_in(self):
        self.zoom += 0.2
        for label in self.page_labels:
            label.set_zoom(self.zoom)
        self.lazy_load_visible_pages()

    def zoom_out(self):
        self.zoom = max(0.2, self.zoom - 0.2)
        for label in self.page_labels:
            label.set_zoom(self.zoom)
        self.lazy_load_visible_pages()

    def goto_page(self):
        try:
            page = int(self.page_input.text()) - 1
            if 0 <= page < len(self.page_labels):
                self.current_page = page
                self.scroll_to_page(page)
        except Exception:
            pass

    def restore_settings(self):
        pass

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Minimalist PDF Viewer")
        self.setGeometry(100, 100, 1000, 700)
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
            self.refresh_bookmark_preview()

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.bookmark_list.clear()
            self.bookmark_preview.setText("No bookmarks")

    def get_current_tab(self):
        return self.tab_widget.currentWidget()

    def bookmark_navigate(self, item):
        tab = self.get_current_tab()
        if tab and tab.doc:
            page_num = tab.bookmarks.get(item.text(), 0)
            tab.current_page = page_num
            tab.scroll_to_page(page_num)

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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec_())