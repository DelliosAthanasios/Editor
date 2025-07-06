import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter, QComboBox, QFileSystemModel, QTreeView
)
from PyQt5.QtCore import Qt, QDir
from user_mode.config_loader import load_config
from user_mode.api import EditorAPI
from user_mode import plugin_loader

# List of main UI elements and their QSS selectors and default QSS
UI_ELEMENTS = [
    ("Main Window", "QMainWindow", "QMainWindow {\n    background: #f6f6f6;\n}"),
    ("Menu Bar", "QMenuBar", "QMenuBar {\n    background: #e4e4e4;\n    color: #222;\n    border-bottom: 1px solid #b0b0b0;\n}"),
    ("Menu Bar Item", "QMenuBar::item", "QMenuBar::item {\n    background: transparent;\n    color: #222;\n    padding: 4px 12px;\n}"),
    ("Menu", "QMenu", "QMenu {\n    background: #e4e4e4;\n    color: #222;\n    border: 1px solid #b0b0b0;\n}"),
    ("Tab Bar", "QTabBar::tab", "QTabBar::tab {\n    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f6f6f6, stop:1 #d0d0d0);\n    color: #222;\n    border: 1px solid #b0b0b0;\n    border-bottom: none;\n    border-top-left-radius: 0px;\n    border-top-right-radius: 0px;\n    min-width: 48px;\n    padding: 3px 10px;\n}"),
    ("Tab Bar Selected", "QTabBar::tab:selected", "QTabBar::tab:selected {\n    background: #cce6ff;\n    color: #000;\n    border: 1.5px solid #3399ff;\n}"),
    ("Button", "QPushButton", "QPushButton {\n    background: #e4e4e4;\n    border: 1px solid #b0b0b0;\n    border-radius: 2px;\n    padding: 4px 12px;\n    color: #222;\n}"),
    ("Button Hover", "QPushButton:hover", "QPushButton:hover {\n    background: #cce6ff;\n}"),
    ("ScrollBar", "QScrollBar:vertical, QScrollBar:horizontal", "QScrollBar:vertical, QScrollBar:horizontal {\n    background: #e4e4e4;\n    width: 18px;\n    margin: 0px;\n    border: 1px solid #b0b0b0;\n}"),
    ("Text Edit", "QTextEdit", "QTextEdit {\n    background: #ffffff;\n    color: #222;\n    selection-background-color: #cce6ff;\n    selection-color: #000;\n}")
]

USER_QSS_PATH = os.path.join(os.path.dirname(__file__), 'user_styles.qss')
GLOBAL_DIR = os.path.join(os.path.dirname(__file__), 'global')

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "user_mode", "user_profile.json")
DEFAULT_PROFILE_PATH = os.path.join(os.path.dirname(__file__), "user_mode", "default_profile.json")

def get_global_entities():
    entities = []
    for fname in os.listdir(GLOBAL_DIR):
        if fname.endswith('.py'):
            entities.append(fname)
    return sorted(entities)

def get_entity_code(entity):
    path = os.path.join(GLOBAL_DIR, entity)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

