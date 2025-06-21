import json
import os
from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import QRegExp

# Update LANGC_DIR to use the global folder
LANGC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'langc')

def get_available_languages():
    """Auto-detect available languages by scanning langc/ for .json files."""
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(LANGC_DIR)
        if f.endswith('.json')
    ]

def load_highlight_config(language):
    """Load syntax highlighting config, or None if not found/invalid."""
    file_path = os.path.join(LANGC_DIR, f'{language}.json')
    if not os.path.exists(file_path):
        print(f"[SyntaxHighlighter] Warning: No syntax config for language: {language}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[SyntaxHighlighter] Failed to load config for '{language}': {e}")
        return None

def make_format(fmt_dict):
    fmt = QTextCharFormat()
    color = fmt_dict.get("color", "#000")
    if color:
        fmt.setForeground(QColor(color))
    if fmt_dict.get("bold"):
        fmt.setFontWeight(QFont.Bold)
    if fmt_dict.get("italic"):
        fmt.setFontItalic(True)
    if fmt_dict.get("underline"):
        fmt.setFontUnderline(True)
    return fmt

class GenericHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language="plain"):
        super().__init__(document)
        self.config = None
        self.highlightingRules = []
        self.multiLineRules = []
        self.set_language(language)

    def set_language(self, language):
        """Set new language and reload rules, fallback to no-highlighting on error."""
        self.language = language
        self.load_rules(language)
        self.rehighlight()

    def load_rules(self, language):
        self.highlightingRules = []
        self.multiLineRules = []
        self.config = load_highlight_config(language)
        if not self.config:
            return  # No rules for this language
        for rule in self.config.get("rules", []):
            fmt = make_format(rule.get("format", {}))
            for pattern in rule.get("patterns", []):
                regex = QRegExp(pattern)
                self.highlightingRules.append((regex, fmt))
        for ml_rule in self.config.get("multiline", []):
            fmt = make_format(ml_rule.get("format", {}))
            start = QRegExp(ml_rule.get("start", ""))
            end = QRegExp(ml_rule.get("end", ""))
            self.multiLineRules.append((start, end, fmt))

    def highlightBlock(self, text):
        if not self.config:
            return
        # Single-line rules
        for pattern, fmt in self.highlightingRules:
            index = pattern.indexIn(text, 0)
            while index >= 0:
                length = pattern.matchedLength()
                self.setFormat(index, length, fmt)
                index = pattern.indexIn(text, index + length)
        # Multiline rules
        for start, end, fmt in self.multiLineRules:
            self.setCurrentBlockState(0)
            startIndex = 0
            if self.previousBlockState() != 1:
                startIndex = start.indexIn(text)
            while startIndex >= 0:
                endIndex = end.indexIn(text, startIndex + start.matchedLength())
                if endIndex == -1:
                    self.setCurrentBlockState(1)
                    blockLen = len(text) - startIndex
                else:
                    blockLen = endIndex - startIndex + end.matchedLength()
                self.setFormat(startIndex, blockLen, fmt)
                if endIndex == -1:
                    break
                startIndex = start.indexIn(text, startIndex + blockLen)
