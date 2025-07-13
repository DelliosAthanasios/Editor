from PyQt5.QtWidgets import QWidget, QSplitter, QVBoxLayout, QAction, QApplication
from PyQt5.QtCore import Qt
import os
import sys
import importlib.util

class SplitContainer(QWidget):
    """
    Recursively manages splits and editors, always splitting the *actual* existing editor instance.
    When you split, the existing editor stays on one side, and the new split is a *copy* (clone) of the editor state.
    This way, every split has a fully working editor and not a blank canvas.
    """
    def __init__(self, editor_factory, parent=None):
        super().__init__(parent)
        self.editor_factory = editor_factory
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.splitter = None
        self.child_containers = []
        self.current_widget = self.editor_factory()
        self.layout.addWidget(self.current_widget)

    def get_focused_leaf(self):
        if self.splitter is None:
            # This is a leaf.
            if hasattr(self.current_widget, "hasFocus") and self.current_widget.hasFocus():
                return self
            if hasattr(self.current_widget, "currentWidget"):
                widget = self.current_widget.currentWidget()
                if widget and hasattr(widget, "hasFocus") and widget.hasFocus():
                    return self
            return self
        for container in self.child_containers:
            focused_leaf = container.get_focused_leaf()
            if focused_leaf:
                return focused_leaf
        return self.child_containers[0] if self.child_containers else self

    def create_cloned_instance(self):
        """Create a new instance of the editor from the clone directory"""
        clone_main_path = os.path.join("clone", "main.py")
        if os.path.exists(clone_main_path):
            try:
                # Import the cloned main module
                spec = importlib.util.spec_from_file_location("cloned_main", clone_main_path)
                cloned_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cloned_module)
                
                # Create a new instance of TextEditor
                cloned_editor = cloned_module.TextEditor()
                cloned_editor.setWindowFlags(Qt.Widget)  # Make it behave as a widget
                
                # Ensure console is hidden by default in cloned instance
                if hasattr(cloned_editor, 'console_panel'):
                    cloned_editor.console_panel.setVisible(False)
                
                return cloned_editor
            except Exception as e:
                print(f"Error creating cloned instance: {e}")
        return None

    def split(self, orientation):
        """
        Recursively split the focused pane and clone the current editor to the new pane.
        """
        if self.splitter is not None:
            # Already split; delegate to focused child
            leaf = self.get_focused_leaf()
            if leaf is not self:
                return leaf.split(orientation)
            return self

        # Save and remove the current widget from layout
        old_widget = self.current_widget
        self.layout.removeWidget(old_widget)
        old_widget.setParent(None)

        # Create splitter and two containers
        self.splitter = QSplitter(orientation)
        # First container keeps the current editor (including open tabs)
        first_container = SplitContainer(self.editor_factory)
        first_container.replace_with_widget(old_widget)
        # Second container is a clone/copy of the current editor state
        second_container = SplitContainer(self.editor_factory)
        # Create and embed the cloned instance
        cloned_instance = self.create_cloned_instance()
        if cloned_instance:
            # Create a new MainTabWidget without any initial tabs
            from main import MainTabWidget
            new_tab = MainTabWidget(file_open_callback=old_widget.file_open_callback)
            # Add the cloned instance as the only tab
            new_tab.addTab(cloned_instance, "Cloned Editor")
            cloned_instance.show()
            second_container.replace_with_widget(new_tab)
        self.child_containers = [first_container, second_container]
        self.splitter.addWidget(first_container)
        self.splitter.addWidget(second_container)
        self.layout.addWidget(self.splitter)
        self.current_widget = self.splitter
        self.splitter.setSizes([1, 1])
        self.splitter.setChildrenCollapsible(False)
        self.splitter.show()

        # Focus the editor in the new pane
        if hasattr(second_container.current_widget, "setFocus"):
            second_container.current_widget.setFocus()
        return second_container

    def cleanup_cloned_instance(self, widget):
        """Clean up a cloned instance and its resources"""
        if hasattr(widget, "currentWidget"):
            current = widget.currentWidget()
            if current and hasattr(current, "close"):
                current.close()
            if current and hasattr(current, "deleteLater"):
                current.deleteLater()
        if hasattr(widget, "deleteLater"):
            widget.deleteLater()

    def unsplit(self):
        """
        Remove the split at this level, keeping only the focused editor subtree.
        """
        if self.splitter is None or not self.child_containers:
            return

        # Find which child is focused
        focused_container = None
        for container in self.child_containers:
            focused_leaf = container.get_focused_leaf()
            if focused_leaf is not None and (
                (focused_leaf is container) or
                (hasattr(focused_leaf.current_widget, "hasFocus") and focused_leaf.current_widget.hasFocus())
            ):
                focused_container = container
                break
        if focused_container is None:
            focused_container = self.child_containers[0]

        # Remove the splitter from layout
        self.layout.removeWidget(self.splitter)
        self.splitter.setParent(None)
        self.splitter = None

        # Clean up unfocused container and its cloned instance
        for c in self.child_containers:
            if c is not focused_container:
                if hasattr(c, "current_widget"):
                    self.cleanup_cloned_instance(c.current_widget)
                c.setParent(None)
        self.child_containers = []

        # Add the focused container's content as the new current_widget
        if focused_container.splitter is None:
            keep_widget = focused_container.current_widget
        else:
            keep_widget = focused_container

        self.current_widget = keep_widget
        self.layout.addWidget(keep_widget)
        keep_widget.show()

    def replace_with_widget(self, widget):
        """Replace current editor with given widget (for internal use)."""
        self.layout.removeWidget(self.current_widget)
        self.current_widget.setParent(None)
        self.current_widget = widget
        self.layout.addWidget(self.current_widget)

    def get_all_editors(self, editors=None):
        if editors is None:
            editors = []
        if self.splitter:
            for container in self.child_containers:
                container.get_all_editors(editors)
        else:
            editors.append(self.current_widget)
        return editors

def add_splitting_actions(window, split_container):
    split_horiz = QAction("Split Horizontally", window)
    split_horiz.setShortcut("Ctrl+Alt+H")
    split_horiz.triggered.connect(lambda: split_current(split_container, Qt.Horizontal))
    window.addAction(split_horiz)

    split_vert = QAction("Split Vertically", window)
    split_vert.setShortcut("Ctrl+Alt+V")
    split_vert.triggered.connect(lambda: split_current(split_container, Qt.Vertical))
    window.addAction(split_vert)

    unsplit = QAction("Unsplit", window)
    unsplit.setShortcut("Ctrl+Alt+U")
    unsplit.triggered.connect(lambda: unsplit_current(split_container))
    window.addAction(unsplit)

def split_current(split_container, orientation):
    leaf = split_container.get_focused_leaf()
    if leaf is not None:
        return leaf.split(orientation)

def unsplit_current(split_container):
    leaf = split_container.get_focused_leaf()
    if leaf is not None:
        return leaf.unsplit()
