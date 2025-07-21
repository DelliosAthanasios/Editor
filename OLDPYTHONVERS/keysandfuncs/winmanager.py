# winmanager.py
"""
Window/Tab/Instance Manager for the Editor
Keeps track of tabs and split-screen instances (screen buffers).
Provides navigation and management utilities for integration with the main app.
"""

class WindowManager:
    def __init__(self):
        # Each instance is a split-screen editor (e.g., a QTabWidget or similar)
        self.instances = []  # List of editor instances (split screens)
        self.active_instance_index = 0

    def add_instance(self, instance):
        self.instances.append(instance)
        self.active_instance_index = len(self.instances) - 1

    def remove_instance(self, instance):
        if instance in self.instances:
            idx = self.instances.index(instance)
            self.instances.remove(instance)
            # Adjust active index
            if self.active_instance_index >= len(self.instances):
                self.active_instance_index = max(0, len(self.instances) - 1)
            elif idx == self.active_instance_index:
                self.active_instance_index = 0

    def get_active_instance(self):
        if self.instances:
            return self.instances[self.active_instance_index]
        return None

    def set_active_instance(self, index):
        if 0 <= index < len(self.instances):
            self.active_instance_index = index

    def next_instance(self):
        if self.instances:
            self.active_instance_index = (self.active_instance_index + 1) % len(self.instances)
            return self.get_active_instance()
        return None

    def prev_instance(self):
        if self.instances:
            self.active_instance_index = (self.active_instance_index - 1) % len(self.instances)
            return self.get_active_instance()
        return None

    # Tab management within the active instance
    def get_tabs(self):
        instance = self.get_active_instance()
        if instance and hasattr(instance, 'count'):
            return [instance.widget(i) for i in range(instance.count())]
        return []

    def get_active_tab(self):
        instance = self.get_active_instance()
        if instance and hasattr(instance, 'currentWidget'):
            return instance.currentWidget()
        return None

    def switch_to_tab(self, tab_index):
        instance = self.get_active_instance()
        if instance and hasattr(instance, 'setCurrentIndex'):
            instance.setCurrentIndex(tab_index)

    def next_tab(self):
        instance = self.get_active_instance()
        if instance and hasattr(instance, 'currentIndex') and hasattr(instance, 'count'):
            idx = instance.currentIndex()
            count = instance.count()
            if count > 0:
                instance.setCurrentIndex((idx + 1) % count)

    def prev_tab(self):
        instance = self.get_active_instance()
        if instance and hasattr(instance, 'currentIndex') and hasattr(instance, 'count'):
            idx = instance.currentIndex()
            count = instance.count()
            if count > 0:
                instance.setCurrentIndex((idx - 1) % count)

# Singleton for global access
winmanager = WindowManager() 