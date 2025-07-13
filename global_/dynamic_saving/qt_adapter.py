from PyQt5.QtCore import QTimer
from .core import DynamicSaver

def enable_dynamic_saving_for_qt(main_window, save_interval_ms=2000):
    tabs = getattr(main_window, "tabs", None)
    if tabs is None:
        print("[DynamicSaving] No tabs attribute found on main_window.")
        return

    saver = DynamicSaver(save_interval_ms=save_interval_ms)
    save_timers = {}
    already_connected = set()

    def autosave_tab(editor_tab):
        editor = getattr(editor_tab, "editor", None)
        file_path = getattr(editor_tab, "_file_path", None)
        if editor is None or file_path is None:
            return
        text = editor.toPlainText()
        if not saver.should_save(editor_tab, text):
            return
        saver.save(editor_tab, file_path, text, on_error=lambda e: print(f"[DynamicSaving] Error auto-saving {file_path}: {e}"))

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

    for i in range(tabs.count()):
        tab = tabs.widget(i)
        connect_editor_tab(tab)

    def on_tab_changed(index):
        if index < 0:
            return
        tab = tabs.widget(index)
        connect_editor_tab(tab)
    tabs.currentChanged.connect(on_tab_changed)

    print("[DynamicSaving] Dynamic saving enabled for all editor tabs.") 