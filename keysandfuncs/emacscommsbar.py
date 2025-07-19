# Emacs-style command registry for the editor minibar

emacs_commands = {}

def emacs_command(name, description):
    def decorator(func):
        emacs_commands[name] = {"func": func, "description": description}
        return func
    return decorator

# --- Emacs-like commands (50 examples) ---

@emacs_command(":save", "Save the current file.")
def save(main_window):
    if main_window: main_window.save_file()

@emacs_command(":open", "Open a file.")
def open_file(main_window):
    if main_window: main_window.open_file()

@emacs_command(":close", "Close the current file.")
def close_file(main_window):
    if main_window: main_window.close_tab(main_window.get_active_tabwidget().currentIndex())

@emacs_command(":quit", "Quit the editor.")
def quit(main_window):
    if main_window: main_window.close()

@emacs_command(":undo", "Undo last change.")
def undo(main_window):
    if main_window: main_window.trigger_undo()

@emacs_command(":redo", "Redo last undone change.")
def redo(main_window):
    if main_window: main_window.trigger_redo()

@emacs_command(":cut", "Cut selected text.")
def cut(main_window):
    if main_window: main_window.get_active_tabwidget().cut()

@emacs_command(":copy", "Copy selected text.")
def copy(main_window):
    if main_window: main_window.get_active_tabwidget().copy()

@emacs_command(":paste", "Paste from clipboard.")
def paste(main_window):
    if main_window: main_window.get_active_tabwidget().paste()

@emacs_command(":select-all", "Select all text in the buffer.")
def select_all(main_window):
    if main_window: main_window.trigger_select_all()

@emacs_command(":find", "Find text in the buffer.")
def find(main_window):
    if main_window: main_window.open_search_dialog("find")

@emacs_command(":replace", "Replace text in the buffer.")
def replace(main_window):
    if main_window: main_window.open_search_dialog("replace")

@emacs_command(":goto-line", "Go to a specific line number.")
def goto_line(main_window):
    if main_window and hasattr(main_window, "trigger_goto_line"): main_window.trigger_goto_line()

@emacs_command(":kill-line", "Delete from cursor to end of line.")
def kill_line():
    pass

@emacs_command(":yank", "Paste last killed text (yank).")
def yank():
    pass

@emacs_command(":kill-region", "Delete selected region.")
def kill_region():
    pass

@emacs_command(":yank-pop", "Cycle through kill ring (yank-pop).")
def yank_pop():
    pass

@emacs_command(":move-beginning-of-line", "Move cursor to beginning of line.")
def move_beginning_of_line():
    pass

@emacs_command(":move-end-of-line", "Move cursor to end of line.")
def move_end_of_line():
    pass

@emacs_command(":forward-word", "Move cursor forward one word.")
def forward_word():
    pass

@emacs_command(":backward-word", "Move cursor backward one word.")
def backward_word():
    pass

@emacs_command(":next-line", "Move cursor to next line.")
def next_line():
    pass

@emacs_command(":previous-line", "Move cursor to previous line.")
def previous_line():
    pass

@emacs_command(":delete-char", "Delete character at cursor.")
def delete_char():
    pass

@emacs_command(":backward-delete-char", "Delete character before cursor.")
def backward_delete_char():
    pass

@emacs_command(":transpose-chars", "Transpose characters at cursor.")
def transpose_chars():
    pass

@emacs_command(":capitalize-word", "Capitalize word at cursor.")
def capitalize_word():
    pass

@emacs_command(":downcase-word", "Downcase word at cursor.")
def downcase_word():
    pass

@emacs_command(":upcase-word", "Upcase word at cursor.")
def upcase_word():
    pass

@emacs_command(":comment-line", "Comment or uncomment current line.")
def comment_line():
    pass

@emacs_command(":indent-region", "Indent selected region.")
def indent_region():
    pass

@emacs_command(":outdent-region", "Outdent selected region.")
def outdent_region():
    pass

@emacs_command(":split-window", "Split editor window.")
def split_window():
    pass

@emacs_command(":delete-window", "Delete current editor window.")
def delete_window():
    pass

@emacs_command(":switch-buffer", "Switch to another buffer.")
def switch_buffer():
    pass

@emacs_command(":list-buffers", "List all open buffers.")
def list_buffers():
    pass

@emacs_command(":revert-buffer", "Reload buffer from disk.")
def revert_buffer():
    pass

@emacs_command(":eval-buffer", "Evaluate buffer (for code files).")
def eval_buffer():
    pass

@emacs_command(":shell-command", "Run a shell command.")
def shell_command():
    pass

@emacs_command(":describe-key", "Show help for a keybinding.")
def describe_key():
    pass

@emacs_command(":describe-function", "Show help for a function.")
def describe_function():
    pass

@emacs_command(":set-mark", "Set the mark at cursor position.")
def set_mark():
    pass

@emacs_command(":exchange-point-and-mark", "Swap cursor and mark.")
def exchange_point_and_mark():
    pass

@emacs_command(":goto-char", "Go to a specific character position.")
def goto_char():
    pass

@emacs_command(":bookmark-set", "Set a bookmark at cursor.")
def bookmark_set():
    pass

@emacs_command(":bookmark-jump", "Jump to a bookmark.")
def bookmark_jump():
    pass

@emacs_command(":toggle-read-only", "Toggle read-only mode for buffer.")
def toggle_read_only():
    pass

@emacs_command(":open-recent", "Open a recently used file.")
def open_recent():
    pass

@emacs_command(":find-file-other-window", "Open file in another window.")
def find_file_other_window():
    pass

# Utility to get all commands and descriptions
def get_emacs_commands():
    return [(name, data["description"]) for name, data in emacs_commands.items()]