class StyleChooser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Style Chooser")
        self.setGeometry(200, 200, 1100, 700)
        self.global_entities = get_global_entities()
        self.styles = self.load_styles()
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left: QSS elements
        self.list_widget = QListWidget()
        for name, selector, _ in UI_ELEMENTS:
            self.list_widget.addItem(name)
        self.list_widget.currentRowChanged.connect(self.on_element_selected)
        splitter.addWidget(self.list_widget)

        # Right: global entities
        self.entity_list = QListWidget()
        for entity in self.global_entities:
            self.entity_list.addItem(entity)
        self.entity_list.currentRowChanged.connect(self.on_entity_selected)
        splitter.addWidget(self.entity_list)

        # Main: QSS/code editor
        main_layout = QVBoxLayout()
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        splitter.addWidget(main_widget)

        self.selector_label = QLabel()
        self.qss_editor = QTextEdit()
        self.qss_editor.setFontFamily("Fira Mono")
        self.qss_editor.setFontPointSize(11)
        self.qss_editor.setTabStopDistance(4 * 8)
        self.qss_editor.setLineWrapMode(QTextEdit.NoWrap)
        main_layout.addWidget(self.selector_label)
        main_layout.addWidget(self.qss_editor, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Style")
        self.save_btn.clicked.connect(self.save_current_style)
        self.save_all_btn = QPushButton("Save All")
        self.save_all_btn.clicked.connect(self.save_all_styles)
        self.load_btn = QPushButton("Reload")
        self.load_btn.clicked.connect(self.reload_styles)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.save_all_btn)
        btn_layout.addWidget(self.load_btn)
        main_layout.addLayout(btn_layout)

        splitter.setSizes([180, 180, 700])
        self.list_widget.setCurrentRow(0)
        self.entity_list.setCurrentRow(-1)

    def load_styles(self):
        styles = {selector: default for _, selector, default in UI_ELEMENTS}
        if os.path.exists(USER_QSS_PATH):
            with open(USER_QSS_PATH, 'r', encoding='utf-8') as f:
                qss = f.read()
            for _, selector, default in UI_ELEMENTS:
                block = self.extract_block(qss, selector)
                if block:
                    styles[selector] = block
        return styles

    def extract_block(self, qss, selector):
        start = qss.find(selector)
        if start == -1:
            return ''
        brace = qss.find('{', start)
        if brace == -1:
            return ''
        end = qss.find('}', brace)
        if end == -1:
            return ''
        return qss[start:end+1]

    def on_element_selected(self, row):
        if row < 0:
            return
        name, selector, default = UI_ELEMENTS[row]
        self.selector_label.setText(f"<b>{name}</b> <code>{selector}</code>")
        self.qss_editor.setReadOnly(False)
        self.qss_editor.setPlainText(self.styles.get(selector, default))
        self.entity_list.setCurrentRow(-1)

    def on_entity_selected(self, row):
        if row < 0:
            return
        entity = self.global_entities[row]
        self.selector_label.setText(f"<b>Source: {entity}</b>")
        self.qss_editor.setReadOnly(True)
        self.qss_editor.setPlainText(get_entity_code(entity))
        self.list_widget.setCurrentRow(-1)

    def save_current_style(self):
        row = self.list_widget.currentRow()
        if row < 0:
            return
        _, selector, default = UI_ELEMENTS[row]
        text = self.qss_editor.toPlainText().strip()
        if not text.startswith(selector):
            text = f'{selector} {{\n{text}\n}}'
        self.styles[selector] = text
        self.save_all_styles()
        QMessageBox.information(self, "Saved", f"Style for {selector} saved.")

    def save_all_styles(self):
        with open(USER_QSS_PATH, 'w', encoding='utf-8') as f:
            for _, selector, default in UI_ELEMENTS:
                block = self.styles[selector].strip()
                if block:
                    if not block.endswith('}'): block += '\n}'
                    f.write(block + '\n\n')
        QMessageBox.information(self, "Saved", "All styles saved to user_styles.qss.")

    def reload_styles(self):
        self.styles = self.load_styles()
        self.on_element_selected(self.list_widget.currentRow())
        QMessageBox.information(self, "Reloaded", "Styles reloaded from user_styles.qss.")

