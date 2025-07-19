import json
import os
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence, QTextCursor
from .config import KEYBINDS_CONFIG_PATH, DEFAULT_KEYBINDS

KEYBIND_PROFILES_PATH = os.path.join(os.path.dirname(__file__), "keybind_profiles.json")

class KeybindManager(QObject):
    keybinds_changed = pyqtSignal(dict)
    profile_changed = pyqtSignal(str)
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.profiles = {}
        self.current_profile = "default"
        self.load_profiles()

    def load_profiles(self):
        if os.path.exists(KEYBIND_PROFILES_PATH):
            try:
                with open(KEYBIND_PROFILES_PATH, "r") as f:
                    self.profiles = json.load(f)
            except Exception:
                self.profiles = {"default": DEFAULT_KEYBINDS.copy()}
        else:
            self.profiles = {"default": DEFAULT_KEYBINDS.copy()}
        if self.current_profile not in self.profiles:
            self.current_profile = list(self.profiles.keys())[0]

    def save_profiles(self):
        with open(KEYBIND_PROFILES_PATH, "w") as f:
            json.dump(self.profiles, f, indent=2)

    def get_keybinds(self):
        return self.profiles.get(self.current_profile, DEFAULT_KEYBINDS.copy())

    def set_keybind(self, action, keys):
        if self.current_profile not in self.profiles:
            self.profiles[self.current_profile] = DEFAULT_KEYBINDS.copy()
        self.profiles[self.current_profile][action]["keys"] = keys
        self.save_profiles()
        self.keybinds_changed.emit(self.get_keybinds())

    def set_profile(self, profile):
        if profile in self.profiles:
            self.current_profile = profile
            self.keybinds_changed.emit(self.get_keybinds())
            self.profile_changed.emit(profile)

    def add_profile(self, name):
        if name not in self.profiles:
            self.profiles[name] = DEFAULT_KEYBINDS.copy()
            self.save_profiles()

    def delete_profile(self, name):
        if name in self.profiles and name != "default":
            del self.profiles[name]
            if self.current_profile == name:
                self.current_profile = "default"
            self.save_profiles()
            self.keybinds_changed.emit(self.get_keybinds())
            self.profile_changed.emit(self.current_profile)

    def reset_profile(self, name=None):
        if name is None:
            name = self.current_profile
        self.profiles[name] = DEFAULT_KEYBINDS.copy()
        self.save_profiles()
        self.keybinds_changed.emit(self.get_keybinds())

    def validate_keybinds(self, keybinds):
        seen = {}
        for action, info in keybinds.items():
            keys = info.get("keys", "").strip()
            if not keys:
                return False, f"Keybind for '{action}' is empty."
            # Split multi-step sequences
            steps = [s.strip() for s in keys.split(',') if s.strip()]
            # Prevent duplicate consecutive steps in a sequence
            for i in range(1, len(steps)):
                if steps[i] == steps[i-1]:
                    return False, f"Duplicate consecutive step '{steps[i]}' in keybind for '{action}'."
            # Check for duplicate full sequences
            seq_tuple = tuple(steps)
            if seq_tuple in seen:
                other_action = seen[seq_tuple]
                return False, f"Duplicate keybind sequence: '{', '.join(steps)}' for '{action}' and '{other_action}'"
            seen[seq_tuple] = action
        return True, ""

keybind_manager = KeybindManager()

# --- Config IO ---
def load_keybinds():
    import os
    if os.path.exists(KEYBINDS_CONFIG_PATH):
        try:
            with open(KEYBINDS_CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_KEYBINDS.copy()

def save_keybinds(keybinds):
    try:
        with open(KEYBINDS_CONFIG_PATH, "w") as f:
            json.dump(keybinds, f, indent=2)
    except Exception as e:
        print("Failed to save keybinds:", e)

# --- Editor Action Helpers for Emacs-like navigation ---
def get_current_editor(main_window):
    tabs = getattr(main_window, "tabs", None)
    if not tabs:
        return None
    widget = tabs.currentWidget()
    if widget and hasattr(widget, "editor"):
        return widget.editor
    return None

def emacs_go_start_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine)
        editor.setTextCursor(cursor)

def emacs_go_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine)
        editor.setTextCursor(cursor)

