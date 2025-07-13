"""
Task Manager Module for Third Edit
Provides system monitoring and process management capabilities
"""

from .task_manager_widget import TaskManagerWidget

def create_task_manager_tab(parent=None):
    """Create and return a task manager tab widget"""
    return TaskManagerWidget(parent)

__all__ = ['create_task_manager_tab', 'TaskManagerWidget'] 