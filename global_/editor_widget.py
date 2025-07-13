import os
import json
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTextEdit
from PyQt5.QtGui import QFont
from global_.theme_manager import theme_manager_singleton, get_editor_styles
from global_.minimap import Minimap
from global_.numberline import NumberLine
from global_.syntax_highlighter import GenericHighlighter
from global_.language_detection import detect_language_by_extension

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