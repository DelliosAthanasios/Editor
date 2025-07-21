from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, QLabel, QSizePolicy, QFrame, QSplitter
)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QTextCursor, QPalette
import os
import sys
import json
import tempfile
import re
from .theme_manager import theme_manager_singleton, get_editor_styles

# Modern Visual Styles
CONSOLE_FONT = QFont("Consolas", 11)
CONSOLE_BG = "#1e1e1e"
CONSOLE_FG = "#d4d4d4"
CONSOLE_TAB_BG = "#252526"
CONSOLE_TAB_ACTIVE = "#1e1e1e"
CONSOLE_TAB_TEXT = "#d4d4d4"
CONSOLE_TAB_INACTIVE = "#858585"
CONSOLE_TAB_LINE = "#007acc"
CONSOLE_BORDER = "#3c3c3c"
CONSOLE_SELECTION = "#264f78"
CONSOLE_ERROR = "#f14c4c"
CONSOLE_SUCCESS = "#6a9955"
CONSOLE_PANEL_MIN_HEIGHT = 100
CONSOLE_PANEL_MAX_HEIGHT = 300

class ModernTabBar(QTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabPosition(QTabWidget.North)
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        self.setStyleSheet(f"""
            QTabBar::tab {{
                background: {palette['base']};
                color: {palette['mid']};
                padding: 6px 16px;
                border: none;
                font: 11px 'Segoe UI';
                min-width: 60px;
            }}
            QTabBar::tab:selected {{
                background: {palette['window']};
                color: {palette['window_text']};
                border-bottom: 2px solid {palette['highlight']};
            }}
            QTabWidget::pane {{
                border-top: 1px solid {palette['mid']};
                top: -1px;
            }}
        """)

class TerminalTab(QWidget):
    def __init__(self, shell_cmd, prompt, parent=None):
        super().__init__(parent)
        self.shell_cmd = shell_cmd
        self.prompt = prompt
        self.process = None
        self.command_history = []
        self.history_index = -1
        self.is_powershell = shell_cmd == "powershell"
        self.prompt_pattern = re.compile(r'^PS\s+[A-Z]:\\.*>?\s*$')
        self.init_ui()
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)
        self.start_shell()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Output area with custom styling
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(CONSOLE_FONT)
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background: {CONSOLE_BG};
                color: {CONSOLE_FG};
                border: none;
                selection-background-color: {CONSOLE_SELECTION};
            }}
        """)
        self.output.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.output.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.output.setLineWrapMode(QTextEdit.NoWrap)

        # Input area with custom styling
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background: {CONSOLE_BG};
                border: 1px solid {CONSOLE_BORDER};
                border-radius: 2px;
            }}
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(4, 2, 4, 2)
        input_layout.setSpacing(4)

        self.prompt_label = QLabel(self.prompt)
        self.prompt_label.setFont(CONSOLE_FONT)
        self.prompt_label.setStyleSheet(f"color: {CONSOLE_FG};")

        self.input = QLineEdit()
        self.input.setFont(CONSOLE_FONT)
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {CONSOLE_FG};
                border: none;
                selection-background-color: {CONSOLE_SELECTION};
            }}
        """)
        self.input.setFrame(False)
        self.input.returnPressed.connect(self.execute_command)
        self.input.installEventFilter(self)

        input_layout.addWidget(self.prompt_label)
        input_layout.addWidget(self.input)

        layout.addWidget(self.output)
        layout.addWidget(input_frame)
        self.setLayout(layout)
        self.setMinimumHeight(CONSOLE_PANEL_MIN_HEIGHT)
        self.setMaximumHeight(CONSOLE_PANEL_MAX_HEIGHT)
        self.input.setFocus()

    def eventFilter(self, obj, event):
        if obj == self.input and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Up:
                self.navigate_history(-1)
                return True
            elif event.key() == Qt.Key_Down:
                self.navigate_history(1)
                return True
        return super().eventFilter(obj, event)

    def navigate_history(self, direction):
        if not self.command_history:
            return
        
        if direction < 0 and self.history_index <= 0:
            self.history_index = 0
        elif direction > 0 and self.history_index >= len(self.command_history) - 1:
            self.history_index = len(self.command_history)
            self.input.clear()
            return
        
        self.history_index = max(0, min(len(self.command_history) - 1, 
                                      self.history_index + direction))
        self.input.setText(self.command_history[self.history_index])
        self.input.setCursorPosition(len(self.input.text()))

    def start_shell(self):
        if self.process:
            try:
                self.process.kill()
                self.process.waitForFinished(1000)
            except:
                pass
            self.process = None

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_output)
        self.process.readyReadStandardError.connect(self.handle_error)
        self.process.finished.connect(self.handle_process_finished)

        try:
            if sys.platform == "win32" and self.shell_cmd == "bash":
                self.process.start("wsl.exe")
            elif sys.platform == "win32" and self.is_powershell:
                self.process.start("powershell.exe", ["-NoProfile", "-NoLogo"])
            else:
                self.process.start(self.shell_cmd)

            if not self.process.waitForStarted(3000):
                raise Exception("Process failed to start")
        except Exception as e:
            self.write_output(f"Failed to start shell: {str(e)}\n", CONSOLE_ERROR)
            QTimer.singleShot(1000, self.start_shell)

    def handle_process_finished(self, exit_code, exit_status):
        if exit_status == QProcess.CrashExit:
            self.write_output("\nProcess crashed. Restarting...\n", CONSOLE_ERROR)
            QTimer.singleShot(1000, self.start_shell)
        elif exit_code != 0:
            self.write_output(f"\nProcess exited with code {exit_code}\n", CONSOLE_ERROR)
            QTimer.singleShot(1000, self.start_shell)

    def execute_command(self):
        if not self.process or self.process.state() != QProcess.Running:
            self.write_output("Shell not running. Restarting...\n", CONSOLE_ERROR)
            self.start_shell()
            return

        cmd = self.input.text().strip()
        if not cmd:
            return

        if cmd not in self.command_history:
            self.command_history.append(cmd)
        self.history_index = len(self.command_history)

        self.write_output(f"{self.prompt} {cmd}\n", CONSOLE_FG)

        try:
            if self.is_powershell:
                self.process.write((cmd + "\r\n").encode('utf-8'))
            else:
                self.process.write((cmd + "\n").encode('utf-8'))
        except Exception as e:
            self.write_output(f"Error sending command: {str(e)}\n", CONSOLE_ERROR)

        self.input.clear()
        self.input.setFocus()

    def handle_output(self):
        try:
            if not self.process:
                return

            data = self.process.readAllStandardOutput().data().decode('utf-8', errors="ignore")
            if not data.strip():
                return

            lines = data.split('\n')
            filtered_lines = []
            
            for line in lines:
                stripped_line = line.strip()
                
                # Skip empty lines
                if not stripped_line:
                    continue
                    
                # Skip PowerShell prompts
                if self.is_powershell:
                    if self.prompt_pattern.match(stripped_line):
                        continue
                    if stripped_line == ">" or stripped_line.startswith("PS "):
                        continue
                
                filtered_lines.append(line)

            if filtered_lines:
                final_data = "\n".join(filtered_lines)
                self.write_output(final_data, CONSOLE_FG)
            
        except Exception as e:
            self.write_output(f"Error reading output: {str(e)}\n", CONSOLE_ERROR)

    def handle_error(self):
        try:
            if not self.process:
                return

            data = self.process.readAllStandardError().data().decode('utf-8', errors="ignore")
            if data.strip():
                self.write_output(data, CONSOLE_ERROR)
        except Exception as e:
            self.write_output(f"Error reading error output: {str(e)}\n", CONSOLE_ERROR)

    def write_output(self, text, color=CONSOLE_FG):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        format = cursor.charFormat()
        format.setForeground(QColor(color))
        cursor.setCharFormat(format)
        cursor.insertText(text)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def closeEvent(self, event):
        if self.process:
            try:
                self.process.kill()
                self.process.waitForFinished(1000)
            except:
                pass
        super().closeEvent(event)

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        self.output.setStyleSheet(f"""
            QTextEdit {{
                background: {editor['background']};
                color: {editor['foreground']};
                border: none;
                selection-background-color: {editor['selection_background']};
            }}
        """)
        self.prompt_label.setStyleSheet(f"color: {editor['foreground']};")
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {editor['foreground']};
                border: none;
                selection-background-color: {editor['selection_background']};
            }}
        """)
        self.parent().setStyleSheet(f"background: {editor['background']}; border-top: 1px solid {palette['mid']};")

class ConsolePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        theme_data = theme_manager_singleton.get_theme()
        self.set_theme(theme_data)
        theme_manager_singleton.themeChanged.connect(self.set_theme)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create tabs
        self.tabs = ModernTabBar()
        
        # Add terminal tabs
        self.tabs.addTab(TerminalTab("powershell", "PS>", self), "PowerShell")
        self.tabs.addTab(TerminalTab("bash", "$", self), "Bash")

        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.setMinimumHeight(CONSOLE_PANEL_MIN_HEIGHT)
        self.setMaximumHeight(CONSOLE_PANEL_MAX_HEIGHT)
        self.setStyleSheet(f"""
            QWidget {{
                background: {CONSOLE_BG};
                border-top: 1px solid {CONSOLE_BORDER};
            }}
        """)

    def focusInEvent(self, event):
        current = self.tabs.currentWidget()
        if hasattr(current, 'input'):
            current.input.setFocus()
        super().focusInEvent(event)

    def set_font(self, font):
        """Set font for all console components"""
        CONSOLE_FONT = font
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'output'):
                widget.output.setFont(font)
            if hasattr(widget, 'input'):
                widget.input.setFont(font)
            if hasattr(widget, 'prompt_label'):
                widget.prompt_label.setFont(font)

    def set_theme(self, theme_data):
        palette = theme_data["palette"]
        editor = theme_data["editor"]
        self.setStyleSheet(f"background: {editor['background']}; border-top: 1px solid {palette['mid']};")
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if hasattr(widget, 'set_theme'):
                widget.set_theme(theme_data)
