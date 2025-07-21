import os
import sys
import shutil
import inspect
import importlib.util
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter, QComboBox, QFileSystemModel, QTreeView, QTabWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QDir
from user_mode.config_loader import load_config
from user_mode.api import EditorAPI
from user_mode import plugin_loader

EDITOR_ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(EDITOR_ROOT)
BACKUP_DIR = os.path.join(EDITOR_ROOT, "changes", "default.backup")

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
GLOBAL_DIR = os.path.join(os.path.dirname(__file__), 'global_')

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

# Utility: backup full editor if not already
def backup_editor():
    if not os.listdir(BACKUP_DIR):
        for item in os.listdir(PROJECT_ROOT):
            if item not in ["user_mode", "addons", "__pycache__"]:
                s = os.path.join(PROJECT_ROOT, item)
                d = os.path.join(BACKUP_DIR, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)

# Utility: find all PyQt UI classes in a .py file
def find_pyqt_ui_classes(path):
    classes = []
    try:
        spec = importlib.util.spec_from_file_location("_mod", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, QWidget) and obj.__module__ == mod.__name__:
                classes.append((name, obj))
    except Exception:
        pass
    return classes

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
    def __init__(self, main_window=None, theme_editor_path=None, font_editor_path=None):
        super().__init__()
        self.setWindowTitle("User Mode - Advanced Customization")
        self.setGeometry(100, 50, 1400, 900)
        self.main_window = main_window
        self.theme_editor_path = theme_editor_path
        self.font_editor_path = font_editor_path
        self.api = EditorAPI(main_window)
        self.init_ui()
        self.load_and_apply_profile(os.path.join(EDITOR_ROOT, "user_mode", "user_profile.json"))

    def init_ui(self):
        central = QWidget()
        layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 2)

        # --- UI Elements Tab ---
        self.ui_tab = QWidget()
        ui_layout = QVBoxLayout(self.ui_tab)
        self.ui_list = QListWidget()
        self.ui_list.itemSelectionChanged.connect(self.on_ui_element_selected)
        ui_layout.addWidget(QLabel("UI Elements (PyQt classes):"))
        ui_layout.addWidget(self.ui_list, 1)
        self.ui_code = QTextEdit()
        self.ui_code.setReadOnly(False)
        ui_layout.addWidget(self.ui_code, 3)
        self.ui_save_btn = QPushButton("Save UI Edit")
        self.ui_save_btn.clicked.connect(self.save_ui_edit)
        ui_layout.addWidget(self.ui_save_btn)
        self.ui_reload_btn = QPushButton("Reload UI File")
        self.ui_reload_btn.clicked.connect(self.reload_ui_file)
        self.ui_restore_btn = QPushButton("Restore UI from Backup")
        self.ui_restore_btn.clicked.connect(self.restore_ui_from_backup)
        ui_layout.addWidget(self.ui_reload_btn)
        ui_layout.addWidget(self.ui_restore_btn)
        self.tabs.addTab(self.ui_tab, "UI Elements")
        self.populate_ui_elements()

        # --- Logic Tab ---
        self.logic_tab = QWidget()
        logic_layout = QVBoxLayout(self.logic_tab)
        logic_layout.addWidget(QLabel("Logic (non-UI Python code):"))
        self.logic_list = QListWidget()
        self.logic_list.itemSelectionChanged.connect(self.on_logic_selected)
        logic_layout.addWidget(self.logic_list, 1)
        self.logic_code = QTextEdit()
        self.logic_code.setReadOnly(False)
        logic_layout.addWidget(self.logic_code, 3)
        self.logic_save_btn = QPushButton("Save Logic Edit")
        self.logic_save_btn.clicked.connect(self.save_logic_edit)
        logic_layout.addWidget(self.logic_save_btn)
        self.logic_reload_btn = QPushButton("Reload Logic File")
        self.logic_reload_btn.clicked.connect(self.reload_logic_file)
        self.logic_restore_btn = QPushButton("Restore Logic from Backup")
        self.logic_restore_btn.clicked.connect(self.restore_logic_from_backup)
        logic_layout.addWidget(self.logic_reload_btn)
        logic_layout.addWidget(self.logic_restore_btn)
        self.tabs.addTab(self.logic_tab, "Logic")
        self.populate_logic_files()

        # --- Addons Tab ---
        self.addons_tab = QWidget()
        addons_layout = QVBoxLayout(self.addons_tab)
        addons_layout.addWidget(QLabel("Addons (user scripts/plugins):"))
        self.addons_list = QListWidget()
        self.addons_list.itemSelectionChanged.connect(self.on_addon_selected)
        addons_layout.addWidget(self.addons_list, 1)
        self.addon_code = QTextEdit()
        self.addon_code.setReadOnly(False)
        addons_layout.addWidget(self.addon_code, 3)
        self.addon_save_btn = QPushButton("Save Addon Edit")
        self.addon_save_btn.clicked.connect(self.save_addon_edit)
        addons_layout.addWidget(self.addon_save_btn)
        self.addon_enable_btn = QPushButton("Enable/Disable Addon")
        self.addon_enable_btn.clicked.connect(self.toggle_addon_enabled)
        addons_layout.addWidget(self.addon_enable_btn)
        self.addon_reload_btn = QPushButton("Reload Addon")
        self.addon_reload_btn.clicked.connect(self.reload_addon)
        self.addon_remove_btn = QPushButton("Remove Addon")
        self.addon_remove_btn.clicked.connect(self.remove_addon)
        self.addon_install_btn = QPushButton("Install Addon from File")
        self.addon_install_btn.clicked.connect(self.install_addon)
        self.addon_restore_btn = QPushButton("Restore Addon from Backup")
        self.addon_restore_btn.clicked.connect(self.restore_addon_from_backup)
        addons_layout.addWidget(self.addon_reload_btn)
        addons_layout.addWidget(self.addon_remove_btn)
        addons_layout.addWidget(self.addon_install_btn)
        addons_layout.addWidget(self.addon_restore_btn)
        self.tabs.addTab(self.addons_tab, "Addons")
        self.populate_addons()

        # --- Help Tab ---
        self.help_tab = QWidget()
        help_layout = QVBoxLayout(self.help_tab)
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setPlainText(self.generate_help_text())
        help_layout.addWidget(help_text)
        self.tabs.addTab(self.help_tab, "Help")

        # Right panel: Theme/Font Editor, Profile, Prompt
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
        right_panel.addWidget(QLabel("Live Python Prompt (context: api, main_window, output)"))
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("Type Python code here. Use api, main_window, output.")
        right_panel.addWidget(self.prompt)
        self.run_btn = QPushButton("Run Prompt")
        self.run_btn.clicked.connect(self.run_prompt)
        right_panel.addWidget(self.run_btn)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("Prompt output and errors will appear here.")
        right_panel.addWidget(self.output)
        right_panel.addStretch(1)

    def populate_ui_elements(self):
        self.ui_list.clear()
        # Scan all .py files for PyQt UI classes
        for root, dirs, files in os.walk(PROJECT_ROOT):
            for fname in files:
                if fname.endswith('.py'):
                    path = os.path.join(root, fname)
                    classes = find_pyqt_ui_classes(path)
                    for name, cls in classes:
                        self.ui_list.addItem(f"{fname}::{name}")
                        # Store mapping for later
                        self.ui_list.item(self.ui_list.count()-1).setData(Qt.UserRole, (path, name))

    def on_ui_element_selected(self):
        items = self.ui_list.selectedItems()
        if not items:
            return
        path, class_name = items[0].data(Qt.UserRole)
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        self.ui_code.setPlainText(code)
        # Optionally: instantiate and show the UI (advanced, not shown here)

    def save_ui_edit(self):
        items = self.ui_list.selectedItems()
        if not items:
            return
        path, class_name = items[0].data(Qt.UserRole)
        # Backup full editor if not already
        if not os.listdir(BACKUP_DIR):
            backup_editor()
        # Save edited code to user_mode/changes/ preserving folder structure
        rel_path = os.path.relpath(path, PROJECT_ROOT)
        save_path = os.path.join(EDITOR_ROOT, "changes", rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(self.ui_code.toPlainText())
        QMessageBox.information(self, "Saved", f"Changes saved to {save_path}")

    def populate_logic_files(self):
        self.logic_list.clear()
        for root, dirs, files in os.walk(PROJECT_ROOT):
            for fname in files:
                if fname.endswith('.py'):
                    path = os.path.join(root, fname)
                    # Only include if no QWidget subclass
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            code = f.read()
                        if 'QWidget' not in code and 'QMainWindow' not in code:
                            self.logic_list.addItem(fname)
                            self.logic_list.item(self.logic_list.count()-1).setData(Qt.UserRole, path)
                    except Exception:
                        continue

    def on_logic_selected(self):
        items = self.logic_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        self.logic_code.setPlainText(code)

    def save_logic_edit(self):
        items = self.logic_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if not os.listdir(BACKUP_DIR):
            backup_editor()
        rel_path = os.path.relpath(path, PROJECT_ROOT)
        save_path = os.path.join(EDITOR_ROOT, "changes", rel_path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(self.logic_code.toPlainText())
        QMessageBox.information(self, "Saved", f"Logic changes saved to {save_path}")

    def populate_addons(self):
        self.addons_list.clear()
        addons_dir = os.path.join(EDITOR_ROOT, "addons")
        # Create addons directory if it doesn't exist
        if not os.path.exists(addons_dir):
            os.makedirs(addons_dir, exist_ok=True)
        for fname in os.listdir(addons_dir):
            if fname.endswith('.py') or fname.endswith('.disabled'):
                path = os.path.join(addons_dir, fname)
                self.addons_list.addItem(fname)
                self.addons_list.item(self.addons_list.count()-1).setData(Qt.UserRole, path)

    def on_addon_selected(self):
        items = self.addons_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        self.addon_code.setPlainText(code)
        # Update enable/disable button text
        if path.endswith('.disabled'):
            self.addon_enable_btn.setText("Enable Addon")
        else:
            self.addon_enable_btn.setText("Disable Addon")

    def save_addon_edit(self):
        items = self.addons_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.addon_code.toPlainText())
        QMessageBox.information(self, "Saved", f"Addon changes saved to {path}")

    def toggle_addon_enabled(self):
        items = self.addons_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        if path.endswith('.disabled'):
            new_path = path[:-9] + '.py'
        else:
            new_path = path[:-3] + '.disabled'
        os.rename(path, new_path)
        self.populate_addons()
        QMessageBox.information(self, "Toggled", f"Addon is now {'enabled' if new_path.endswith('.py') else 'disabled'}: {os.path.basename(new_path)}")

    def generate_help_text(self):
        return (
            "Editor User Mode Help\n\n"
            "- UI Elements: Edit PyQt UI code. Changes are saved to user_mode/changes/.\n"
            "- Logic: (Coming soon) Organize and edit non-UI logic.\n"
            "- Addons: (Coming soon) Manage user plugins/scripts in addons/.\n"
            "- Theme/Font Editor: Launches the regular editor windows.\n"
            "- Live Python Prompt: Run code with access to api, main_window, output.\n"
            "- Backup: On first edit, the full editor is backed up to user_mode/changes/default.backup/.\n"
        )

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
        self.load_and_apply_profile(os.path.join(EDITOR_ROOT, "user_mode", "user_profile.json"))

    def run_prompt(self):
        code = self.prompt.toPlainText()
        local_ctx = {
            "api": self.api,
            "main_window": self.main_window,
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
        if self.theme_editor_path:
            import subprocess
            subprocess.Popen([sys.executable, self.theme_editor_path])
        else:
            QMessageBox.information(self, "Theme Editor", "Theme editor path not set.")

    def launch_font_editor(self):
        if self.font_editor_path:
            import subprocess
            subprocess.Popen([sys.executable, self.font_editor_path])
        else:
            QMessageBox.information(self, "Font Editor", "Font editor path not set.")

    # --- Live reload and restore logic (stubs) ---
    def reload_ui_file(self):
        QMessageBox.information(self, "Reload", "UI file reloaded (stub). Reload the app to see changes.")

    def restore_ui_from_backup(self):
        QMessageBox.information(self, "Restore", "UI file restored from backup (stub).")

    def reload_logic_file(self):
        QMessageBox.information(self, "Reload", "Logic file reloaded (stub). Reload the app to see changes.")

    def restore_logic_from_backup(self):
        QMessageBox.information(self, "Restore", "Logic file restored from backup (stub).")

    def reload_addon(self):
        items = self.addons_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("addon_mod", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            QMessageBox.information(self, "Reloaded", f"Addon {os.path.basename(path)} reloaded.")
        except Exception as e:
            QMessageBox.critical(self, "Reload Error", str(e))

    def remove_addon(self):
        items = self.addons_list.selectedItems()
        if not items:
            return
        path = items[0].data(Qt.UserRole)
        os.remove(path)
        self.populate_addons()
        QMessageBox.information(self, "Removed", f"Addon {os.path.basename(path)} removed.")

    def install_addon(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select Addon Python File", "", "Python Files (*.py)")
        if fname:
            dest = os.path.join(EDITOR_ROOT, "addons", os.path.basename(fname))
            shutil.copy2(fname, dest)
            self.populate_addons()
            QMessageBox.information(self, "Installed", f"Addon {os.path.basename(fname)} installed.")

    def restore_addon_from_backup(self):
        QMessageBox.information(self, "Restore", "Addon restored from backup (stub).")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UserModeWindow()
    window.show()
    sys.exit(app.exec_()) 