# -*- coding: utf-8 -*-
"""
nice_console_tabby_style.py

A minimal terminal UI visually matching the reference image (Tabby terminal style).
- Option panel (hide/show with arrow button)
- Mac-style traffic light window controls (red/yellow/green)
- Flat dark background, rounded corners, subtle drop shadow
- Font/terminal area matches screenshot as close as possible
- No large toolbar/buttons, small icons
- Split panes (horizontal/vertical), tabs, and option panel as shown
- All UI colors, padding, and controls matched to photo

Requires: PyQt5, Python 3.8+
"""

import os
import sys
import platform
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QSplitter,
    QTextEdit, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QComboBox, QLabel, QFrame, QStyle, QSizePolicy, QDialog, QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QProcess, QEvent, QTimer, pyqtSignal, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QPalette, QBrush, QIcon, QTextCharFormat, QTextCursor, QSyntaxHighlighter, QPixmap, QPainterPath

# --- CONFIGURATION ---

def get_default_dir():
    if platform.system() == "Windows":
        return str(Path.home())
    return str(Path.home())

CONFIG = {
    "bg": "#22232b",
    "fg": "#e6e8ef",
    "prompt_color": "#7ad6ff",
    "stderr_color": "#ff5370",
    "git_color": "#a5e075",
    "font": QFont("JetBrains Mono", 14),
    "session_file": ".nice_console_session.json",
    "shells": {
        "powershell": {
            "cmd": "powershell",
            "args": ["-NoLogo", "-NoExit", "-Command", "-"],
            "prompt": "PS {dir}> "
        },
        "bash": {
            "cmd": "bash",
            "args": ["--login", "-i"],
            "prompt": "{dir}$ "
        },
        "git-bash": {
            "cmd": "bash",
            "args": ["--login", "-i"],
            "prompt": "gitbash:{dir}$ "
        },
        "cmd": {
            "cmd": "cmd",
            "args": [],
            "prompt": "{dir}> "
        }
    },
    "accent": "#4bcf75",
    "tab_bg": "#23242c",
    "tab_active": "#282932",
    "tab_text": "#cccccc",
    "border": "#202128",
    "tab_radius": 12,
    "tab_fontsize": 14,
    "tab_padding": "6px 24px",
    "shadow": "#00000020",
    "panel_bg": "#23242c",
    "panel_fg": "#92a1b0",
    "panel_border": "#262932",
    "mac_red": "#ff5f56",
    "mac_yellow": "#ffbd2e",
    "mac_green": "#27c93f",
}

SUPPORTED_SHELLS = list(CONFIG["shells"].keys())

# --- UTILITY CLASSES ---

class TerminalHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.prompt_format = QTextCharFormat()
        self.prompt_format.setForeground(QColor(CONFIG["prompt_color"]))
        self.prompt_format.setFontWeight(QFont.Bold)
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor(CONFIG["stderr_color"]))
        self.error_format.setFontItalic(True)
        self.git_format = QTextCharFormat()
        self.git_format.setForeground(QColor(CONFIG["git_color"]))
        self.git_format.setFontWeight(QFont.Bold)

    def highlightBlock(self, text):
        if text.strip().startswith(("PS", "$", ">", "gitbash:")):
            self.setFormat(0, len(text), self.prompt_format)
        elif "git" in text and text.strip().startswith("git "):
            self.setFormat(0, len(text), self.git_format)
        elif any(e in text.lower() for e in ["error", "fail", "fatal"]):
            self.setFormat(0, len(text), self.error_format)

class ClosableWidget(QWidget):
    closed = pyqtSignal()
    def __init__(self, content_widget, parent=None):
        super().__init__(parent)
        self.content = content_widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.content)
        self.setLayout(layout)
    def _close(self):
        self.closed.emit()
        self.deleteLater()

class Workspace:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.session_file = str(Path(self.path) / CONFIG["session_file"])

# --- MACOS WINDOW TRAFFIC LIGHTS ---

