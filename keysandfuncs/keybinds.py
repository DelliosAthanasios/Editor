import atexit
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional, Sequence
import weakref

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QMessageBox, QShortcut

from .keybind_editor import KeybindEditorWidget


# ---------------------------------------------------------------------------#
# Paths & persistence helpers
# ---------------------------------------------------------------------------#
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_KEYBINDS_PATH = os.path.join(_BASE_DIR, "user_keybinds.json")
_SESSION_LOG_PATH = os.path.join(_BASE_DIR, "keybinsses.log")


def _ensure_directory(path: str):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


class SessionKeybindLogger:
    """Writes every triggered keybind to a log that is cleared on exit."""

    def __init__(self, log_path: str):
        self._path = log_path
        self._attached = False
        _ensure_directory(log_path)
        with open(self._path, "w", encoding="utf-8") as handle:
            handle.write("")
        atexit.register(self.cleanup)

    @property
    def path(self) -> str:
        return self._path

    def attach_to_app(self):
        if self._attached:
            return
        app = QApplication.instance()
        if app:
            app.aboutToQuit.connect(self.cleanup)
            self._attached = True

    def log(self, sequence: str, action_ids: Sequence[str]):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {sequence} -> {', '.join(action_ids)}\n"
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line)

    def cleanup(self):
        try:
            if os.path.exists(self._path):
                os.remove(self._path)
        except OSError:
            pass


SESSION_LOGGER = SessionKeybindLogger(_SESSION_LOG_PATH)


# ---------------------------------------------------------------------------#
# Action definitions
# ---------------------------------------------------------------------------#


def _safe_call(callable_: Callable, *args, **kwargs):
    try:
        callable_(*args, **kwargs)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"[Keybinds] failed to execute action: {exc}")


def _close_active_tab(window):
    tab_widget = window.get_active_tabwidget()
    if tab_widget is None:
        return
    index = tab_widget.currentIndex()
    if index >= 0:
        window.close_tab(index)


def _open_search(window, mode: str):
    window.open_search_dialog(mode)


def _toggle_tab_bar(window):
    window.toggle_tab_bar_button()


def _combined_toggle(window):
    window.view_toggle_numberline()
    window.toggle_minimap()


def _cycle_windows(window, direction=1):
    windows = [ref for ref in _WINDOW_MANAGERS.keys() if hasattr(ref, "activateWindow")]
    if len(windows) <= 1 or window not in windows:
        return
    idx = windows.index(window)
    target = windows[(idx + direction) % len(windows)]
    target.show()
    target.raise_()
    target.activateWindow()
    target.setFocus()


def _cycle_tabs(window, direction=1):
    tab_widget = window.get_active_tabwidget()
    if not tab_widget or tab_widget.count() <= 1:
        return
    current = tab_widget.currentIndex()
    tab_widget.setCurrentIndex((current + direction) % tab_widget.count())


def _get_current_text_editor(window):
    """Helper to get the QTextEdit widget from the active tab."""
    tab_widget = window.get_active_tabwidget()
    if not tab_widget:
        return None
    current_tab = tab_widget.currentWidget()
    if not current_tab:
        return None
    if hasattr(current_tab, "editor"):
        return current_tab.editor
    return None


def _toggle_vim_mode(window):
    """Toggle Vim mode for the current editor."""
    from .viman import VIM_MODE
    editor = _get_current_text_editor(window)
    if editor:
        VIM_MODE.activate(editor)


def _toggle_emacs_mode(window):
    """Toggle Emacs mode for the current editor."""
    from .eman import EMACS_MODE
    editor = _get_current_text_editor(window)
    if editor:
        EMACS_MODE.activate(editor)


