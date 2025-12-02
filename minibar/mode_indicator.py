"""
Visual indicator showing the current editing mode.
"""

from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt


class ModeIndicator(QLabel):
    """Visual indicator for the current editing mode."""
    
    MODE_STYLES = {
        "normal": {
            "bg": "#2d2d2d",
            "fg": "#cccccc",
            "text": "NORMAL",
            "symbol": "●"
        },
        "vim": {
            "bg": "#4a9eff",
            "fg": "#ffffff",
            "text": "VIM",
            "symbol": "▶"
        },
        "vim-insert": {
            "bg": "#ff9800",
            "fg": "#ffffff",
            "text": "INSERT",
            "symbol": "▶"
        },
        "vim-replace": {
            "bg": "#f44336",
            "fg": "#ffffff",
            "text": "REPLACE",
            "symbol": "▶"
        },
        "emacs": {
            "bg": "#9c27b0",
            "fg": "#ffffff",
            "text": "EMACS",
            "symbol": "◇"
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 10, QFont.Bold))
        self.setFixedWidth(100)
        self.setAlignment(Qt.AlignCenter)
        self.set_mode("normal")
    
    def set_mode(self, mode: str, submode: str = None):
        """Update the indicator to show the specified mode."""
        # Determine display mode
        if mode == "vim" and submode:
            display_mode = f"vim-{submode}"
        else:
            display_mode = mode
        
        style = self.MODE_STYLES.get(display_mode, self.MODE_STYLES["normal"])
        
        # Build display text
        if mode == "vim" and submode:
            text = f"{style['symbol']} {submode.upper()}"
        else:
            text = f"{style['symbol']} {style['text']}"
        
        self.setText(text)
        self.setStyleSheet(
            f"background-color: {style['bg']}; "
            f"color: {style['fg']}; "
            f"border: none; "
            f"padding: 2px 8px; "
            f"font-weight: bold;"
        )

