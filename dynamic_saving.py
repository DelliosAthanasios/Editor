import sys
import os
from PyQt5.QtCore import QTimer

def enable_dynamic_saving(main_window, save_interval_ms=2000):
    """
    Enables dynamic (auto) saving of all editor tabs in the provided main_window.
    :param main_window: The main TextEditor window instance.
    :param save_interval_ms: Minimum interval (in ms) between saves for each tab.
    """
    tabs = getattr(main_window, "tabs", None)
    if tabs is None:
        print("[DynamicSaving] No tabs attribute found on main_window.")
        return

    # Dictionary to store last saved content per tab to avoid unnecessary writes
    last_saved_text = {}

    # Timer-based debounce for each tab to avoid saving on every keystroke
    save_timers = {}

    # Keep track of already-connected tabs to avoid double-connecting
    already_connected = set()

    def autosave_tab(editor_tab):
        editor = getattr(editor_tab, "editor", None)
        file_path = getattr(editor_tab, "_file_path", None)
        if editor is None or file_path is None:
            return

        text = editor.toPlainText()
        if last_saved_text.get(editor_tab) == text:
            return  # No changes since last save
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            last_saved_text[editor_tab] = text
            # print(f"[DynamicSaving] Auto-saved: {file_path}")
        except Exception as e:
            print(f"[DynamicSaving] Error auto-saving {file_path}:", e)

    def schedule_autosave(editor_tab):
        if editor_tab in save_timers:
            save_timers[editor_tab].stop()
        else:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda tab=editor_tab: autosave_tab(tab))
            save_timers[editor_tab] = timer
        save_timers[editor_tab].start(save_interval_ms)

    def connect_editor_tab(editor_tab):
        if editor_tab in already_connected:
            return
        editor = getattr(editor_tab, "editor", None)
        if editor is None:
            return
        editor.textChanged.connect(lambda et=editor_tab: schedule_autosave(et))
        already_connected.add(editor_tab)

    # Connect signal for all existing editor tabs
    for i in range(tabs.count()):
        tab = tabs.widget(i)
        connect_editor_tab(tab)

    # Connect to tab change to handle new tabs
    def on_tab_changed(index):
        if index < 0:
            return
        tab = tabs.widget(index)
        connect_editor_tab(tab)
    tabs.currentChanged.connect(on_tab_changed)

    print("[DynamicSaving] Dynamic saving enabled for all editor tabs.")

# --- If running as script, try to hook into an existing QApplication ---

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        print("[DynamicSaving] Please run this after the main application is started.")
        sys.exit(1)

    # Try to find the main window
    main_window = None
    for widget in app.topLevelWidgets():
        if widget.objectName() == "MainWindow" or widget.windowTitle() == "Third Edit":
            main_window = widget
            break
    if main_window is None:
        print("[DynamicSaving] Could not find main window. Please provide it explicitly.")
        sys.exit(1)

    enable_dynamic_saving(main_window)