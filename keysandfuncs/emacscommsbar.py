"""
Minimal Emacs-style command registry used by the Minibar.

It reuses the same action handlers defined for the regular keybind system so
both features stay in sync without needing a second implementation.
"""

from typing import Callable, Dict

from .keybinds import ACTION_BLUEPRINTS


def _action_lookup() -> Dict[str, Callable]:
    lookup = {}
    for blueprint in ACTION_BLUEPRINTS:
        lookup[blueprint["id"]] = blueprint["handler"]
    return lookup


_HANDLERS = _action_lookup()


def _cmd(action_id: str, description: str):
    handler = _HANDLERS.get(action_id)

    def _runner(window):
        if handler and window is not None:
            handler(window)

    return {"description": description, "func": _runner}


emacs_commands = {
    "C-x C-f": _cmd("open_file", "Open file"),
    "C-x C-s": _cmd("save_file", "Save file"),
    "C-x C-n": _cmd("new_tab", "New tab"),
    "C-x C-b": _cmd("toggle_file_tree", "Toggle file tree"),
    "C-x b": _cmd("toggle_file_tree", "Toggle file tree"),
    "C-x k": _cmd("close_current_tab", "Close current tab"),
    "C-x 1": _cmd("toggle_tab_bar", "Toggle tab bar visibility"),
    "C-x 2": _cmd("split_editor", "Split editor"),
    "C-x 3": _cmd("split_editor", "Split editor"),
    "C-x 0": _cmd("close_current_tab", "Close current tab"),
    "C-x C-g": _cmd("open_code_explorer", "Enable code explorer"),
    "C-x m": _cmd("toggle_console", "Toggle console panel"),
    "C-x C-m": _cmd("toggle_console", "Toggle console panel"),
    "C-x C-d": _cmd("open_diagram", "Open diagram sketch"),
    "C-x C-l": _cmd("open_latex", "Open LaTeX editor"),
    "C-x C-p": _cmd("open_process_manager", "Open process manager"),
    "C-x C-t": _cmd("toggle_tab_bar", "Toggle tab bar"),
    "C-x C-e": _cmd("open_code_explorer", "Open code explorer"),
    "C-x C-r": _cmd("toggle_numberline", "Toggle number line"),
    "C-x C-m m": _cmd("toggle_minimap", "Toggle minimap"),
    "C-x C-space": _cmd("open_minibar", "Show minibar"),
}


__all__ = ["emacs_commands"]

