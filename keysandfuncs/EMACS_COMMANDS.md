# Emacs Minibar Commands

Below are the available Emacs-style commands you can use in the minibar. You can trigger them by either typing the command (e.g., C-x C-f) or by pressing the actual key sequence (e.g., Ctrl+X, then Ctrl+F) in the minibar.

## File & Buffer Management
| Key Sequence | Description |
|--------------|-------------|
| C-x C-f | Open file (find-file) |
| C-x C-s | Save current buffer |
| C-x C-w | Save buffer to a different file (write-file) |
| C-x b   | Switch to buffer |
| C-x C-b | List all buffers |
| C-x k   | Kill (close) buffer |
| C-x C-c | Quit Emacs |
| C-x C-v | Open a new file, replacing current buffer |

## Navigation
| Key Sequence | Description |
|--------------|-------------|
| C-a   | Move to beginning of line |
| C-e   | Move to end of line |
| M-<   | Move to beginning of buffer |
| M->   | Move to end of buffer |
| C-n   | Next line |
| C-p   | Previous line |
| C-f   | Forward character |
| C-b   | Backward character |
| M-f   | Forward word |
| M-b   | Backward word |
| C-v   | Page down |
| M-v   | Page up |
| C-l   | Center screen on current line |

## Editing Text
| Key Sequence | Description |
|--------------|-------------|
| C-d   | Delete character under cursor |
| M-d   | Delete word forward |
| M-DEL | Delete word backward |
| C-k   | Kill (cut) to end of line |
| C-y   | Yank (paste) |
| M-y   | Cycle through kill ring (after yank) |
| C-/   | Undo |
| C-x u | Undo (alternate) |
| C-SPC | Set mark (start selecting) |
| C-w   | Kill (cut) region |
| M-w   | Copy region |

## Search & Replace
| Key Sequence | Description |
|--------------|-------------|
| C-s   | Incremental search forward |
| C-r   | Incremental search backward |
| M-%   | Query replace |
| C-M-% | Query replace using regex |

## Macros
| Key Sequence | Description |
|--------------|-------------|
| C-x ( | Start recording macro |
| C-x ) | Stop recording macro |
| C-x e | Execute last macro |
| M-x name-last-kbd-macro | Name last macro |
| M-x insert-kbd-macro    | Insert macro into buffer |

## Window Management
| Key Sequence | Description |
|--------------|-------------|
| C-x 0 | Close current window |
| C-x 1 | Close all other windows |
| C-x 2 | Split window horizontally |
| C-x 3 | Split window vertically |
| C-x o | Switch to other window |

## Help & Info
| Key Sequence | Description |
|--------------|-------------|
| C-h t | Emacs tutorial |
| C-h k | Describe keybinding |
| C-h f | Describe function |
| C-h v | Describe variable |
| C-h a | Search for command by name (apropos) | 