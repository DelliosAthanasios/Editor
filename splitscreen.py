from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox, QDialogButtonBox, QWidget, QSplitter
)
from PyQt5.QtCore import Qt

class SplitChoiceDialog(QDialog):
    def __init__(self, tab_names, theme='dark', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Tab to Split")
        layout = QVBoxLayout(self)
        label = QLabel("Which window do you want to split?")
        layout.addWidget(label)
        self.combo = QComboBox()
        self.combo.addItems(tab_names)
        layout.addWidget(self.combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Theming to match main.py's dark/light mode
        if theme == 'dark':
            self.setStyleSheet("""
                QDialog { background-color: #2b2b2b; color: white; }
                QLabel, QComboBox, QPushButton, QDialogButtonBox { color: white; }
            """)
        else:
            self.setStyleSheet("")

    def selected_tab_index(self):
        return self.combo.currentIndex()

def split_tab(tab_widget, index, orientation=Qt.Horizontal):
    """
    Splits the widget at tab index with a new instance of the same widget (copy of content).
    orientation: Qt.Horizontal (vertical split visually), Qt.Vertical (horizontal split visually)
    """
    # If this tab is already a splitter, do not allow further splitting (for simplicity)
    original_widget = tab_widget.widget(index)
    if isinstance(original_widget, QSplitter):
        # If already a splitter, ask which pane to split (advanced, not implemented here)
        return

    # Only split editor tabs (not file explorer, etc.)
    if not hasattr(original_widget, "editor"):
        return

    # Create a new instance of the same tab and copy the content/font
    # Delayed import to avoid circular import
    from main import EditorTabWidget

    # Copy font, numberline position and content
    new_tab = EditorTabWidget(
        font=original_widget.editor.font(),
        numberline_on_left=getattr(original_widget, "numberline_on_left", True)
    )
    new_tab.editor.setPlainText(original_widget.editor.toPlainText())

    # Remove the original tab
    tab_title = tab_widget.tabText(index)
    tab_widget.removeTab(index)

    # Build a splitter and add both widgets
    splitter = QSplitter(orientation)
    splitter.addWidget(original_widget)
    splitter.addWidget(new_tab)

    # Insert the splitter as a new tab, with a similar title
    new_title = f"{tab_title} (Split)"
    tab_widget.insertTab(index, splitter, new_title)
    tab_widget.setCurrentIndex(index)