def emacs_go_next_word(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.NextWord)
        editor.setTextCursor(cursor)

def emacs_go_prev_word(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.PreviousWord)
        editor.setTextCursor(cursor)

def emacs_go_up_one_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Up)
        editor.setTextCursor(cursor)

def emacs_go_down_one_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Down)
        editor.setTextCursor(cursor)

def emacs_forward_char(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Right)
        editor.setTextCursor(cursor)

def emacs_backward_char(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Left)
        editor.setTextCursor(cursor)

def emacs_go_start_of_doc(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.Start)
        editor.setTextCursor(cursor)

def emacs_go_end_of_doc(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor.setTextCursor(cursor)

def emacs_delete_to_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        editor.setTextCursor(cursor)

def emacs_transpose_chars(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        pos = cursor.position()
        if pos == 0:
            return
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        left_char = cursor.selectedText()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        right_char = cursor.selectedText()
        if left_char and right_char:
            cursor.insertText(right_char + left_char)
            cursor.movePosition(QTextCursor.Left)
            editor.setTextCursor(cursor)

def emacs_set_mark(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.clearSelection()
        editor.setTextCursor(cursor)

def emacs_select_to_end_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

def emacs_select_to_start_of_line(main_window):
    editor = get_current_editor(main_window)
    if editor:
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

# -- Integration Helper Functions --
def apply_keybinds_to_editor(main_window, keybinds):
    tabwidget = main_window.tabs
    if not hasattr(main_window, "_keybind_shortcuts"):
        main_window._keybind_shortcuts = []
    for sc in main_window._keybind_shortcuts:
        sc.setParent(None)
    main_window._keybind_shortcuts = []
    action_map = {
        "Undo": main_window.trigger_undo,
        "Redo": main_window.trigger_redo,
        "Select All": main_window.trigger_select_all,
        "Search": lambda: main_window.trigger_search() if hasattr(main_window, "trigger_search") else None,
        "Replace": lambda: main_window.trigger_replace() if hasattr(main_window, "trigger_replace") else None,
        "Go to Line": lambda: main_window.trigger_goto_line() if hasattr(main_window, "trigger_goto_line") else None,
        "Go to Word": lambda: main_window.trigger_goto_word() if hasattr(main_window, "trigger_goto_word") else None,
        "Save File": main_window.save_file,
        "Open File": main_window.open_file,
        "New File": main_window.new_file,
        "Close Tab": lambda: main_window.close_tab(tabwidget.currentIndex()),
        "Duplicate File": main_window.duplicate_file,
        "Toggle Minimap": main_window.toggle_minimap,
        "Toggle Number Line": main_window.view_toggle_numberline,
        "Toggle File Tree": main_window.toggle_file_tree,
        # --- Emacs-like navigation ---
        "Go to Start of Line": lambda: emacs_go_start_of_line(main_window),
        "Go to End of Line": lambda: emacs_go_end_of_line(main_window),
        "Go to Next Word": lambda: emacs_go_next_word(main_window),
        "Go to Previous Word": lambda: emacs_go_prev_word(main_window),
        "Go Up One Line": lambda: emacs_go_up_one_line(main_window),
        "Go Down One Line": lambda: emacs_go_down_one_line(main_window),
        "Go Forward One Char": lambda: emacs_forward_char(main_window),
        "Go Backward One Char": lambda: emacs_backward_char(main_window),
        "Go to Start of Document": lambda: emacs_go_start_of_doc(main_window),
        "Go to End of Document": lambda: emacs_go_end_of_doc(main_window),
        "Delete Current Line": lambda: emacs_delete_to_end_of_line(main_window),
        "Transpose Characters": lambda: emacs_transpose_chars(main_window),
        "Set Mark": lambda: emacs_set_mark(main_window),
        "Select to End of Line": lambda: emacs_select_to_end_of_line(main_window),
        "Select to Start of Line": lambda: emacs_select_to_start_of_line(main_window),
    }
    for action, info in keybinds.items():
        keys = info["keys"]
        func = action_map.get(action)
        if not keys or not func:
            continue
        try:
            shortcut = QShortcut(QKeySequence(keys), main_window)
            shortcut.activated.connect(func)
            main_window._keybind_shortcuts.append(shortcut)
        except Exception as e:
            print(f"Error binding shortcut for {action}: {e}") 