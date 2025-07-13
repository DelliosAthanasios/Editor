"""
Task Manager Module for Third Edit
Provides system monitoring and process management capabilities
"""

def create_task_manager_tab(parent=None):
    """Create and return a task manager tab widget with proper fallback"""
    try:
        # Try to use the ultra-fast version first
        from .fast_ui_components import FastTaskManagerWidget
        return FastTaskManagerWidget(parent)
    except Exception as e:
        print(f"Fast task manager failed: {e}")
        try:
            # Fallback to the standard version
            from .task_manager_widget import TaskManagerWidget
            return TaskManagerWidget(parent)
        except Exception as e2:
            print(f"Standard task manager failed: {e2}")
            # Final fallback to legacy version
            try:
                from .legacy_task_manager import TaskManagerWidget
                return TaskManagerWidget(parent)
            except Exception as e3:
                print(f"Legacy task manager failed: {e3}")
                # Create a simple error widget
                from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
                error_widget = QWidget(parent)
                layout = QVBoxLayout(error_widget)
                error_label = QLabel("Task Manager is not available.\nPlease install psutil: pip install psutil")
                error_label.setStyleSheet("color: red; font-size: 14px;")
                layout.addWidget(error_label)
                return error_widget

def create_standard_task_manager_tab(parent=None):
    """Create and return the standard task manager tab widget"""
    from .task_manager_widget import TaskManagerWidget
    return TaskManagerWidget(parent)

def create_fast_task_manager_tab(parent=None):
    """Create and return the ultra-fast task manager tab widget"""
    from .fast_ui_components import FastTaskManagerWidget
    return FastTaskManagerWidget(parent)

__all__ = [
    'create_task_manager_tab', 
    'create_standard_task_manager_tab',
    'create_fast_task_manager_tab'
] 