ACTION_BLUEPRINTS = [
    {
        "id": "toggle_file_tree",
        "title": "Toggle File Tree",
        "description": "Show or hide the project tree",
        "handler": lambda win: win.toggle_file_tree(),
    },
    {
        "id": "toggle_numberline",
        "title": "Toggle Number Line",
        "description": "Show or hide gutter line numbers",
        "handler": lambda win: win.view_toggle_numberline(),
    },
    {
        "id": "rotate_numberline",
        "title": "Rotate Number Line",
        "description": "Move number line to the other side",
        "handler": lambda win: win.rotate_number_line(),
    },
    {
        "id": "toggle_minimap",
        "title": "Toggle Minimap",
        "description": "Show or hide the minimap",
        "handler": lambda win: win.toggle_minimap(),
    },
    {
        "id": "toggle_console",
        "title": "Toggle Console",
        "description": "Show or hide the console panel",
        "handler": lambda win: win.toggle_console(),
    },
    {
        "id": "new_file",
        "title": "New File",
        "description": "Create a new file",
        "handler": lambda win: win.new_file(),
    },
    {
        "id": "open_file",
        "title": "Open File",
        "description": "Open a file from disk",
        "handler": lambda win: win.open_file(),
    },
    {
        "id": "save_file",
        "title": "Save File",
        "description": "Save the active file",
        "handler": lambda win: win.save_file(),
    },
    {
        "id": "new_tab",
        "title": "New Tab",
        "description": "Open a blank editor tab",
        "handler": lambda win: win.add_new_tab(),
    },
    {
        "id": "open_file_explorer_tab",
        "title": "Open File Explorer Tab",
        "description": "Add file explorer as a tab",
        "handler": lambda win: win.add_file_explorer_tab(),
    },
    {
        "id": "close_current_tab",
        "title": "Close Current Tab",
        "description": "Close the current editor tab",
        "handler": _close_active_tab,
    },
    {
        "id": "search_find",
        "title": "Find",
        "description": "Open the find dialog",
        "handler": lambda win: _open_search(win, "find"),
    },
    {
        "id": "search_replace",
        "title": "Find and Replace",
        "description": "Open the find-and-replace dialog",
        "handler": lambda win: _open_search(win, "replace"),
    },
    {
        "id": "open_code_explorer",
        "title": "Enable Code Explorer",
        "description": "Analyze current file with code explorer",
        "handler": lambda win: win.enable_code_explorer(),
    },
    {
        "id": "open_minibar",
        "title": "Open Minibar",
        "description": "Show the command minibar",
        "handler": lambda win: win.show_minibar(),
    },
    {
        "id": "split_editor",
        "title": "Split Editor",
        "description": "Split the editor area",
        "handler": lambda win: win.handle_split_action(),
    },
    {
        "id": "open_process_manager",
        "title": "Process Manager",
        "description": "Open the process manager tab",
        "handler": lambda win: win.open_process_manager(),
    },
    {
        "id": "open_music_player",
        "title": "Music Player",
        "description": "Open music player tab",
        "handler": lambda win: win.open_music_player(),
    },
    {
        "id": "open_pdf_dialog",
        "title": "Open PDF",
        "description": "Open file dialog for PDFs",
        "handler": lambda win: win.open_pdf_file(),
    },
    {
        "id": "open_image_dialog",
        "title": "Open Image",
        "description": "Open file dialog for images",
        "handler": lambda win: win.open_image_file(),
    },
    {
        "id": "open_diagram",
        "title": "Diagramm Sketch",
        "description": "Open the diagram sketch tab",
        "handler": lambda win: win.open_diagramm_sketch(),
    },
    {
        "id": "open_latex",
        "title": "LaTeX Editor",
        "description": "Open a LaTeX editor tab",
        "handler": lambda win: win.open_latex_editor(),
    },
    {
        "id": "toggle_tab_bar",
        "title": "Toggle Tab Bar",
        "description": "Hide or show the editor tab bar",
        "handler": _toggle_tab_bar,
    },
    {
        "id": "numberline_minimap_combo",
        "title": "Toggle Number Line + Minimap",
        "description": "Toggle both gutter and minimap together",
        "handler": _combined_toggle,
    },
    {
        "id": "cycle_windows_forward",
        "title": "Next Window",
        "description": "Activate the next editor window",
        "handler": lambda win: _cycle_windows(win, direction=1),
    },
    {
        "id": "cycle_windows_backward",
        "title": "Previous Window",
        "description": "Activate the previous editor window",
        "handler": lambda win: _cycle_windows(win, direction=-1),
    },
    {
        "id": "cycle_tabs_forward",
        "title": "Next Tab",
        "description": "Switch to the next tab",
        "handler": lambda win: _cycle_tabs(win, direction=1),
    },
    {
        "id": "cycle_tabs_backward",
        "title": "Previous Tab",
        "description": "Switch to the previous tab",
        "handler": lambda win: _cycle_tabs(win, direction=-1),
    },
    {
        "id": "toggle_vim_mode",
        "title": "Toggle Vim Mode",
        "description": "Activate/deactivate Vim text manipulation mode",
        "handler": _toggle_vim_mode,
    },
    {
        "id": "toggle_emacs_mode",
        "title": "Toggle Emacs Mode",
        "description": "Activate/deactivate Emacs text manipulation mode",
        "handler": _toggle_emacs_mode,
    },
]