class TrafficLights(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(62, 22)
        self.setAttribute(Qt.WA_TranslucentBackground)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = [CONFIG['mac_red'], CONFIG['mac_yellow'], CONFIG['mac_green']]
        x = 10
        for color in colors:
            painter.setBrush(QColor(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPoint(x, 11), 7, 7)
            x += 20

# --- OPTION PANEL ---

class OptionPanel(QFrame):
    toggled = pyqtSignal(bool)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OptionPanel")
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QFrame#OptionPanel {{
                background: {CONFIG['panel_bg']};
                border-right: 1px solid {CONFIG['panel_border']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 2, 2)
        # Panel title and hide arrow
        title_bar = QHBoxLayout()
        lbl = QLabel("Options")
        lbl.setStyleSheet(f"color: {CONFIG['panel_fg']}; font-size: 13px; font-weight: bold;")
        title_bar.addWidget(lbl)
        title_bar.addStretch()
        self.arrow_btn = QPushButton("←")
        self.arrow_btn.setFixedSize(20, 22)
        self.arrow_btn.setCursor(Qt.PointingHandCursor)
        self.arrow_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 17px;
            }
            QPushButton:hover { color: #fff; }
        """)
        self.arrow_btn.clicked.connect(self.hide_panel)
        title_bar.addWidget(self.arrow_btn)
        layout.addLayout(title_bar)
        layout.addSpacing(10)
        # Combo for shell, open folder
        self.shell_box = QComboBox()
        self.shell_box.addItems(SUPPORTED_SHELLS)
        self.shell_box.setStyleSheet(f"""
            QComboBox {{
                background: {CONFIG['tab_active']};
                color: {CONFIG['accent']};
                font-size: 13px;
                border-radius: 7px;
                padding: 5px 10px;
            }}
        """)
        layout.addWidget(self.shell_box)
        layout.addSpacing(14)
        self.open_btn = QPushButton("Open console in folder")
        self.open_btn.setCursor(Qt.PointingHandCursor)
        self.open_btn.setStyleSheet(f"""
            QPushButton {{
                background: {CONFIG['tab_active']};
                color: {CONFIG['accent']};
                border: none;
                border-radius: 9px;
                padding: 7px 10px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {CONFIG['accent']}22;
                color: {CONFIG['fg']};
            }}
        """)
        layout.addWidget(self.open_btn)
        layout.addStretch()
        self.setLayout(layout)
    def hide_panel(self):
        self.setVisible(False)
        self.toggled.emit(False)
    def show_panel(self):
        self.setVisible(True)
        self.toggled.emit(True)

# --- MINIMAP/SHOW OPTIONS ARROW ---

class MiniMapWidget(QWidget):
    clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(18)
        self.setCursor(Qt.PointingHandCursor)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw simple ">" arrow
        path = QPainterPath()
        path.moveTo(6, 7)
        path.lineTo(13, 13)
        path.lineTo(6, 19)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#888"))
        painter.drawPath(path)
    def mousePressEvent(self, event):
        self.clicked.emit()

# --- TERMINAL PANE ---

class TerminalPane(QWidget):
    def __init__(self, workspace, shell="powershell", parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.shell = shell
        self.history = []
        self.history_index = 0
        self.process = None
        self.current_prompt = ""
        self.output_locked = False
        self.init_ui()
        self.start_shell()
        self.setFocusPolicy(Qt.StrongFocus)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(0)
        # Terminal output area
        self.output = QTextEdit()
        self.output.setReadOnly(False)
        self.output.setFont(CONFIG["font"])
        self.output.setStyleSheet(self._output_stylesheet())
        self.output.installEventFilter(self)
        TerminalHighlighter(self.output.document())
        self.output.setContextMenuPolicy(Qt.DefaultContextMenu)
        layout.addWidget(self.output)
        self.setLayout(layout)

    def _output_stylesheet(self):
        return f"""
            background: {CONFIG["bg"]};
            color: {CONFIG['fg']};
            border: none;
            border-radius: 0px;
            padding: 0px 0px 3px 8px;
            selection-background-color: #3ac6e0cc;
            font-size: 14px;
        """

    def eventFilter(self, obj, event):
        if obj == self.output and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.execute_command()
                return True
            elif key == Qt.Key_Up:
                self.navigate_history(-1)
                return True
            elif key == Qt.Key_Down:
                self.navigate_history(1)
                return True
            elif key == Qt.Key_Backspace:
                cursor = self.output.textCursor()
                pos = cursor.position()
                if pos > self.output.document().lastBlock().position() + len(self.current_prompt):
                    return False
                else:
                    return True
        return super().eventFilter(obj, event)

    def set_shell(self, shell_name):
        self.shell = shell_name
        self.terminate_shell()
        self.start_shell()

    def start_shell(self):
        if self.process:
            self.terminate_shell()
        shell_cfg = CONFIG["shells"][self.shell]
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.setWorkingDirectory(self.workspace.path)
        cmd = shell_cfg["cmd"]
        args = shell_cfg["args"]
        if self.shell == "git-bash":
            git_bash = self.find_git_bash()
            if not git_bash:
                self.show_system_msg("Git Bash not found on this system.")
                return
            cmd = git_bash
        if not self._is_shell_available(cmd):
            self.show_system_msg(f"Shell '{cmd}' not found.")
            self.output_locked = True
            return
        self.process.start(cmd, args)
        started = self.process.waitForStarted(1000)
        if not started:
            self.show_system_msg(f"Failed to start '{cmd}'")
            self.output_locked = True
            return
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        QTimer.singleShot(200, self.show_prompt)

    def _is_shell_available(self, cmd):
        if os.path.isabs(cmd):
            return os.path.exists(cmd)
        for p in os.environ.get("PATH", "").split(os.pathsep):
            exe = os.path.join(p, cmd + (".exe" if platform.system()=="Windows" else ""))
            if os.path.isfile(exe):
                return True
        return False

    def terminate_shell(self):
        if self.process:
            self.process.kill()
            self.process = None

    def find_git_bash(self):
        guesses = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe"
        ]
        for guess in guesses:
            if os.path.isfile(guess):
                return guess
        return None

    def navigate_history(self, delta):
        if not self.history:
            return
        self.history_index = max(0, min(self.history_index + delta, len(self.history)-1))
        self.replace_input(self.history[self.history_index])

    def replace_input(self, text):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(self.current_prompt + text)
        self.output.setTextCursor(cursor)

    def show_prompt(self):
        shell_cfg = CONFIG["shells"][self.shell]
        prompt = shell_cfg["prompt"].format(dir=os.path.basename(self.workspace.path))
        self.current_prompt = prompt
        self.output.setTextColor(QColor(CONFIG["prompt_color"]))
        self.output.append(self.current_prompt)
        self.move_cursor_to_end()
        self.output_locked = False

    def move_cursor_to_end(self):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output.setTextCursor(cursor)

    def get_current_input(self):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        line = cursor.selectedText()
        if line.startswith(self.current_prompt):
            return line[len(self.current_prompt):].strip()
        return line.strip()

    def execute_command(self):
        if self.output_locked:
            return
        cmd = self.get_current_input()
        if not cmd:
            self.show_prompt()
            return
        self.history.append(cmd)
        self.history_index = len(self.history)
        self.output_locked = True

        if self.shell in ("git-bash", "bash"):
            to_write = cmd + '\n'
        elif self.shell == "cmd":
            to_write = cmd + "\n"
        else:
            to_write = cmd + "\n"

        try:
            self.process.write(to_write.encode("utf-8"))
        except Exception as e:
            self.show_system_msg(f"Failed to write to shell: {e}")
            self.output_locked = False

    def handle_stdout(self):
        data = self.process.readAllStandardOutput().data().decode(errors="replace")
        self.output.setTextColor(QColor(CONFIG["fg"]))
        self.output.insertPlainText(data)
        self.move_cursor_to_end()
        self.output_locked = False

    def handle_stderr(self):
        data = self.process.readAllStandardError().data().decode(errors="replace")
        self.output.setTextColor(QColor(CONFIG["stderr_color"]))
        self.output.insertPlainText(data)
        self.move_cursor_to_end()
        self.output_locked = False

    def process_finished(self):
        self.show_system_msg("Shell process ended.")
        self.output_locked = True

    def show_system_msg(self, msg):
        self.output.setTextColor(QColor(CONFIG["stderr_color"]))
        self.output.append(f"[SYSTEM] {msg}")
        self.move_cursor_to_end()

# --- SPLIT PANE ---

class TabPane(QSplitter):
    def __init__(self, workspace_path, shell, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.workspace_path = workspace_path
        self.shell = shell
        self.setSizes([1])
        self.init_panes()

    def init_panes(self):
        self.terminal = TerminalPane(Workspace(self.workspace_path), self.shell)
        closable_term = ClosableWidget(self.terminal)
        closable_term.closed.connect(self._close_self)
        self.addWidget(closable_term)

    def _close_self(self):
        if self.count() == 1:
            parent_tab = self.parentWidget()
            if hasattr(parent_tab, 'deleteLater'):
                parent_tab.deleteLater()
        else:
            for i in range(self.count()):
                widget = self.widget(i)
                if isinstance(widget, ClosableWidget) and widget.isHidden():
                    self.widget(i).deleteLater()

# --- MAIN APP WINDOW ---

class NiceConsoleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tabby Style Terminal")
        self.setMinimumSize(900, 530)
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setMovable(True)
        self.setCentralWidget(self.tabs)
        self.default_dir = get_default_dir()
        self.active_shell = "bash" if platform.system() != "Windows" else "powershell"
        self.option_panel = OptionPanel()
        self.option_panel.hide_panel()
        self.option_panel.shell_box.setCurrentText(self.active_shell)
        self.option_panel.shell_box.currentTextChanged.connect(self.set_active_shell)
        self.option_panel.open_btn.clicked.connect(self.open_console_in_folder)
        self.option_panel.toggled.connect(self._panel_toggled)
        self.minimap = MiniMapWidget()
        self.minimap.clicked.connect(self.show_option_panel)
        # Top bar
        self._make_topbar()
        # Layout
        main_widget = QWidget()
        self.main_layout = QHBoxLayout(main_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.option_panel)
        self.main_layout.addWidget(self.minimap)
        self.main_layout.addWidget(self.tabs)
        self.setCentralWidget(main_widget)
        # Visual polish
        self.setStyleSheet(self._main_stylesheet())
        # Start in default dir
        self.add_tab(self.default_dir, shell=self.active_shell)

    def _make_topbar(self):
        bar = QWidget()
        bar.setFixedHeight(36)
        bar.setStyleSheet(f"background: {CONFIG['tab_bg']}; border-top-left-radius: 13px; border-top-right-radius: 13px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 6, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(TrafficLights())
        layout.addStretch()
        gear = QLabel()
        gear.setPixmap(QPixmap(16,16))
        gear.setFixedSize(24,24)
        layout.addWidget(gear)
        # Insert before tabs
        self.setMenuWidget(bar)

    def _main_stylesheet(self):
        return f"""
            QMainWindow {{
                background: {CONFIG['bg']};
                border-radius: 15px;
            }}
            QTabWidget::pane {{
                border: none;
                background: {CONFIG['tab_bg']};
                border-radius: {CONFIG['tab_radius']}px;
            }}
            QTabBar::tab {{
                background: {CONFIG['tab_bg']};
                color: {CONFIG['tab_text']};
                border: none;
                border-radius: {CONFIG['tab_radius']}px {CONFIG['tab_radius']}px 0 0;
                min-width: 100px;
                padding: {CONFIG['tab_padding']};
                font-size: {CONFIG["tab_fontsize"]}px;
                margin-right: 2px;
                margin-left: 2px;
                font-family: JetBrains Mono, Fira Mono, Menlo, 'DejaVu Sans Mono', monospace;
                font-weight: 500;
                letter-spacing: 1.1px;
            }}
            QTabBar::tab:selected {{
                background: {CONFIG['tab_active']};
                color: {CONFIG['accent']};
                border-bottom: 2px solid {CONFIG['accent']};
            }}
            QTabBar::tab:hover {{
                background: #23262c;
                color: {CONFIG['accent']};
            }}
        """

    def set_active_shell(self, shell):
        self.active_shell = shell

    def show_option_panel(self):
        self.option_panel.show_panel()
        self.minimap.setVisible(False)

    def _panel_toggled(self, visible):
        self.minimap.setVisible(not visible)

    def add_tab(self, path, shell=None):
        if not path or not os.path.isdir(path):
            return
        if shell is None:
            shell = self.active_shell
        pane = TabPane(path, shell)
        tab_label = os.path.basename(path) or path
        self.tabs.addTab(pane, tab_label)
        self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def close_tab(self, idx):
        widget = self.tabs.widget(idx)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(idx)

    def open_console_in_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Folder for New Console", self.default_dir)
        if not path:
            return
        self.add_tab(path, shell=self.option_panel.shell_box.currentText())

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = NiceConsoleApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()