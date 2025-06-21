import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog,
    QTextEdit, QStyleFactory, QTabWidget, QWidget, QHBoxLayout,
    QMessageBox, QVBoxLayout, QTreeView, QFileSystemModel, QSplitter
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QFontMetrics, QIcon
from PyQt5.QtCore import Qt, QTimer, QRect, QDir

# --- File Explorer integration ---
from file_explorer import FileExplorer
import edit_actions
import keybinds

# --- Minimap integration moved to minimap.py ---
from minimap import Minimap

# --- SplitScreen integration ---
import splitscreen

FONT_CONFIG_PATH = "font_config.json"

def load_font_config():
    try:
        if os.path.exists(FONT_CONFIG_PATH):
            with open(FONT_CONFIG_PATH, "r") as f:
                config = json.load(f)
                font = QFont(config["family"], config["size"])
                font.setBold(config.get("bold", False))
                font.setItalic(config.get("italic", False))
                font.setUnderline(config.get("underline", False))
                return font
    except Exception as e:
        print("Error loading font config:", e)
    return QFont("Fira Code", 12)

class NumberLine(QWidget):
    def __init__(self, editor: QTextEdit):
        super().__init__(editor)
        self.editor = editor
        self.font = editor.font()  # Ensure font matches editor at init
        self.setFont(self.font)
        self.setMinimumWidth(self.calculate_width())
        self.editor.textChanged.connect(self.updateWidth)
        self.editor.verticalScrollBar().valueChanged.connect(self.update)
        self.editor.cursorPositionChanged.connect(self.update)
        self.show()

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
            painter.fillRect(event.rect(), QColor("#222226"))
            painter.setFont(self.font)
            fm = QFontMetrics(self.font)

            # Calculate the first visible block
            cursor = self.editor.textCursor()
            doc = self.editor.document()
            block = doc.firstBlock()

            # Get the vertical scroll bar value
            scroll_bar = self.editor.verticalScrollBar()
            scroll_value = scroll_bar.value()

            # Calculate line height and visible lines
            line_height = fm.lineSpacing()
            viewport_height = self.editor.viewport().height()

            # The y offset (in pixels) at which the viewport starts in the document
            y_offset = -scroll_value

            # For every visible block, draw its number
            block = doc.firstBlock()
            block_number = 1
            block_y = y_offset

            # Calculate pixel offset for each block using block layout
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
                painter.setPen(QColor("#909090"))
                rect_to_draw = QRect(0, int(block_top), self.width(), line_height)
                painter.drawText(rect_to_draw, Qt.AlignRight | Qt.AlignVCenter, str(block_number))
                block = block.next()
                block_number += 1
        except Exception as e:
            print("Error in NumberLine paintEvent:", e)

class EditorTabWidget(QWidget):
    def __init__(self, parent=None, font=None, numberline_on_left=True):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QTextEdit()
        self.editor.setFrameStyle(QTextEdit.NoFrame)
        self.editor.setContentsMargins(0, 0, 0, 0)
        if font is not None:
            self.editor.setFont(font)
        else:
            font = self.editor.font()
        self.numberline = NumberLine(self.editor)
        self.numberline.setFont(self.editor.font())  # Sync font immediately
        self.minimap = Minimap(self, self.editor, self.numberline)
        self.numberline_on_left = numberline_on_left
        self.update_layout()
        self.numberline.show()
        self.minimap.show()

    def update_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        if self.numberline_on_left:
            self.layout.addWidget(self.numberline)
            self.layout.addWidget(self.editor)
            self.layout.addWidget(self.minimap)
        else:
            self.layout.addWidget(self.minimap)
            self.layout.addWidget(self.editor)
            self.layout.addWidget(self.numberline)

    def setFont(self, font):
        self.editor.setFont(font)
        self.numberline.setFont(font)  # Always keep in sync
        self.numberline.update()
        self.editor.update()

    def set_numberline_side(self, left=True):
        self.numberline_on_left = left
        self.update_layout()

