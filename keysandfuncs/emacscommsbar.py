# Emacs-style command registry for the editor minibar, using real Emacs keybindings and categories

emacs_commands = {}

def emacs_command(name, description):
    def decorator(func):
        emacs_commands[name] = {"func": func, "description": description}
        return func
    return decorator

# --- File & Buffer Management ---
@emacs_command("C-x C-f", "Open file (find-file)")
def find_file(main_window):
    if main_window: main_window.open_file()

@emacs_command("C-x C-s", "Save current buffer")
def save_buffer(main_window):
    if main_window: main_window.save_file()

@emacs_command("C-x C-w", "Save buffer to a different file (write-file)")
def write_file(main_window):
    if main_window and hasattr(main_window, 'save_file_as'): main_window.save_file_as()

@emacs_command("C-x b", "Switch to buffer")
def switch_to_buffer(main_window):
    if main_window and hasattr(main_window, 'switch_buffer'): main_window.switch_buffer()

@emacs_command("C-x C-b", "List all buffers")
def list_buffers(main_window):
    if main_window and hasattr(main_window, 'list_buffers'): main_window.list_buffers()

@emacs_command("C-x k", "Kill (close) buffer")
def kill_buffer(main_window):
    if main_window: main_window.close_tab(main_window.get_active_tabwidget().currentIndex())

@emacs_command("C-x C-c", "Quit Emacs")
def quit_emacs(main_window):
    if main_window: main_window.close()

@emacs_command("C-x C-v", "Open a new file, replacing current buffer")
def visit_new_file(main_window):
    if main_window and hasattr(main_window, 'visit_new_file'): main_window.visit_new_file()

# --- Navigation ---
@emacs_command("C-a", "Move to beginning of line")
def move_beginning_of_line(main_window):
    if main_window and hasattr(main_window, 'move_cursor_line_start'): main_window.move_cursor_line_start()

@emacs_command("C-e", "Move to end of line")
def move_end_of_line(main_window):
    if main_window and hasattr(main_window, 'move_cursor_line_end'): main_window.move_cursor_line_end()

@emacs_command("M-<", "Move to beginning of buffer")
def move_beginning_of_buffer(main_window):
    if main_window and hasattr(main_window, 'move_cursor_buffer_start'): main_window.move_cursor_buffer_start()

@emacs_command("M->", "Move to end of buffer")
def move_end_of_buffer(main_window):
    if main_window and hasattr(main_window, 'move_cursor_buffer_end'): main_window.move_cursor_buffer_end()

@emacs_command("C-n", "Next line")
def next_line(main_window):
    if main_window and hasattr(main_window, 'move_cursor_down'): main_window.move_cursor_down()

@emacs_command("C-p", "Previous line")
def previous_line(main_window):
    if main_window and hasattr(main_window, 'move_cursor_up'): main_window.move_cursor_up()

@emacs_command("C-f", "Forward character")
def forward_char(main_window):
    if main_window and hasattr(main_window, 'move_cursor_right'): main_window.move_cursor_right()

@emacs_command("C-b", "Backward character")
def backward_char(main_window):
    if main_window and hasattr(main_window, 'move_cursor_left'): main_window.move_cursor_left()

@emacs_command("M-f", "Forward word")
def forward_word(main_window):
    if main_window and hasattr(main_window, 'move_cursor_word_right'): main_window.move_cursor_word_right()

@emacs_command("M-b", "Backward word")
def backward_word(main_window):
    if main_window and hasattr(main_window, 'move_cursor_word_left'): main_window.move_cursor_word_left()

@emacs_command("C-v", "Page down")
def page_down(main_window):
    if main_window and hasattr(main_window, 'page_down'): main_window.page_down()

@emacs_command("M-v", "Page up")
def page_up(main_window):
    if main_window and hasattr(main_window, 'page_up'): main_window.page_up()

@emacs_command("C-l", "Center screen on current line")
def recenter(main_window):
    if main_window and hasattr(main_window, 'recenter'): main_window.recenter()

# --- Editing Text ---
@emacs_command("C-d", "Delete character under cursor")
def delete_char(main_window):
    if main_window and hasattr(main_window, 'delete_char'): main_window.delete_char()

@emacs_command("M-d", "Delete word forward")
def delete_word_forward(main_window):
    if main_window and hasattr(main_window, 'delete_word_forward'): main_window.delete_word_forward()

@emacs_command("M-DEL", "Delete word backward")
def delete_word_backward(main_window):
    if main_window and hasattr(main_window, 'delete_word_backward'): main_window.delete_word_backward()

@emacs_command("C-k", "Kill (cut) to end of line")
def kill_line(main_window):
    if main_window and hasattr(main_window, 'kill_line'): main_window.kill_line()

