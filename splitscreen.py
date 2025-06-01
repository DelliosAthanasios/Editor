from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, 
    QDialogButtonBox, QWidget, QSplitter, QGridLayout, QCheckBox, QGroupBox,
    QRadioButton, QButtonGroup, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal

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

        # Add orientation choice
        orientation_group = QGroupBox("Split Orientation")
        orientation_layout = QVBoxLayout()
        self.horizontal_radio = QRadioButton("Horizontal Split (Side by Side)")
        self.vertical_radio = QRadioButton("Vertical Split (Top and Bottom)")
        self.horizontal_radio.setChecked(True)
        orientation_layout.addWidget(self.horizontal_radio)
        orientation_layout.addWidget(self.vertical_radio)
        orientation_group.setLayout(orientation_layout)
        layout.addWidget(orientation_group)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Theming to match main.py's theme
        if theme == 'dark':
            self.setStyleSheet("""
                QDialog { background-color: #2b2b2b; color: white; }
                QLabel, QComboBox, QPushButton, QDialogButtonBox, QGroupBox, QRadioButton { color: white; }
                QGroupBox { border: 1px solid #444; border-radius: 5px; margin-top: 1ex; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
            """)
        else:
            self.setStyleSheet("")

    def selected_tab_index(self):
        return self.combo.currentIndex()
        
    def get_orientation(self):
        return Qt.Horizontal if self.horizontal_radio.isChecked() else Qt.Vertical