class FileTreeWidget(QWidget):
    """A simple file tree browser using QFileSystemModel and QTreeView."""

    def __init__(self, file_open_callback, parent=None):
        super().__init__(parent)
        self.file_open_callback = file_open_callback
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.model = QFileSystemModel()
        try:
            self.model.setRootPath(QDir.rootPath())
            self.tree = QTreeView()
            self.tree.setModel(self.model)
            self.tree.setRootIndex(self.model.index(QDir.rootPath()))
            self.tree.setHeaderHidden(True)
            self.tree.doubleClicked.connect(self.open_file_from_tree)
            self.tree.setAnimated(True)
            self.tree.setIndentation(16)
            self.tree.setSortingEnabled(True)
            layout.addWidget(self.tree)
        except Exception as e:
            print("Error initializing FileTreeWidget:", e)
        self.setLayout(layout)

    def open_file_from_tree(self, index):
        if not index.isValid():
            return
        file_path = self.model.filePath(index)
        if os.path.isfile(file_path) and self.is_supported(file_path):
            self.file_open_callback(file_path)

    @staticmethod
    def is_supported(file_path):
        supported = (".txt", ".py", ".md", ".json", ".ini", ".csv", ".log")
        return file_path.lower().endswith(supported)

class MainTabWidget(QTabWidget):
    """Main application tab widget, supports both editors and file explorer."""

    def __init__(self, file_open_callback, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.file_open_callback = file_open_callback

    def add_editor_tab(self, title="Untitled", content="", font=None, numberline_on_left=True, file_path=None):
        editor_tab = EditorTabWidget(font=font, numberline_on_left=numberline_on_left)
        editor_tab.editor.setPlainText(content)
        index = self.addTab(editor_tab, title)
        self.setCurrentIndex(index)
        editor_tab.numberline.setVisible(True)
        editor_tab.editor.textChanged.connect(editor_tab.numberline.update)
        editor_tab.editor.cursorPositionChanged.connect(editor_tab.numberline.update)
        # Optionally associate the file path with the tab
        editor_tab._file_path = file_path

    def add_file_explorer_tab(self):
        explorer = FileExplorer()
        index = self.addTab(explorer, "File Explorer")
        self.setCurrentIndex(index)

    def close_tab(self, index):
        self.removeTab(index)

class TextEditor(QMainWindow):
    def __init__(self, canvas_parent=None):
        super().__init__()
        self.canvas_parent = canvas_parent
        self.setWindowTitle("Third Edit")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyle(QStyleFactory.create("Fusion"))
        self.current_font = load_font_config()
        self.show_numberline = True
        self.numberline_on_left = True
        self.filetree_visible = False
<<<<<<< Updated upstream
        self.theme = "dark"
=======
        self.checkpoint_manager = CheckpointManager()
        self.music_player = None
        self.child_windows = []  # Keep references to child windows
>>>>>>> Stashed changes
        self.init_ui()
        self.set_dark_theme()

    def init_ui(self):
        self.tabs = MainTabWidget(file_open_callback=self.open_file_in_editor_tab)
        self.tabs.add_editor_tab(font=self.current_font, numberline_on_left=self.numberline_on_left)
        # File tree widget, hidden by default
        self.file_tree_widget = FileTreeWidget(file_open_callback=self.open_file_in_editor_tab)
        self.file_tree_widget.setVisible(False)
        # Splitter for file tree and editor tabs
        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.addWidget(self.file_tree_widget)
        self.splitter.addWidget(self.tabs)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([0, 1])
        self.setCentralWidget(self.splitter)
        self.create_menu_bar()

<<<<<<< Updated upstream
=======
    def add_editor_tab_to_splitter(self, orientation=None):
        # Optionally change orientation
        if orientation is not None:
            self.editor_splitter.setOrientation(orientation)
        editor = MainTabWidget(file_open_callback=self.open_file_in_editor_tab)
        editor.add_editor_tab(font=self.current_font, numberline_on_left=self.numberline_on_left)
        self.editor_splitter.addWidget(editor)
        self.editors.append(editor)

    def remove_editor_tab_from_splitter(self):
        if len(self.editors) > 1:
            editor = self.editors.pop()
            editor.setParent(None)
            editor.deleteLater()

    def setup_split_actions(self):
        # Split horizontally
        self.split_horizontal_action = QAction("Split Horizontally", self)
        self.split_horizontal_action.setShortcut("Ctrl+Alt+H")
        self.split_horizontal_action.triggered.connect(self.handle_split_action)
        self.addAction(self.split_horizontal_action)

        # Split vertically (same as horizontally for new window)
        self.split_vertical_action = QAction("Split Vertically", self)
        self.split_vertical_action.setShortcut("Ctrl+Alt+V")
        self.split_vertical_action.triggered.connect(self.handle_split_action)
        self.addAction(self.split_vertical_action)

        # Unsplit (close this window if not the last one)
        self.unsplit_action = QAction("Unsplit Window", self)
        self.unsplit_action.setShortcut("Ctrl+Alt+U")
        self.unsplit_action.triggered.connect(self.close)
        self.addAction(self.unsplit_action)

    def get_active_tabwidget(self):
        # Return the last editor (focused logic can be improved)
        if self.editors:
            return self.editors[-1]
        return None

>>>>>>> Stashed changes
    def open_file_in_editor_tab(self, file_path):
        # Only open if not already open, otherwise switch tab
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "_file_path") and tab._file_path == file_path:
                self.tabs.setCurrentIndex(i)
                return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            title = os.path.basename(file_path)
            self.tabs.add_editor_tab(title=title, content=content, font=self.current_font,
                                    numberline_on_left=self.numberline_on_left, file_path=file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def add_new_tab(self, title="Untitled", content=""):
        self.tabs.add_editor_tab(title=title, content=content, font=self.current_font, numberline_on_left=self.numberline_on_left)

    def add_file_explorer_tab(self):
        self.tabs.add_file_explorer_tab()

    def close_tab(self, index):
        self.tabs.close_tab(index)

    def toggle_file_tree(self):
        self.filetree_visible = not self.filetree_visible
        self.file_tree_widget.setVisible(self.filetree_visible)
        if self.filetree_visible:
            self.splitter.setSizes([200, 1200])
        else:
            self.splitter.setSizes([0, 1])

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        file_menu.addAction("New File", self.new_file)
        file_menu.addAction("Open File", self.open_file)
        file_menu.addAction("Save File", self.save_file)
        file_menu.addAction("Dublicate File", self.duplicate_file)
        file_menu.addSeparator()
        file_menu.addAction("New Tab", lambda: self.add_new_tab())
        file_menu.addAction("Open File Explorer", self.add_file_explorer_tab)
        file_menu.addAction("Close Tab", lambda: self.close_tab(self.tabs.currentIndex()))

        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Undo", self.trigger_undo)
        edit_menu.addAction("Redo", self.trigger_redo)
        edit_menu.addAction("Select All", self.trigger_select_all)
        search_menu = edit_menu.addMenu("Search")
        search_menu.addAction("Replace")
        go_to_menu = edit_menu.addMenu("Go To")
        go_to_menu.addAction("Line")
        go_to_menu.addAction("Word")
        checkpoints_menu = edit_menu.addMenu("Checkpoints")
        checkpoints_menu.addAction("Create Checkpoint")
        checkpoints_menu.addAction("Go to Checkpoint")

        view_menu = menu_bar.addMenu("View")
        # --- Rename "Toggle File Menu" to "Toggle File Tree" and link to file tree toggle
        toggle_filetree_action = QAction("Toggle File Tree", self)
        toggle_filetree_action.setCheckable(True)
        toggle_filetree_action.setChecked(self.filetree_visible)
        toggle_filetree_action.triggered.connect(self.toggle_file_tree)
        view_menu.addAction(toggle_filetree_action)
        toggle_numberline_action = QAction("Toggle Number Line", self)
        toggle_numberline_action.setCheckable(True)
        toggle_numberline_action.setChecked(self.show_numberline)
        toggle_numberline_action.triggered.connect(self.view_toggle_numberline)
        view_menu.addAction(toggle_numberline_action)
        rotate_numberline_action = QAction("Rotate Number Line", self)
        rotate_numberline_action.triggered.connect(self.rotate_number_line)
        view_menu.addAction(rotate_numberline_action)
        view_menu.addAction("Toggle Minimap", self.toggle_minimap)

        # --- Split Screen menu with advanced split
        split_screen_menu = view_menu.addMenu("Split Screen")
<<<<<<< Updated upstream
        horizontal_split_action = QAction("Horizontal Split", self)
        horizontal_split_action.triggered.connect(self.split_horizontally)
        split_screen_menu.addAction(horizontal_split_action)

        vertical_split_action = QAction("Vertical Split", self)
        vertical_split_action.triggered.connect(self.split_vertically)
        split_screen_menu.addAction(vertical_split_action)

        advanced_split_action = QAction("Advanced Split", self)
        # No functionality, placeholder
        split_screen_menu.addAction(advanced_split_action)

=======
        split_horizontal_action = QAction("Split Horizontally", self)
        split_horizontal_action.setShortcut("Ctrl+Alt+H")
        split_horizontal_action.triggered.connect(self.handle_split_action)
        split_screen_menu.addAction(split_horizontal_action)
        
        split_vertical_action = QAction("Split Vertically", self)
        split_vertical_action.setShortcut("Ctrl+Alt+V")
        split_vertical_action.triggered.connect(self.handle_split_action)
        split_screen_menu.addAction(split_vertical_action)
        
        unsplit_action = QAction("Unsplit Window", self)
        unsplit_action.setShortcut("Ctrl+Alt+U")
        unsplit_action.triggered.connect(self.close)
        split_screen_menu.addAction(unsplit_action)
        
>>>>>>> Stashed changes
        Themes_screen_menu = view_menu.addMenu("Themes")
        Themes_screen_menu.addAction("White Mode", self.set_light_theme)
        Themes_screen_menu.addAction("Dark Mode", self.set_dark_theme)

        options_menu = menu_bar.addMenu("Options")
        options_menu.addAction("Font Editor", self.font_editor)
        options_menu.addAction("Theme Manager")
        options_menu.addAction("Extensions")

        keybind_menu = menu_bar.addMenu("Keybinds")
        keybind_menu.addAction("Configure Keybinds")
        keybind_menu.addAction("Default Keybinds Map")

        languages_menu = menu_bar.addMenu("Languages")
        languages_menu.addAction("Syntax Options")
        languages_menu.addAction("Compilers")

        env_menu = menu_bar.addMenu("Environments")
        env_menu.addAction("Create Environment")
        env_menu.addAction("Configure Environment")
        env_menu.addAction("Create Custom Environment")

        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("Documentation")
        help_menu.addAction("Tutorial")
        help_menu.addAction("About Developer")

        tools_menu = menu_bar.addMenu("Tools")
        tools_menu.addAction("Process Manager")
        tools_menu.addAction("Control Panel")
        tools_menu.addAction("Open PDF")
        tools_menu.addAction("Open Image")
        tools_menu.addAction("Diagramm Sketch")
        tools_menu.addAction("View Editor Source Code")

    # --- Split screen logic ---
    def split_horizontally(self):
        self._split_tab(Qt.Vertical)

    def split_vertically(self):
        self._split_tab(Qt.Horizontal)

    def _split_tab(self, orientation):
        tab_count = self.tabs.count()
        tab_names = []
        possible_indexes = []
        for i in range(tab_count):
            widget = self.tabs.widget(i)
            if hasattr(widget, "editor") or isinstance(widget, QSplitter):
                tab_names.append(self.tabs.tabText(i))
                possible_indexes.append(i)
        if not tab_names:
            QMessageBox.warning(self, "Warning", "No editor tab to split.")
            return
        if len(tab_names) == 1:
            index = possible_indexes[0]
            splitscreen.split_tab(self.tabs, index, orientation)
        else:
            # Show a themed popup to select which tab to split
            dialog = splitscreen.SplitChoiceDialog(tab_names, theme=self.theme, parent=self)
            if dialog.exec_() == QDialog.Accepted:
                idx = dialog.selected_tab_index()
                index = possible_indexes[idx]
                splitscreen.split_tab(self.tabs, index, orientation)

    def trigger_undo(self):
        widget = self.tabs.currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.undo()

    def trigger_redo(self):
        widget = self.tabs.currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.redo()

    def trigger_select_all(self):
        widget = self.tabs.currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.selectAll()

    def view_toggle_numberline(self):
        self.show_numberline = not self.show_numberline
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "numberline"):
                tab.numberline.setVisible(self.show_numberline)

    def toggle_minimap(self):
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "minimap"):
                tab.minimap.setVisible(not tab.minimap.isVisible())

    def rotate_number_line(self):
        self.numberline_on_left = not self.numberline_on_left
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "set_numberline_side"):
                tab.set_numberline_side(self.numberline_on_left)

    def new_file(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Create New File", "",
                "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.add_new_tab(title=os.path.basename(file_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Invalid Creation request: {str(e)}")

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open File")
        if file_name:
            self.open_file_in_editor_tab(file_name)

    def save_file(self):
        current_widget = self.tabs.currentWidget()
        if not current_widget:
            return
        if hasattr(current_widget, 'editor'):
            editor = current_widget.editor
            content = editor.toPlainText()
        else:
            return  # FileExplorer tab

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.tabs.setTabText(self.tabs.currentIndex(), os.path.basename(file_path))
                # Optionally set the file path on the tab for duplicate prevention
                current_widget._file_path = file_path
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")

    def duplicate_file(self):
        current_index = self.tabs.currentIndex()
        if current_index == -1:
            return

        current_widget = self.tabs.widget(current_index)
        # Don't allow duplicating a File Explorer or File Tree tab
        if not hasattr(current_widget, "editor"):
            QMessageBox.warning(self, "Warning", "Cannot duplicate this tab")
            return

        editor = current_widget.editor
        content = editor.toPlainText()
        original_name = self.tabs.tabText(current_index)

        if original_name == "Untitled":
            QMessageBox.warning(self, "Warning", "Please save the file before duplicating")
            return

        base_path = os.path.splitext(original_name)[0]
        extension = os.path.splitext(original_name)[1] or ""
        counter = 1
        new_name = f"{base_path}_duplicate{extension}"

        while True:
            if not os.path.exists(new_name):
                break
            new_name = f"{base_path}_duplicate{counter}{extension}"
            counter += 1

        try:
            with open(new_name, 'w', encoding='utf-8') as f:
                f.write(content)
            self.add_new_tab(title=os.path.basename(new_name), content=content)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Duplication failed: {str(e)}")

    def set_dark_theme(self):
        self.theme = "dark"
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.Highlight, QColor(100, 100, 255))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)

        self.setStyleSheet("""
            QMenuBar { background-color: #2b2b2b; color: white; }
            QMenuBar::item:selected { background: #44475a; }
            QMenu { background-color: #2b2b2b; color: white; }
            QMenu::item:selected { background-color: #44475a; }
        """)

    def set_light_theme(self):
        self.theme = "light"
        QApplication.setPalette(QApplication.style().standardPalette())
        self.setStyleSheet("")

    def font_editor(self):
        from font_editor import FontEditor
        self.font_editor_window = FontEditor()
        self.font_editor_window.settings_applied.connect(self.apply_font_from_editor)
        self.font_editor_window.show()

    def apply_font_from_editor(self, font):
        self.current_font = font
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if hasattr(tab, "setFont"):
                tab.setFont(font)

    def handle_split_action(self):
        if self.canvas_parent is not None:
            self.canvas_parent.add_split_editor()
        else:
            self.open_new_window()

    def open_new_window(self):
        new_window = TextEditor()
        new_window.show()
        self.child_windows.append(new_window)

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = TextEditor()
        edit_actions.connect_edit_menu(window)
        keybinds.integrate_keybinds_menu(window)
        window.show()
        sys.exit(app.exec_())
    except Exception as exc:
        print('An error occurred while running the application:', exc)