class UserModeWindow(QMainWindow):
    def __init__(self, main_window=None, theme_editor=None, font_editor=None):
        super().__init__()
        self.setWindowTitle("User Mode Profile Manager")
        self.setGeometry(200, 100, 1200, 800)
        self.main_window = main_window
        self.theme_editor = theme_editor
        self.font_editor = font_editor
        self.api = EditorAPI(main_window)
        self.init_ui()
        self.load_and_apply_profile(PROFILE_PATH)

    def init_ui(self):
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # File browser (left)
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath(QDir.currentPath())
        self.file_tree = QTreeView()
        self.file_tree.setModel(self.file_model)
        self.file_tree.setRootIndex(self.file_model.index(QDir.currentPath()))
        self.file_tree.setColumnWidth(0, 250)
        self.file_tree.clicked.connect(self.on_file_selected)
        layout.addWidget(self.file_tree, 2)

        # Main area (center)
        main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(main_splitter, 5)

        # Top: code/source viewer
        self.code_view = QTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFontFamily("Fira Mono")
        self.code_view.setFontPointSize(11)
        main_splitter.addWidget(self.code_view)

        # Bottom: live Python prompt and output
        prompt_layout = QVBoxLayout()
        prompt_widget = QWidget()
        prompt_widget.setLayout(prompt_layout)
        main_splitter.addWidget(prompt_widget)

        self.prompt_label = QLabel("<b>Live Python Prompt</b> (context: api, main_window, theme_editor, font_editor)")
        prompt_layout.addWidget(self.prompt_label)
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("Type Python code here. Use api, main_window, theme_editor, font_editor.")
        prompt_layout.addWidget(self.prompt)
        self.run_btn = QPushButton("Run Prompt")
        self.run_btn.clicked.connect(self.run_prompt)
        prompt_layout.addWidget(self.run_btn)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Prompt output and errors will appear here.")
        prompt_layout.addWidget(self.output)

        # Right: profile controls and editor launchers
        right_panel = QVBoxLayout()
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        layout.addWidget(right_widget, 2)
        self.profile_label = QLabel("Active Profile: user_profile.json")
        right_panel.addWidget(self.profile_label)
        self.reload_btn = QPushButton("Reload Profile")
        self.reload_btn.clicked.connect(self.reload_profile)
        right_panel.addWidget(self.reload_btn)
        self.theme_btn = QPushButton("Open Theme Editor")
        self.theme_btn.clicked.connect(self.launch_theme_editor)
        right_panel.addWidget(self.theme_btn)
        self.font_btn = QPushButton("Open Font Editor")
        self.font_btn.clicked.connect(self.launch_font_editor)
        right_panel.addWidget(self.font_btn)
        right_panel.addStretch(1)

    def on_file_selected(self, index):
        path = self.file_model.filePath(index)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    code = f.read()
                self.code_view.setPlainText(code)
            except Exception as e:
                self.code_view.setPlainText(f"Error reading file: {e}")
        else:
            self.code_view.setPlainText("")

    def load_and_apply_profile(self, path):
        try:
            config = load_config(path)
        except Exception as e:
            QMessageBox.critical(self, "Config Error", str(e))
            return
        self.api.set_theme(config["theme"])
        self.api.set_font(**config["font"])
        for plugin_path in config.get("plugins", []):
            plugin_loader.load_plugin(os.path.join("user_mode", plugin_path), self.api)
        for event, hook in config.get("hooks", {}).items():
            if ":" in hook:
                plugin_path, func_name = hook.split(":")
                mod = plugin_loader.load_plugin(os.path.join("user_mode", plugin_path), self.api)
                self.api.register_hook(event, getattr(mod, func_name))
            else:
                self.api.register_hook(event, eval(hook))
        # TODO: Apply other config sections (ui, keybindings, ai_assist, integrations)

    def reload_profile(self):
        self.load_and_apply_profile(PROFILE_PATH)

    def run_prompt(self):
        code = self.prompt.toPlainText()
        local_ctx = {
            "api": self.api,
            "main_window": self.main_window,
            "theme_editor": self.theme_editor,
            "font_editor": self.font_editor,
            "output": self.output
        }
        try:
            old_stdout, old_stderr = sys.stdout, sys.stderr
            from io import StringIO
            sys.stdout = sys.stderr = mystream = StringIO()
            exec(code, local_ctx)
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.output.setPlainText(mystream.getvalue())
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.output.setPlainText(str(e))

    def launch_theme_editor(self):
        if self.theme_editor:
            self.theme_editor.show()
            self.theme_editor.raise_()
        else:
            QMessageBox.information(self, "Theme Editor", "Theme editor is not available in this context.")

    def launch_font_editor(self):
        if self.font_editor:
            self.font_editor.show()
            self.font_editor.raise_()
        else:
            QMessageBox.information(self, "Font Editor", "Font editor is not available in this context.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UserModeWindow()
    window.show()
    sys.exit(app.exec_()) 