class CustomSplitDialog(QDialog):
    def __init__(self, tab_names, theme='dark', parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Split Configuration")
        self.tab_names = tab_names
        self.theme = theme
        self.selected_tabs = []
        self.split_config = "2x1"  # Default: 2 columns, 1 row
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab selection
        tab_group = QGroupBox("Select Tabs to Include")
        tab_layout = QVBoxLayout()
        self.tab_checkboxes = []
        
        for i, name in enumerate(self.tab_names):
            checkbox = QCheckBox(name)
            if i < 2:  # Select first two tabs by default
                checkbox.setChecked(True)
            self.tab_checkboxes.append(checkbox)
            tab_layout.addWidget(checkbox)
            
        tab_group.setLayout(tab_layout)
        layout.addWidget(tab_group)
        
        # Layout configuration
        layout_group = QGroupBox("Layout Configuration")
        layout_grid = QGridLayout()
        
        # Layout options with visual representation
        self.layout_options = {
            "1x2": self.create_layout_preview("1x2", 1, 2),
            "2x1": self.create_layout_preview("2x1", 2, 1),
            "2x2": self.create_layout_preview("2x2", 2, 2),
            "3x1": self.create_layout_preview("3x1", 3, 1),
            "1x3": self.create_layout_preview("1x3", 1, 3)
        }
        
        # Add layout options to grid
        layout_grid.addWidget(self.layout_options["2x1"], 0, 0)
        layout_grid.addWidget(self.layout_options["1x2"], 0, 1)
        layout_grid.addWidget(self.layout_options["2x2"], 1, 0)
        layout_grid.addWidget(self.layout_options["3x1"], 1, 1)
        layout_grid.addWidget(self.layout_options["1x3"], 2, 0, 1, 2)
        
        layout_group.setLayout(layout_grid)
        layout.addWidget(layout_group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Apply theme
        if self.theme == 'dark':
            self.setStyleSheet("""
                QDialog { background-color: #2b2b2b; color: white; }
                QLabel, QComboBox, QPushButton, QDialogButtonBox, QGroupBox, QCheckBox, QRadioButton { color: white; }
                QGroupBox { border: 1px solid #444; border-radius: 5px; margin-top: 1ex; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; }
            """)
        
        self.resize(500, 500)
        
    def create_layout_preview(self, name, cols, rows):
        """Create a visual preview of the layout configuration."""
        group = QGroupBox(f"{name} ({cols}x{rows})")
        group_layout = QVBoxLayout()
        
        # Create a frame to show the layout visually
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setMinimumHeight(80)
        frame.setMinimumWidth(120)
        
        # Create a grid layout to represent the split
        preview_layout = QGridLayout(frame)
        preview_layout.setSpacing(2)
        
        # Add cells to represent the split areas
        for row in range(rows):
            for col in range(cols):
                cell = QFrame()
                cell.setFrameShape(QFrame.Box)
                cell.setStyleSheet("background-color: #444;")
                preview_layout.addWidget(cell, row, col)
        
        group_layout.addWidget(frame)
        
        # Add radio button for selection
        radio = QRadioButton("Select")
        radio.setChecked(name == self.split_config)
        radio.toggled.connect(lambda checked, n=name: self.on_layout_selected(n, checked))
        group_layout.addWidget(radio)
        
        group.setLayout(group_layout)
        return group
        
    def on_layout_selected(self, name, checked):
        """Handle layout selection."""
        if checked:
            self.split_config = name
            
    def get_selected_tabs(self):
        """Get the indices of selected tabs."""
        selected = []
        for i, checkbox in enumerate(self.tab_checkboxes):
            if checkbox.isChecked():
                selected.append(i)
        return selected
        
    def get_layout_config(self):
        """Get the selected layout configuration."""
        cols, rows = map(int, self.split_config.split('x'))
        return cols, rows

def split_tab(tab_widget, index, orientation=Qt.Horizontal):
    """
    Splits the widget at tab index with a new empty tab.
    orientation: Qt.Horizontal (side by side), Qt.Vertical (top and bottom)
    """
    # If this tab is already a splitter, do not allow further splitting (for simplicity)
    original_widget = tab_widget.widget(index)
    if isinstance(original_widget, QSplitter):
        # If already a splitter, don't split further
        return

    # Only split editor tabs (not file explorer, etc.)
    if not hasattr(original_widget, "editor"):
        return

    # Create a new empty tab with the same font and numberline settings
    # Delayed import to avoid circular import
    from main import EditorTabWidget

    # Create empty tab with same font and numberline settings
    new_tab = EditorTabWidget(
        font=original_widget.editor.font(),
        numberline_on_left=getattr(original_widget, "numberline_on_left", True)
    )
    
    # Remove the original tab
    tab_title = tab_widget.tabText(index)
    tab_widget.removeTab(index)

    # Build a splitter and add both widgets
    splitter = QSplitter(orientation)
    splitter.addWidget(original_widget)
    splitter.addWidget(new_tab)
    
    # Set equal sizes for the split panes
    splitter.setSizes([1, 1])

    # Insert the splitter as a new tab, with a similar title
    new_title = f"{tab_title} (Split)"
    tab_widget.insertTab(index, splitter, new_title)
    tab_widget.setCurrentIndex(index)

def create_custom_split(tab_widget, tab_indices, cols, rows):
    """
    Create a custom split layout with empty tabs.
    
    Args:
        tab_widget: The tab widget containing the tabs
        tab_indices: List of tab indices to include in the split
        cols: Number of columns in the grid
        rows: Number of rows in the grid
    """
    if not tab_indices:
        return
        
    # Create empty widgets for the grid
    widgets = []
    
    # Get font and settings from the first selected tab if possible
    font = None
    numberline_on_left = True
    
    if tab_indices and tab_indices[0] < tab_widget.count():
        original_widget = tab_widget.widget(tab_indices[0])
        if hasattr(original_widget, "editor"):
            font = original_widget.editor.font()
            numberline_on_left = getattr(original_widget, "numberline_on_left", True)
    
    # Create empty tabs for the grid
    from main import EditorTabWidget
    for i in range(cols * rows):
        new_tab = EditorTabWidget(
            font=font,
            numberline_on_left=numberline_on_left
        )
        widgets.append(new_tab)
    
    # Create the main splitter for rows
    main_splitter = QSplitter(Qt.Vertical)
    
    # Create a splitter for each row
    for row in range(rows):
        row_splitter = QSplitter(Qt.Horizontal)
        
        # Add widgets for this row
        for col in range(cols):
            idx = row * cols + col
            if idx < len(widgets):
                row_splitter.addWidget(widgets[idx])
        
        # Set equal sizes for columns
        sizes = [1] * row_splitter.count()
        row_splitter.setSizes(sizes)
        
        # Add the row splitter to the main splitter
        main_splitter.addWidget(row_splitter)
    
    # Set equal sizes for rows
    sizes = [1] * main_splitter.count()
    main_splitter.setSizes(sizes)
    
    # Create a new tab with the custom split
    new_title = "Custom Split"
    new_index = tab_widget.addTab(main_splitter, new_title)
    tab_widget.setCurrentIndex(new_index)
    
    return new_index
