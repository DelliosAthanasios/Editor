import sys
import os
import json
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QAction, QFileDialog,
    QStyleFactory, QTabWidget, QWidget, QHBoxLayout,
    QMessageBox, QVBoxLayout, QTreeView, QFileSystemModel, QSplitter, QDialog, QTextEdit, QActionGroup
)
from PyQt5.QtGui import QFont, QPalette, QColor, QPainter, QFontMetrics, QTextCursor
from PyQt5.QtCore import Qt, QTimer, QRect, QDir

from global_.file_explorer import FileExplorer
from global_.file_tree import FileTreeWidget
import global_.edit_actions as edit_actions
from global_.edit_actions import SearchReplaceDialog
import global_.keybinds as keybinds
from global_.minimap import Minimap
from global_.theme_manager import theme_manager_singleton, get_editor_styles, get_menu_bar_styles, get_separator_styles, get_tab_bar_styles, get_classic_styles, get_user_styles, ThemeManagerDialog, load_user_prefs, save_user_prefs
from global_.checkpoints import CheckpointManager, CheckpointDialog, CheckpointManagerDialog
from global_.image_viewer_widget import ImageViewerWidget
from global_.pdf_viewer import PDFViewer
from global_.ce import CodeExplorerWidget
from global_.console import ConsolePanel
from global_.split import SplitContainer, add_splitting_actions, split_current, unsplit_current
from global_.syntax_highlighter import GenericHighlighter
from global_.syntax_highlighting_dialog import SyntaxHighlightingDialog
from global_.language_detection import detect_language_by_extension
from global_.diagramm_sketch import DiagrammSketchWidget
from global_.dynamic_saving import enable_dynamic_saving_for_qt

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

def set_dark_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(40, 40, 40))
    palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)


class NumberLine(QWidget):
    def __init__(self, editor: QTextEdit, theme_data=None):
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

