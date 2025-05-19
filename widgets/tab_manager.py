import tkinter as tk
from tkinter import ttk

class TabManager(ttk.Notebook):
    def __init__(self, master, on_close_tab):
        super().__init__(master)
        self.on_close_tab = on_close_tab
        self.enable_traversal()

    def add_tab(self, frame, title="Untitled"):
        """Adds a frame as a new tab with a title."""
        self.add(frame, text=title)

    def current_tab(self):
        """Returns the currently selected tab frame."""
        tab_id = self.select()
        return self.nametowidget(tab_id) if tab_id else None

    def rename_tab(self, frame, title):
        """Renames a tab's title."""
        idx = self.index(frame)
        self.tab(idx, text=title)

    def tabs(self):
        """Returns a list of all open tab frames."""
        return [self.nametowidget(tab_id) for tab_id in self.tabs_id_list()]

    def tabs_id_list(self):
        """Returns a list of tab IDs (internal use)."""
        return super().tabs()

    def forget(self, index):
        """Closes the tab at the given index."""
        tab_list = self.tabs_id_list()
        if 0 <= index < len(tab_list):
            super().forget(tab_list[index])

    def open_new_window(self, app_class):
        """Opens a new window instance of the app."""
        new_win = tk.Toplevel()
        app_class(master=new_win)

