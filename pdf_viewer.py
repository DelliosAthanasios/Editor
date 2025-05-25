import sys
import fitz  # PyMuPDF
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
    QPushButton, QFileDialog, QHBoxLayout, QSlider, QScrollArea,
    QLineEdit, QListWidget, QListWidgetItem, QDockWidget, QMessageBox,
    QTabWidget, QComboBox, QGridLayout
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QIcon
from PyQt5.QtCore import Qt, QSize, QEvent

class PDFPageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.highlights = []

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.pixmap():
            painter = QPainter(self)
            painter.setPen(QPen(Qt.NoPen))
            painter.setBrush(QColor(255, 255, 0, 120))
            for rect in self.highlights:
                painter.drawRect(*rect)
            painter.end()

class PDFTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_viewer = parent
        self.doc = None
        self.current_page = 0
        self.zoom = 1.5
        self.bookmarks = {}
        self.page_labels = []
        self.search_results = []
        self.current_search_index = -1
        
        self.init_ui()
        
    def init_ui(self):
        self.label1 = PDFPageLabel()
        self.label2 = PDFPageLabel()
        self.label3 = PDFPageLabel()
        self.label4 = PDFPageLabel()
        self.page_labels = [self.label1, self.label2, self.label3, self.label4]
        
        for label in self.page_labels:
            label.hide()
            
        self.page_label = QLabel("Page: 0 / 0")
        self.page_label.setAlignment(Qt.AlignCenter)

        # Navigation Controls
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

        self.image_layout = QHBoxLayout()
        for label in self.page_labels:
            self.image_layout.addWidget(label)

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.image_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.installEventFilter(self)

        main_layout = QVBoxLayout()
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(scroll_area)

        self.setLayout(main_layout)
        
    def eventFilter(self, source, event):
        if event.type() == QEvent.Wheel and source is self.parent().parent().parent():
            delta = event.angleDelta().y()
            if delta > 0:
                self.prev_page()
            else:
                self.next_page()
            return True
        return super().eventFilter(source, event)
        
    def change_page_count(self, index):
        self.display_pages()
        
    def get_page_count(self):
        return self.pages_combo.currentIndex() + 1
        
    def open_pdf(self, file_name):
        try:
            self.doc = fitz.open(file_name)
            self.current_page = 0
            self.bookmarks = {}
            if self.parent_viewer:
                self.parent_viewer.bookmark_list.clear()
                self.parent_viewer.populate_overview_for_tab(self)
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
            if i < page_count and self.current_page + i < total_pages:
                self.show_page(self.page_labels[i], self.current_page + i)
                self.page_labels[i].show()
            else:
                self.page_labels[i].clear()
                self.page_labels[i].hide()

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

    def next_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page + page_count < len(self.doc):
                self.current_page += page_count
                self.display_pages()

    def prev_page(self):
        if self.doc:
            page_count = self.get_page_count()
            if self.current_page - page_count >= 0:
                self.current_page -= page_count
                self.display_pages()

    def zoom_changed(self, value):
        self.zoom = value / 10.0
        self.display_pages()

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
            for page_num in range(len(self.doc)):
                page = self.doc.load_page(page_num)
                text_instances = page.search_for(query)
                for inst in text_instances:
                    self.search_results.append((page_num, inst))
            
            if self.search_results:
                self.current_search_index = 0
                self.highlight_search_result()
            else:
                QMessageBox.information(self, "Search", "Text not found.")

    def highlight_search_result(self):
        if not self.search_results or self.current_search_index < 0:
            return
            
        page_num, rect = self.search_results[self.current_search_index]
        self.current_page = page_num
        self.display_pages()
        
        # Find which label contains this page
        page_count = self.get_page_count()
        label_index = page_num - self.current_page
        if 0 <= label_index < page_count:
            label = self.page_labels[label_index]
            label.highlights = [(rect.x0 * self.zoom, rect.y0 * self.zoom, 
                               rect.width * self.zoom, rect.height * self.zoom)]
            label.update()

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

    def toggle_overview(self):
        if self.parent_viewer:
            self.parent_viewer.toggle_overview()

    def get_page_preview(self, page_num, size=QSize(100, 150)):
        if not self.doc or page_num >= len(self.doc):
            return None
            
        page = self.doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
        mode = QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, mode).copy()
        pixmap = QPixmap.fromImage(img)
        return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

class PDFViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enhanced PDF Viewer")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet(self.get_stylesheet())

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        self.open_button = QPushButton("Open PDF")
        self.open_button.clicked.connect(self.open_pdf)
        
        # Add open button to toolbar
        toolbar = self.addToolBar("Toolbar")
        toolbar.addWidget(self.open_button)

        # Bookmarks Dock
        self.bookmark_dock = QDockWidget("Bookmarks", self)
        self.bookmark_list = QListWidget()
        self.bookmark_list.itemClicked.connect(self.bookmark_navigate)
        self.bookmark_dock.setWidget(self.bookmark_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bookmark_dock)

        # Overview Dock
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

    def open_pdf(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Open PDF", "", "PDF Files (*.pdf)")
        for file_name in file_names:
            self.add_pdf_tab(file_name)

    def add_pdf_tab(self, file_name):
        tab = PDFTab(self)
        if tab.open_pdf(file_name):
            self.tab_widget.addTab(tab, file_name.split('/')[-1])
            self.tab_widget.setCurrentWidget(tab)
            self.populate_overview_for_tab(tab)

    def close_tab(self, index):
        self.tab_widget.removeTab(index)
        if self.tab_widget.count() == 0:
            self.bookmark_list.clear()
            self.clear_overview()

    def clear_overview(self):
        for i in reversed(range(self.overview_layout.count())): 
            self.overview_layout.itemAt(i).widget().setParent(None)

    def get_current_tab(self):
        return self.tab_widget.currentWidget()

    def bookmark_navigate(self, item):
        tab = self.get_current_tab()
        if tab and tab.doc:
            page_num = tab.bookmarks.get(item.text(), 0)
            tab.current_page = page_num
            tab.display_pages()

    def toggle_overview(self):
        if self.overview_dock.isVisible():
            self.overview_dock.hide()
        else:
            self.overview_dock.show()
            tab = self.get_current_tab()
            if tab:
                self.populate_overview_for_tab(tab)

    def populate_overview_for_tab(self, tab):
        self.clear_overview()
        if tab and tab.doc:
            cols = 3
            row = 0
            col = 0
            
            for i in range(len(tab.doc)):
                preview_label = QLabel()
                preview_label.setFixedSize(120, 180)
                preview_label.setAlignment(Qt.AlignCenter)
                
                preview = tab.get_page_preview(i, QSize(100, 150))
                if preview:
                    preview_label.setPixmap(preview)
                
                page_label = QLabel(f"Page {i + 1}")
                page_label.setAlignment(Qt.AlignCenter)
                
                container = QWidget()
                container_layout = QVBoxLayout()
                container_layout.addWidget(preview_label)
                container_layout.addWidget(page_label)
                container.setLayout(container_layout)
                
                container.mousePressEvent = lambda event, page=i: self.overview_navigate(page)
                
                self.overview_layout.addWidget(container, row, col)
                
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

    def overview_navigate(self, page_num):
        tab = self.get_current_tab()
        if tab and tab.doc:
            tab.current_page = page_num
            tab.display_pages()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = PDFViewer()
    viewer.show()
    sys.exit(app.exec_())