DEFAULT_BINDINGS: Dict[str, List[str]] = {
    "Ctrl+B": ["toggle_file_tree"],
    "Ctrl+Shift+M": ["toggle_minimap"],
    "Ctrl+Alt+M": ["numberline_minimap_combo"],
    "Ctrl+Shift+L": ["toggle_numberline"],
    "Ctrl+Shift+R": ["rotate_numberline"],
    "Ctrl+Alt+C": ["toggle_console"],
    "Ctrl+N": ["new_file"],
    "Ctrl+O": ["open_file"],
    "Ctrl+S": ["save_file"],
    "Ctrl+T": ["new_tab"],
    "Ctrl+Shift+E": ["open_file_explorer_tab"],
    "Ctrl+W": ["close_current_tab"],
    "Ctrl+F": ["search_find"],
    "Ctrl+H": ["search_replace"],
    "Ctrl+E": ["open_code_explorer"],
    "Ctrl+Space": ["open_minibar"],
    "Ctrl+Alt+S": ["split_editor"],
    "Ctrl+Alt+P": ["open_process_manager"],
    "Ctrl+Alt+L": ["open_latex"],
    "Ctrl+Alt+D": ["open_diagram"],
    "Ctrl+Alt+I": ["open_image_dialog"],
    "Ctrl+Alt+F": ["open_pdf_dialog"],
    "Ctrl+Alt+T": ["toggle_tab_bar"],
    "Ctrl+Alt+G": ["open_music_player"],
    "Ctrl+PageDown": ["cycle_tabs_forward"],
    "Ctrl+PageUp": ["cycle_tabs_backward"],
    "Ctrl+Alt+Tab": ["cycle_windows_forward"],
    "Ctrl+Alt+Shift+Tab": ["cycle_windows_backward"],
    "Ctrl+Shift+V": ["toggle_vim_mode"],
    "Ctrl+Alt+E": ["toggle_emacs_mode"],
    "Escape": ["toggle_vim_mode"],
}


# ---------------------------------------------------------------------------#
# Keybind manager
# ---------------------------------------------------------------------------#


@dataclass
class ActionEntry:
    action_id: str
    title: str
    description: str
    handler: Callable


