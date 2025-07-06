import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QSplitter
)
from PyQt5.QtCore import Qt

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

if __name__ == '__main__':
    app = QApplication([])
    window = StyleChooser()
    window.show()
    app.exec_() 