@emacs_command("C-y", "Yank (paste)")
def yank(main_window):
    if main_window and hasattr(main_window, 'yank'): main_window.yank()

@emacs_command("M-y", "Cycle through kill ring (after yank)")
def yank_pop(main_window):
    if main_window and hasattr(main_window, 'yank_pop'): main_window.yank_pop()

@emacs_command("C-/", "Undo")
def undo(main_window):
    if main_window: main_window.trigger_undo()

@emacs_command("C-x u", "Undo (alternate)")
def undo_alt(main_window):
    if main_window: main_window.trigger_undo()

@emacs_command("C-SPC", "Set mark (start selecting)")
def set_mark(main_window):
    if main_window and hasattr(main_window, 'set_mark'): main_window.set_mark()

@emacs_command("C-w", "Kill (cut) region")
def kill_region(main_window):
    if main_window and hasattr(main_window, 'kill_region'): main_window.kill_region()

@emacs_command("M-w", "Copy region")
def copy_region(main_window):
    if main_window and hasattr(main_window, 'copy_region'): main_window.copy_region()

# --- Search & Replace ---
@emacs_command("C-s", "Incremental search forward")
def isearch_forward(main_window):
    if main_window: main_window.open_search_dialog("find")

@emacs_command("C-r", "Incremental search backward")
def isearch_backward(main_window):
    if main_window and hasattr(main_window, 'open_search_dialog_backward'): main_window.open_search_dialog_backward()

@emacs_command("M-%", "Query replace")
def query_replace(main_window):
    if main_window and hasattr(main_window, 'query_replace'): main_window.query_replace()

@emacs_command("C-M-%", "Query replace using regex")
def query_replace_regex(main_window):
    if main_window and hasattr(main_window, 'query_replace_regex'): main_window.query_replace_regex()

# --- Macros ---
@emacs_command("C-x (", "Start recording macro")
def start_macro(main_window):
    if main_window and hasattr(main_window, 'start_macro'): main_window.start_macro()

@emacs_command("C-x )", "Stop recording macro")
def stop_macro(main_window):
    if main_window and hasattr(main_window, 'stop_macro'): main_window.stop_macro()

@emacs_command("C-x e", "Execute last macro")
def execute_macro(main_window):
    if main_window and hasattr(main_window, 'execute_macro'): main_window.execute_macro()

@emacs_command("M-x name-last-kbd-macro", "Name last macro")
def name_last_macro(main_window):
    if main_window and hasattr(main_window, 'name_last_macro'): main_window.name_last_macro()

@emacs_command("M-x insert-kbd-macro", "Insert macro into buffer")
def insert_macro(main_window):
    if main_window and hasattr(main_window, 'insert_macro'): main_window.insert_macro()

# --- Window Management ---
@emacs_command("C-x 0", "Close current window")
def close_window(main_window):
    if main_window: main_window.close()

@emacs_command("C-x 1", "Close all other windows")
def close_other_windows(main_window):
    if main_window and hasattr(main_window, 'close_other_windows'): main_window.close_other_windows()

@emacs_command("C-x 2", "Split window horizontally")
def split_window_horizontally(main_window):
    if main_window and hasattr(main_window, 'split_window_horizontally'): main_window.split_window_horizontally()

@emacs_command("C-x 3", "Split window vertically")
def split_window_vertically(main_window):
    if main_window and hasattr(main_window, 'split_window_vertically'): main_window.split_window_vertically()

@emacs_command("C-x o", "Switch to other window")
def switch_other_window(main_window):
    if main_window and hasattr(main_window, 'switch_other_window'): main_window.switch_other_window()

# --- Help & Info ---
@emacs_command("C-h t", "Emacs tutorial")
def emacs_tutorial(main_window):
    if main_window and hasattr(main_window, 'emacs_tutorial'): main_window.emacs_tutorial()

@emacs_command("C-h k", "Describe keybinding")
def describe_key(main_window):
    if main_window and hasattr(main_window, 'describe_key'): main_window.describe_key()

@emacs_command("C-h f", "Describe function")
def describe_function(main_window):
    if main_window and hasattr(main_window, 'describe_function'): main_window.describe_function()

@emacs_command("C-h v", "Describe variable")
def describe_variable(main_window):
    if main_window and hasattr(main_window, 'describe_variable'): main_window.describe_variable()

@emacs_command("C-h a", "Search for command by name (apropos)")
def apropos(main_window):
    if main_window and hasattr(main_window, 'apropos'): main_window.apropos()

# Utility to get all commands and descriptions
def get_emacs_commands():
    return [(name, data["description"]) for name, data in emacs_commands.items()]