class EditorTabWidget(QWidget):
    def __init__(self, parent=None, font=None, numberline_on_left=True, language="python", file_path=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.editor = QTextEdit()
        self.editor.setFrameStyle(QTextEdit.NoFrame)
        self.editor.setContentsMargins(0, 0, 0, 0)
        self.editor.setWordWrapMode(False)
        if font is not None:
            self.editor.setFont(font)
        else:
            font = self.editor.font()
        theme_data = theme_manager_singleton.get_theme()
        self.numberline = NumberLine(self.editor, theme_data)
        self.numberline.setFont(self.editor.font())
        self.minimap = Minimap(self, self.editor, self.numberline, theme_data)
        self.numberline_on_left = numberline_on_left
        self.update_layout()
        self.numberline.show()
        self.minimap.show()
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        self.set_theme(theme_data)

        # Syntax highlighting integration
        if file_path:
            lang = detect_language_by_extension(file_path)
        else:
            lang = language
        self.highlighter = GenericHighlighter(self.editor.document(), language=lang)
        self.current_language = lang

    def set_theme(self, theme_data):
        self.editor.setStyleSheet(get_editor_styles(theme_data))
        if hasattr(self, "numberline"):
            self.numberline.set_theme(theme_data)
        if hasattr(self, "minimap"):
            self.minimap.set_theme(theme_data)
        # No per-widget stylesheet needed; main window applies global style

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
        self.numberline.setFont(font)
        self.numberline.update()
        self.editor.update()

    def set_numberline_side(self, left=True):
        self.numberline_on_left = left
        self.update_layout()

    def set_highlighting_language(self, language):
        self.highlighter = GenericHighlighter(self.editor.document(), language=language)
        self.current_language = language

class MainTabWidget(QTabWidget):
    def __init__(self, file_open_callback, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_tab)
        self.file_open_callback = file_open_callback
        
        # Connect to theme changes
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        # Apply initial theme
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
    
    def set_theme(self, theme_data):
        # No per-widget stylesheet needed; main window applies global style
        pass

    def add_editor_tab(self, title="Untitled", content="", font=None, numberline_on_left=True, file_path=None):
        lang = detect_language_by_extension(file_path) if file_path else "python"
        editor_tab = EditorTabWidget(font=font, numberline_on_left=numberline_on_left, language=lang, file_path=file_path)
        editor_tab.editor.setPlainText(content)
        index = self.addTab(editor_tab, title)
        self.setCurrentIndex(index)
        editor_tab.numberline.setVisible(True)
        editor_tab.editor.textChanged.connect(editor_tab.numberline.update)
        editor_tab.editor.cursorPositionChanged.connect(editor_tab.numberline.update)
        editor_tab._file_path = file_path

    def add_pdf_tab(self, file_path):
        if not os.path.exists(file_path):
            return False
        try:
            pdf_viewer = PDFViewer()
            pdf_viewer.add_pdf_tab(file_path)
            title = os.path.basename(file_path)
            index = self.addTab(pdf_viewer, title)
            self.setCurrentIndex(index)
            pdf_viewer._file_path = file_path
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF viewer: {str(e)}")
            return False

    def add_code_explorer_tab(self, file_path):
        for i in range(self.count()):
            widget = self.widget(i)
            if hasattr(widget, "_ce_file_path") and widget._ce_file_path == file_path:
                self.setCurrentIndex(i)
                return
        try:
            ce_widget = CodeExplorerWidget(file_path, parent=self)
            ce_widget._ce_file_path = file_path
            title = f"Code Explorer: {os.path.basename(file_path)}"
            index = self.addTab(ce_widget, title)
            self.setCurrentIndex(index)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Code Explorer: {str(e)}")

    def add_image_tab(self, file_path):
        if not os.path.exists(file_path):
            return False
        image_widget = ImageViewerWidget(self, file_path)
        title = os.path.basename(file_path)
        index = self.addTab(image_widget, title)
        self.setCurrentIndex(index)
        return True

    def add_file_explorer_tab(self):
        explorer = FileExplorer()
        index = self.addTab(explorer, "File Explorer")
        self.setCurrentIndex(index)

    def add_diagramm_sketch_tab(self):
        widget = DiagrammSketchWidget()
        index = self.addTab(widget, "Diagramm Sketch")
        self.setCurrentIndex(index)

    def add_advanced_editor_tab(self, file_path):
        """Add an advanced editor tab for large files"""
        try:
            from advancedloading import create_advanced_editor_tab
            advanced_widget = create_advanced_editor_tab(file_path, self)
            if advanced_widget:
                title = f"Large File: {os.path.basename(file_path)}"
                index = self.addTab(advanced_widget, title)
                self.setCurrentIndex(index)
                advanced_widget._file_path = file_path
                return True
        except ImportError:
            QMessageBox.warning(self, "Warning", "Advanced loading module not available")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create advanced editor: {str(e)}")
        return False

    def close_tab(self, index):
        self.removeTab(index)

class TextEditor(QMainWindow):
    def __init__(self, canvas_parent=None):
        super().__init__()
        self.canvas_parent = canvas_parent
        self.setWindowTitle("Third Edit")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyle(QStyleFactory.create("Fusion"))
        self.theme = theme_manager_singleton.current_theme_key
        self.themes = theme_manager_singleton.themes
        self.current_font = load_font_config()
        self.show_numberline = True
        self.numberline_on_left = True
        self.filetree_visible = False
        self.checkpoint_manager = CheckpointManager()
        self.music_player = None
        self.child_windows = []  # Keep references to child windows
        self.init_ui()
        self.apply_theme(self.theme)
        # Always use classic style
        self.setStyleSheet(get_classic_styles(theme_manager_singleton.get_theme()))
        self.setup_split_actions()
        # Connect to theme changes
        theme_manager_singleton.themeChanged.connect(self.on_theme_changed)
        enable_dynamic_saving_for_qt(self)

    def editor_factory(self):
        return MainTabWidget(file_open_callback=self.open_file_in_editor_tab)

    def init_ui(self):
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)

        # Create file tree widget
        self.file_tree = FileTreeWidget(self)
        self.file_tree.setVisible(False)  # Initially hidden
        # Connect the file tree's signal to open files
        self.file_tree.file_opened.connect(self.open_file_in_editor_tab)

        # Editor splitter for unlimited splits
        self.editor_splitter = QSplitter(Qt.Horizontal)
        self.editor_splitter.setStyleSheet("background-color: #23232a; border: none;")
        self.editors = []
        self.add_editor_tab_to_splitter()

        # Add widgets to main splitter
        self.main_splitter.addWidget(self.file_tree)
        self.main_splitter.addWidget(self.editor_splitter)

        # Set initial sizes
        self.main_splitter.setSizes([200, 1000])

        # Create central widget and layout
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.main_splitter)

        # Add console panel
        self.console_panel = ConsolePanel(self)
        self.console_panel.setVisible(False)  # Set console to be hidden by default
        layout.addWidget(self.console_panel)

        self.setCentralWidget(central_widget)
        self.create_menu_bar()

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

    def open_file_in_editor_tab(self, file_path):
        tab_widget = self.get_active_tabwidget()
        for i in range(tab_widget.count()):
            tab = tab_widget.widget(i)
            tab_file_path = getattr(tab, "_file_path", None)
            if tab_file_path == file_path:
                tab_widget.setCurrentIndex(i)
                return
        _, ext = os.path.splitext(file_path.lower())
        if ext == '.pdf':
            tab_widget.add_pdf_tab(file_path)
            return
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        if ext in image_extensions:
            tab_widget.add_image_tab(file_path)
            return
        
        # Check if file needs advanced loading
        try:
            from advancedloading import should_use_advanced_loading, load_large_file, create_advanced_editor_tab
            
            should_use, file_info = should_use_advanced_loading(file_path)
            
            if should_use:
                # Use advanced loading for large files
                result = load_large_file(file_path, self)
                if result is not None:
                    content, use_advanced_editor = result
                    title = os.path.basename(file_path)
                    
                    if use_advanced_editor:
                        # Use advanced editor for large files
                        if tab_widget.add_advanced_editor_tab(file_path):
                            return
                        else:
                            # Fallback to normal loading if advanced editor fails
                            pass
                    else:
                        # Use normal editor with loaded content
                        tab_widget.add_editor_tab(title=title, content=content, font=self.current_font,
                                                  numberline_on_left=self.numberline_on_left, file_path=file_path)
                        return
            else:
                # Use normal loading for small files
                with open(file_path, "r", encoding=file_info.get('encoding', 'utf-8')) as f:
                    content = f.read()
                title = os.path.basename(file_path)
                tab_widget.add_editor_tab(title=title, content=content, font=self.current_font,
                                          numberline_on_left=self.numberline_on_left, file_path=file_path)
                return
        except ImportError:
            # Fallback to original method if advancedloading module is not available
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                title = os.path.basename(file_path)
                tab_widget.add_editor_tab(title=title, content=content, font=self.current_font,
                                          numberline_on_left=self.numberline_on_left, file_path=file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def add_new_tab(self, title="Untitled", content=""):
        self.get_active_tabwidget().add_editor_tab(title=title, content=content, font=self.current_font, numberline_on_left=self.numberline_on_left)

    def add_file_explorer_tab(self):
        self.get_active_tabwidget().add_file_explorer_tab()

    def close_tab(self, index):
        self.get_active_tabwidget().close_tab(index)

    def toggle_file_tree(self):
        self.filetree_visible = not self.filetree_visible
        self.file_tree.setVisible(self.filetree_visible)
        if self.filetree_visible:
            # Set the root path to the current directory
            current_dir = os.getcwd()
            self.file_tree.set_root_path(current_dir)

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
        file_menu.addAction("Close Tab", lambda: self.close_tab(self.get_active_tabwidget().currentIndex()))
        
        edit_menu = menu_bar.addMenu("Edit")
        edit_menu.addAction("Undo", self.trigger_undo)
        edit_menu.addAction("Redo", self.trigger_redo)
        edit_menu.addAction("Select All", self.trigger_select_all)
        search_menu = edit_menu.addMenu("Search")
        search_menu.addAction("Find", lambda: self.open_search_dialog("find"))
        search_menu.addAction("Find and Replace", lambda: self.open_search_dialog("replace"))
        go_to_menu = edit_menu.addMenu("Go To")
        go_to_menu.addAction("Line")
        go_to_menu.addAction("Word")
        checkpoints_menu = edit_menu.addMenu("Checkpoints")
        checkpoints_menu.addAction("Create Checkpoint", self.create_checkpoint)
        checkpoints_menu.addAction("Go to Next Checkpoint", self.goto_next_checkpoint)
        checkpoints_menu.addAction("Go to Previous Checkpoint", self.goto_prev_checkpoint)
        checkpoints_menu.addAction("Manage Checkpoints...", self.open_checkpoint_manager)
        
        view_menu = menu_bar.addMenu("View")
        toggle_filetree_action = QAction("Toggle File Tree", self)
        toggle_filetree_action.setCheckable(True)
        toggle_filetree_action.setChecked(self.filetree_visible)
        toggle_filetree_action.setShortcut("Ctrl+B")  # Same shortcut as VS Code
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
        
        toggle_console_action = QAction("Toggle Console", self)
        toggle_console_action.setCheckable(True)
        toggle_console_action.setChecked(False)
        toggle_console_action.triggered.connect(self.toggle_console)
        toggle_console_action.setShortcut("Ctrl+X,Ctrl+C")
        view_menu.addAction(toggle_console_action)
        
        code_explorer_action = QAction("Enable Code Explorer", self)
        code_explorer_action.triggered.connect(self.enable_code_explorer)
        view_menu.addAction(code_explorer_action)
        
        split_screen_menu = view_menu.addMenu("Split Screen")
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
        
        Themes_screen_menu = view_menu.addMenu("Themes")
        Themes_screen_menu.addAction("White Mode", self.set_light_theme)
        Themes_screen_menu.addAction("Dark Mode", self.set_dark_theme)
        Themes_screen_menu.addSeparator()
        Themes_screen_menu.addAction("Theme Manager...", self.open_theme_manager)
        
        options_menu = menu_bar.addMenu("Options")
        options_menu.addAction("Font Editor", self.font_editor)
        options_menu.addAction("Extensions")
        options_menu.addAction("Syntax Highlighting", self.open_syntax_highlighting_dialog)
        keybind_menu = menu_bar.addMenu("Keybinds")
        keybind_menu.addAction("Configure Keybinds")
        keybind_menu.addAction("Default Keybinds Map")
        languages_menu = menu_bar.addMenu("Languages")
        languages_menu.addAction("Syntax Options")
        languages_menu.addAction("Compilers")
        languages_menu.addAction("CPU Emulators", self.open_assembly_emulator_tab)
        # (keep existing compilers if any)
        env_menu = menu_bar.addMenu("Environments")
        env_menu.addAction("Create Environment")
        env_menu.addAction("Configure Environment")
        env_menu.addAction("Create Custom Environment")
        help_menu = menu_bar.addMenu("Help")
        help_menu.addAction("Documentation")
        help_menu.addAction("Tutorial")
        help_menu.addAction("About Developer")
        tools_menu = menu_bar.addMenu("Tools")
        process_manager_action = QAction("Process Manager", self)
        process_manager_action.triggered.connect(self.open_process_manager)
        tools_menu.addAction(process_manager_action)
        tools_menu.addAction("Control Panel")
        open_pdf_action = QAction("Open PDF", self)
        open_pdf_action.triggered.connect(self.open_pdf_file)
        tools_menu.addAction(open_pdf_action)
        open_image_action = QAction("Open Image", self)
        open_image_action.triggered.connect(self.open_image_file)
        tools_menu.addAction(open_image_action)
        tools_menu.addAction("Diagramm Sketch", self.open_diagramm_sketch)
        tools_menu.addAction("View Editor Source Code")
        music_player_action = QAction("Music Player", self)
        music_player_action.triggered.connect(self.open_music_player)
        tools_menu.addAction(music_player_action)
        
        # Advanced loading option
        advanced_loading_action = QAction("Open Large File (Advanced Loading)", self)
        advanced_loading_action.triggered.connect(self.open_large_file_advanced)
        tools_menu.addAction(advanced_loading_action)

    def open_syntax_highlighting_dialog(self):
        dlg = SyntaxHighlightingDialog(self)
        dlg.exec_()
        # Optionally: reload all editor highlighters if their config changed

    def apply_theme(self, theme_key):
        app = QApplication.instance()
        theme_data = theme_manager_singleton.apply_theme(app, theme_key)
        self.theme = theme_manager_singleton.current_theme_key
        for editor in self.editors:
            if hasattr(editor, "set_theme"):
                editor.set_theme(theme_data)
        # Update menu bar styling
        self.update_menu_bar_theme(theme_data)
        # Update separator styling
        self.update_separator_theme(theme_data)
        # Always use classic style
        self.setStyleSheet(get_classic_styles(theme_data))

    def update_menu_bar_theme(self, theme_data):
        """Update menu bar styling to match the current theme"""
        menu_style = get_menu_bar_styles(theme_data)
        self.menuBar().setStyleSheet(menu_style)

    def update_separator_theme(self, theme_data):
        """Update separator styling between minimap and numberline"""
        separator_style = get_separator_styles(theme_data)
        
        # Apply to main splitter and editor splitter
        self.main_splitter.setStyleSheet(separator_style)
        self.editor_splitter.setStyleSheet(separator_style)

    def on_theme_changed(self, theme_data):
        """Handle theme changes from the theme manager"""
        self.theme = theme_manager_singleton.current_theme_key
        # Update menu bar and separators
        self.update_menu_bar_theme(theme_data)
        self.update_separator_theme(theme_data)
        # Always use classic style
        self.setStyleSheet(get_classic_styles(theme_data))

    def set_dark_theme(self):
        self.apply_theme("dark")

    def set_light_theme(self):
        self.apply_theme("light")

    def open_theme_manager(self):
        dialog = ThemeManagerDialog(self, self.theme)
        if dialog.exec_():
            selected_theme = dialog.get_selected_theme_key()
            if selected_theme != self.theme:
                self.apply_theme(selected_theme)

    def font_editor(self):
        from global_.font_editor import FontEditor
        self.font_editor_window = FontEditor()
        self.font_editor_window.settings_applied.connect(self.apply_font_from_editor)
        self.font_editor_window.show()

    def apply_font_from_editor(self, font):
        self.current_font = font
        for editor in self.editors:
            # Update all tabs in the editor
            for i in range(editor.count()):
                tab = editor.widget(i)
                if hasattr(tab, "editor"):
                    # Only update the editor text and number line
                    tab.editor.setFont(font)
                    if hasattr(tab, "numberline"):
                        tab.numberline.setFont(font)
                        tab.numberline.update()
                    # Update minimap if present
                    if hasattr(tab, "minimap"):
                        tab.minimap.update()
        if self.console_panel:
            self.console_panel.set_font(font)

    def trigger_undo(self):
        widget = self.get_active_tabwidget().currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.undo()

    def trigger_redo(self):
        widget = self.get_active_tabwidget().currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.redo()

    def trigger_select_all(self):
        widget = self.get_active_tabwidget().currentWidget()
        if widget and hasattr(widget, "editor"):
            widget.editor.selectAll()

    def view_toggle_numberline(self):
        self.show_numberline = not self.show_numberline
        for editor in self.editors:
            for i in range(editor.count()):
                tab = editor.widget(i)
                if hasattr(tab, "numberline"):
                    tab.numberline.setVisible(self.show_numberline)

    def toggle_minimap(self):
        for editor in self.editors:
            for i in range(editor.count()):
                tab = editor.widget(i)
                if hasattr(tab, "minimap"):
                    tab.minimap.setVisible(not tab.minimap.isVisible())

    def rotate_number_line(self):
        self.numberline_on_left = not self.numberline_on_left
        for editor in self.editors:
            for i in range(editor.count()):
                tab = editor.widget(i)
                if hasattr(tab, "set_numberline_side"):
                    tab.set_numberline_side(self.numberline_on_left)

    def new_file(self):
        try:
            # Assembly Emulator integration
            from global_.assembly_emulator_tab import AssemblyEmulatorTab
            current_widget = self.get_active_tabwidget().currentWidget()
            if isinstance(current_widget, AssemblyEmulatorTab):
                current_widget.new_file()
                self.get_active_tabwidget().setTabText(self.get_active_tabwidget().currentIndex(), "CPU Emulator")
                return
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
            # Assembly Emulator integration
            from global_.assembly_emulator_tab import AssemblyEmulatorTab
            current_widget = self.get_active_tabwidget().currentWidget()
            if isinstance(current_widget, AssemblyEmulatorTab):
                current_widget.open_file(file_name)
                self.get_active_tabwidget().setTabText(self.get_active_tabwidget().currentIndex(), os.path.basename(file_name))
                return
            self.open_file_in_editor_tab(file_name)

    def save_file(self):
        current_widget = self.get_active_tabwidget().currentWidget()
        if not current_widget:
            return
        # Assembly Emulator integration
        from global_.assembly_emulator_tab import AssemblyEmulatorTab
        if isinstance(current_widget, AssemblyEmulatorTab):
            current_widget.save_file()
            if current_widget._file_path:
                self.get_active_tabwidget().setTabText(self.get_active_tabwidget().currentIndex(), os.path.basename(current_widget._file_path))
            return
        if hasattr(current_widget, 'editor'):
            editor = current_widget.editor
            content = editor.toPlainText()
        else:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save File", "",
            "All Files (*);;Text Files (*.txt);;Python Files (*.py)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.get_active_tabwidget().setTabText(self.get_active_tabwidget().currentIndex(), os.path.basename(file_path))
                current_widget._file_path = file_path
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {str(e)}")

    def duplicate_file(self):
        current_index = self.get_active_tabwidget().currentIndex()
        if current_index == -1:
            return
        current_widget = self.get_active_tabwidget().widget(current_index)
        if not hasattr(current_widget, "editor"):
            QMessageBox.warning(self, "Warning", "Cannot duplicate this tab")
            return
        editor = current_widget.editor
        content = editor.toPlainText()
        original_name = self.get_active_tabwidget().tabText(current_index)
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

    def open_music_player(self):
        try:
            from global_.music_player import MusicPlayerWidget
            if not self.music_player:
                self.music_player = QWidget()
                self.music_player.setWindowTitle("Music Player")
                layout = QVBoxLayout(self.music_player)
                player_widget = MusicPlayerWidget(self.music_player)
                layout.addWidget(player_widget)
                self.music_player.resize(500, 400)
            self.music_player.show()
            self.music_player.activateWindow()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Music Player: {str(e)}")

    def open_pdf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if file_path:
            self.get_active_tabwidget().add_pdf_tab(file_path)

    def open_image_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp);;All Files (*)"
        )
        if file_path:
            self.get_active_tabwidget().add_image_tab(file_path)

    def open_diagramm_sketch(self):
        self.get_active_tabwidget().add_diagramm_sketch_tab()

    def enable_code_explorer(self):
        current_tab = self.get_active_tabwidget().currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
        file_path = getattr(current_tab, "_file_path", None)
        content = current_tab.editor.toPlainText()
        if not content:
            QMessageBox.warning(self, "Warning", "No content to analyze.")
            return
        temp_file = None
        if not file_path:
            import tempfile
            fd, temp_file = tempfile.mkstemp(suffix='.py')
            os.close(fd)
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            file_path = temp_file
        try:
            self.get_active_tabwidget().add_code_explorer_tab(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Code Explorer: {str(e)}")
        if temp_file:
            try:
                QTimer.singleShot(5000, lambda: os.remove(temp_file) if os.path.exists(temp_file) else None)
            except:
                pass

    def toggle_console(self):
        if self.console_panel:
            self.console_panel.setVisible(not self.console_panel.isVisible())
            if self.console_panel.isVisible():
                self.console_panel.tabs.setFocus()

    def create_checkpoint(self):
        current_tab = self.get_active_tabwidget().currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
        editor = current_tab.editor
        cursor = editor.textCursor()
        line_number = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        dialog = CheckpointDialog(self, line_number=line_number, file_path=file_path)
        if dialog.exec_():
            checkpoint = dialog.get_checkpoint()
            if checkpoint:
                self.checkpoint_manager.add_checkpoint(checkpoint)
                self.highlight_checkpoint(current_tab, checkpoint)
                QMessageBox.information(
                    self,
                    "Checkpoint Created",
                    f"Checkpoint '{checkpoint.name}' created at line {line_number + 1}."
                )

    def highlight_checkpoint(self, tab, checkpoint):
        if not hasattr(tab, "editor"):
            return
        editor = tab.editor
        format = self.checkpoint_manager.get_format_for_checkpoint(checkpoint)
        cursor = QTextCursor(editor.document().findBlockByNumber(checkpoint.line_number))
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.setCharFormat(format)

    def goto_next_checkpoint(self):
        current_tab = self.get_active_tabwidget().currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
        editor = current_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please save the file first.")
            return
        next_checkpoint = self.checkpoint_manager.get_next_checkpoint(file_path, current_line)
        if next_checkpoint:
            self.goto_checkpoint_line(editor, next_checkpoint.line_number)
        else:
            QMessageBox.information(self, "No Checkpoint", "No next checkpoint found.")

    def goto_prev_checkpoint(self):
        current_tab = self.get_active_tabwidget().currentWidget()
        if not current_tab or not hasattr(current_tab, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
        editor = current_tab.editor
        cursor = editor.textCursor()
        current_line = cursor.blockNumber()
        file_path = getattr(current_tab, "_file_path", None)
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please save the file first.")
            return
        prev_checkpoint = self.checkpoint_manager.get_prev_checkpoint(file_path, current_line)
        if prev_checkpoint:
            self.goto_checkpoint_line(editor, prev_checkpoint.line_number)
        else:
            QMessageBox.information(self, "No Checkpoint", "No previous checkpoint found.")

    def goto_checkpoint_line(self, editor, line_number):
        cursor = QTextCursor(editor.document().findBlockByNumber(line_number))
        editor.setTextCursor(cursor)
        editor.centerCursor()

    def open_checkpoint_manager(self):
        dialog = CheckpointManagerDialog(self, self.checkpoint_manager)
        if dialog.exec_() and dialog.selected_checkpoint:
            checkpoint = dialog.get_selected_checkpoint()
            if checkpoint and checkpoint.file_path:
                self.open_file_in_editor_tab(checkpoint.file_path)
                tab_widget = self.get_active_tabwidget()
                for i in range(tab_widget.count()):
                    tab = tab_widget.widget(i)
                    if hasattr(tab, "_file_path") and tab._file_path == checkpoint.file_path:
                        tab_widget.setCurrentIndex(i)
                        if hasattr(tab, "editor"):
                            self.goto_checkpoint_line(tab.editor, checkpoint.line_number)
                        break

    def open_search_dialog(self, mode="find"):
        """Open the search dialog with the specified mode"""
        current_widget = self.get_active_tabwidget().currentWidget()
        if not current_widget or not hasattr(current_widget, "editor"):
            QMessageBox.warning(self, "Warning", "No editor tab active.")
            return
            
        from global_.edit_actions import open_search_replace_dialog
        open_search_replace_dialog(self, current_widget.editor, mode)

    def handle_split_action(self):
        if self.canvas_parent is not None:
            self.canvas_parent.add_split_editor()
        else:
            self.open_new_window()

    def open_new_window(self):
        new_window = TextEditor()
        new_window.show()
        self.child_windows.append(new_window)

    def open_assembly_emulator_tab(self):
        from global_.assembly_emulator_tab import AssemblyEmulatorTab
        tab_widget = self.get_active_tabwidget()
        emulator_tab = AssemblyEmulatorTab(self)
        tab_widget.addTab(emulator_tab, "CPU Emulator")
        tab_widget.setCurrentWidget(emulator_tab)

    def open_process_manager(self):
        """Open the process manager in a new tab"""
        try:
            from global_.task_manager import create_task_manager_tab
            task_manager_widget = create_task_manager_tab(self)
            self.get_active_tabwidget().addTab(task_manager_widget, "Process Manager")
            self.get_active_tabwidget().setCurrentWidget(task_manager_widget)
        except ImportError as e:
            QMessageBox.critical(self, "Error", f"Failed to load Process Manager: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Process Manager: {str(e)}")

    def open_large_file_advanced(self):
        """Open a file using advanced loading regardless of size"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Large File (Advanced Loading)")
        if file_name:
            try:
                from advancedloading import load_large_file
                result = load_large_file(file_name, self)
                if result is not None:
                    content, use_advanced_editor = result
                    title = os.path.basename(file_name)
                    
                    if use_advanced_editor:
                        # Use advanced editor for large files
                        if not self.get_active_tabwidget().add_advanced_editor_tab(file_name):
                            QMessageBox.warning(self, "Warning", "Failed to create advanced editor")
                    else:
                        # Use normal editor with loaded content
                        self.get_active_tabwidget().add_editor_tab(
                            title=title, 
                            content=content, 
                            font=self.current_font,
                            numberline_on_left=self.numberline_on_left, 
                            file_path=file_name
                        )
            except ImportError:
                QMessageBox.warning(self, "Warning", "Advanced loading module not available")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def get_tabs(self):
        # For dynamic saving compatibility
        return self.get_active_tabwidget()
    @property
    def tabs(self):
        return self.get_tabs()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        set_dark_palette(app)
        app.setStyle(QStyleFactory.create("Fusion"))
        window = TextEditor()
        edit_actions.connect_edit_menu(window)
        keybinds.integrate_keybinds_menu(window)
        window.show()
        sys.exit(app.exec_())
    except Exception as exc:
        print('An error occurred while running the application:', exc)
        import traceback
        traceback.print_exc()
