from PyQt5.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt5.QtCore import QRegExp

class LatexHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        # Command format
        command_format = QTextCharFormat()
        command_format.setForeground(QColor("#569CD6"))
        command_format.setFontWeight(QFont.Bold)
        self.highlighting_rules.append((QRegExp(r"\\[a-zA-Z]+"), command_format))
        # Comment format
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        self.highlighting_rules.append((QRegExp(r"%[^\n]*"), comment_format))
        # Math mode
        math_format = QTextCharFormat()
        math_format.setForeground(QColor("#B5CEA8"))
        self.highlighting_rules.append((QRegExp(r"\$[^$]*\$"), math_format))
        # Braces
        brace_format = QTextCharFormat()
        brace_format.setForeground(QColor("#DCDCAA"))
        self.highlighting_rules.append((QRegExp(r"[{}]"), brace_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            expression = QRegExp(pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, fmt)
                index = expression.indexIn(text, index + length) 