class KeybindManager:
    """Owns runtime keybinds for a TextEditor instance."""

    def __init__(self, window):
        self.window = window
        self._shortcuts: List[QShortcut] = []
        self._shortcut_info: List = []  # (shortcut, sequence, action_ids) tuples
        self._actions: Dict[str, ActionEntry] = self._build_action_map()
        self._bindings: Dict[str, List[str]] = self._load_bindings()
        SESSION_LOGGER.attach_to_app()
        self._install_shortcuts()

    # ---------------------- bindings persistence ---------------------------#
    def _load_bindings(self) -> Dict[str, List[str]]:
        if os.path.exists(_USER_KEYBINDS_PATH):
            try:
                with open(_USER_KEYBINDS_PATH, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                bindings = data.get("bindings", {})
                if isinstance(bindings, dict):
                    return {k: list(v) for k, v in bindings.items()}
            except Exception:
                pass
        return dict(DEFAULT_BINDINGS)

    def _save_bindings(self):
        payload = {"bindings": self._bindings}
        with open(_USER_KEYBINDS_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    # ---------------------- action helpers --------------------------------#
    def _build_action_map(self) -> Dict[str, ActionEntry]:
        action_map = {}
        for blueprint in ACTION_BLUEPRINTS:
            action_map[blueprint["id"]] = ActionEntry(
                action_id=blueprint["id"],
                title=blueprint["title"],
                description=blueprint["description"],
                handler=lambda win=self.window, handler=blueprint["handler"]: handler(win),
            )
        return action_map

    def available_actions(self) -> List[dict]:
        return [
            {"id": entry.action_id, "title": entry.title, "description": entry.description}
            for entry in self._actions.values()
        ]

    # ---------------------- shortcut management ---------------------------#
    def _install_shortcuts(self):
        self._clear_shortcuts()
        self._shortcut_info = []  # List of (shortcut, sequence, action_ids) tuples
        for sequence, action_ids in self._bindings.items():
            if not sequence.strip():
                continue
            shortcut = QShortcut(QKeySequence(sequence), self.window)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(
                lambda seq=sequence, ids=list(action_ids): self._execute_binding(seq, ids)
            )
            self._shortcuts.append(shortcut)
            self._shortcut_info.append((shortcut, sequence, action_ids))

    def _clear_shortcuts(self):
        for shortcut in self._shortcuts:
            try:
                shortcut.activated.disconnect()
            except TypeError:
                pass
            shortcut.setParent(None)
        self._shortcuts.clear()
        self._shortcut_info.clear()
    
    def set_shortcuts_enabled(self, enabled: bool, allow_mode_toggles: bool = False):
        """Enable or disable shortcuts. If allow_mode_toggles=True, keep mode toggle shortcuts enabled."""
        allowed_actions = {"toggle_vim_mode", "toggle_emacs_mode", "open_minibar"} if allow_mode_toggles else set()
        
        for shortcut, sequence, action_ids in self._shortcut_info:
            # Keep enabled if it's a mode toggle and we're allowing them
            if allow_mode_toggles and any(aid in allowed_actions for aid in action_ids):
                shortcut.setEnabled(True)
            else:
                shortcut.setEnabled(enabled)

    def _execute_binding(self, sequence: str, action_ids: Sequence[str]):
        # Check if vim or emacs mode is active - block normal keybinds if so
        editor = _get_current_text_editor(self.window)
        if editor:
            mode = self._get_current_mode(editor)
            if mode in ("vim", "emacs"):
                # Only allow mode toggles and special commands in modal modes
                allowed_actions = {
                    "toggle_vim_mode",
                    "toggle_emacs_mode",
                    "open_minibar",
                }
                # Filter out actions that aren't allowed in modal mode
                filtered_ids = [aid for aid in action_ids if aid in allowed_actions]
                if not filtered_ids:
                    # Block this keybind - modal mode is active
                    return
                action_ids = filtered_ids
        
        executed = []
        for action_id in action_ids:
            action = self._actions.get(action_id)
            if not action:
                continue
            _safe_call(action.handler)
            executed.append(action_id)
        if executed:
            SESSION_LOGGER.log(sequence, executed)
    
    def update_shortcut_state(self):
        """Update shortcut enabled state based on current mode."""
        editor = _get_current_text_editor(self.window)
        if editor:
            mode = self._get_current_mode(editor)
            # Disable shortcuts when in modal mode, but keep mode toggles enabled
            if mode in ("vim", "emacs"):
                self.set_shortcuts_enabled(False, allow_mode_toggles=True)
            else:
                self.set_shortcuts_enabled(True)
        else:
            self.set_shortcuts_enabled(True)
    
    def _get_current_mode(self, editor) -> str:
        """Get the current editing mode for an editor."""
        try:
            from .viman import is_vim_mode_active
            if is_vim_mode_active(editor):
                return "vim"
        except Exception:
            pass
        
        try:
            from .eman import is_emacs_mode_active
            if is_emacs_mode_active(editor):
                return "emacs"
        except Exception:
            pass
        
        return "normal"

    # ---------------------- external API ----------------------------------#
    @property
    def bindings(self) -> Dict[str, List[str]]:
        return dict(self._bindings)

    def update_bindings(self, bindings: Dict[str, List[str]]):
        self._bindings = {k: list(v) for k, v in bindings.items()}
        self._install_shortcuts()
        self._save_bindings()

    def reset_to_defaults(self):
        self.update_bindings(dict(DEFAULT_BINDINGS))


# Track managers per window, avoid recreating duplicates.
_WINDOW_MANAGERS: "weakref.WeakKeyDictionary[object, KeybindManager]" = weakref.WeakKeyDictionary()


def _manager_for(window) -> KeybindManager:
    manager = _WINDOW_MANAGERS.get(window)
    if manager is None:
        manager = KeybindManager(window)
        _WINDOW_MANAGERS[window] = manager
    return manager


# ---------------------------------------------------------------------------#
# Public helpers wired into main.py
# ---------------------------------------------------------------------------#


def show_default_keybinds(window):
    lines = [f"{seq}  →  {', '.join(actions)}" for seq, actions in sorted(DEFAULT_BINDINGS.items())]
    QMessageBox.information(window, "Default Keybinds", "\n".join(lines))


def configure_keybinds(window):
    manager = _manager_for(window)
    tab_widget = window.get_active_tabwidget()
    if tab_widget is None:
        QMessageBox.warning(window, "Keybind Editor", "No active tab widget available.")
        return

    # Prevent duplicate editor tabs
    for idx in range(tab_widget.count()):
        widget = tab_widget.widget(idx)
        if isinstance(widget, KeybindEditorWidget):
            tab_widget.setCurrentIndex(idx)
            return

    editor_widget = KeybindEditorWidget(
        parent=tab_widget,
        bindings=manager.bindings,
        actions=manager.available_actions(),
    )

    def close_tab():
        index = tab_widget.indexOf(editor_widget)
        if index >= 0:
            tab_widget.removeTab(index)

    editor_widget.bindingsSaved.connect(lambda bindings: (manager.update_bindings(bindings), close_tab()))
    editor_widget.requestClose.connect(close_tab)

    index = tab_widget.addTab(editor_widget, "Keybind Editor")
    tab_widget.setCurrentIndex(index)


def integrate_keybinds_menu(window):
    """Attach keybind actions to the existing “Keybinds” menu."""
    manager = _manager_for(window)

    menu_bar = window.menuBar()
    keybind_menu = _find_menu(menu_bar, "Keybinds")
    if keybind_menu is None:
        keybind_menu = menu_bar.addMenu("Keybinds")
    else:
        keybind_menu.clear()

    configure_action = QAction("Configure Keybinds…", window)
    configure_action.triggered.connect(lambda: configure_keybinds(window))
    keybind_menu.addAction(configure_action)

    defaults_action = QAction("Show Default Keybinds", window)
    defaults_action.triggered.connect(lambda: show_default_keybinds(window))
    keybind_menu.addAction(defaults_action)

    reset_action = QAction("Reset to Defaults", window)
    reset_action.triggered.connect(manager.reset_to_defaults)
    keybind_menu.addAction(reset_action)

    log_action = QAction("Open Current Log", window)
    log_action.triggered.connect(lambda: _open_log_file(window))
    keybind_menu.addAction(log_action)
    
    keybind_menu.addSeparator()
    
    dict_action = QAction("Command Dictionary", window)
    dict_action.triggered.connect(lambda: _show_command_dictionary(window))
    keybind_menu.addAction(dict_action)

    # Ensure shortcuts stay alive for window lifetime.
    _WINDOW_MANAGERS[window] = manager


def _show_command_dictionary(window):
    """Show command dictionary as a tab."""
    from .command_dictionary import show_command_dictionary
    show_command_dictionary(window)


def _find_menu(menu_bar, title: str) -> Optional[QMenu]:
    for action in menu_bar.actions():
        menu = action.menu()
        if menu and menu.title().lower() == title.lower():
            return menu
    return None


def _open_log_file(window):
    if not os.path.exists(SESSION_LOGGER.path):
        QMessageBox.information(window, "Keybind Log", "No keybinds have been triggered yet.")
        return
    try:
        with open(SESSION_LOGGER.path, "r", encoding="utf-8") as handle:
            content = handle.read().strip() or "No entries yet."
        QMessageBox.information(window, "Keybind Log (Session)", content)
    except Exception as exc:
        QMessageBox.critical(window, "Keybind Log Error", str(exc))

