import os
import sys
import json
import threading
import time
from typing import Optional, Callable, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, 
    QPushButton, QTextEdit, QSpinBox, QCheckBox, QGroupBox,
    QMessageBox, QApplication, QWidget, QSplitter, QTabWidget
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont, QTextCursor

# Configuration
def load_config():
    """Load configuration from JSON file"""
    try:
        with open('advanced_loading_config.json', 'r') as f:
            config = json.load(f)
        return config
    except (FileNotFoundError, json.JSONDecodeError):
        # Return default configuration if file not found or invalid
        return {
            "line_threshold": 1000,
            "chunk_size": 1000,
            "memory_limit_mb": 50,
            "preview_lines": 50,
            "supported_encodings": ["utf-8", "latin-1", "cp1252", "iso-8859-1"],
            "ui_settings": {
                "dialog_width": 500,
                "dialog_height": 400,
                "preview_height": 150
            },
            "performance": {
                "max_preview_lines": 100,
                "chunk_size_min": 100,
                "chunk_size_max": 10000
            }
        }

# Load configuration
CONFIG = load_config()
DEFAULT_LINE_THRESHOLD = CONFIG.get("line_threshold", 1000)
DEFAULT_CHUNK_SIZE = CONFIG.get("chunk_size", 1000)
DEFAULT_MEMORY_LIMIT = CONFIG.get("memory_limit_mb", 50) * 1024 * 1024

class FileAnalyzer(QObject):
    """Analyzes file size and determines if advanced loading is needed"""
    
    def __init__(self):
        super().__init__()
        self.line_threshold = CONFIG.get("line_threshold", DEFAULT_LINE_THRESHOLD)
        self.memory_limit = CONFIG.get("memory_limit_mb", 50) * 1024 * 1024
        self.supported_encodings = CONFIG.get("supported_encodings", ["utf-8", "latin-1", "cp1252", "iso-8859-1"])
    
    def should_use_advanced_loading(self, file_path: str) -> tuple[bool, Dict[str, Any]]:
        """
        Determines if a file should use advanced loading
        Returns: (should_use_advanced, file_info)
        """
        try:
            file_size = os.path.getsize(file_path)
            file_info = {
                'path': file_path,
                'size': file_size,
                'size_mb': file_size / (1024 * 1024),
                'lines': 0,
                'encoding': 'utf-8'
            }
            
            # Check file size first
            if file_size > self.memory_limit:
                return True, file_info
            
            # Count lines efficiently
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
                file_info['lines'] = line_count
                
                if line_count > self.line_threshold:
                    return True, file_info
                    
            except UnicodeDecodeError:
                # Try different encodings from configuration
                for encoding in self.supported_encodings[1:]:  # Skip utf-8 as it was already tried
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            line_count = sum(1 for _ in f)
                        file_info['lines'] = line_count
                        file_info['encoding'] = encoding
                        
                        if line_count > self.line_threshold:
                            return True, file_info
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # If all encodings fail, treat as binary
                    return True, file_info
            
            return False, file_info
            
        except Exception as e:
            return False, {'error': str(e)}

class ChunkedFileLoader(QThread):
    """Loads large files in chunks with progress reporting"""
    
    progress_updated = pyqtSignal(int, int)  # current, total
    chunk_loaded = pyqtSignal(list)  # lines in chunk
    loading_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, encoding: str = 'utf-8'):
        super().__init__()
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.encoding = encoding
        self.total_lines = 0
        self.is_cancelled = False
    
    def run(self):
        try:
            # First pass: count total lines
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                self.total_lines = sum(1 for _ in f)
            
            if self.total_lines == 0:
                self.loading_finished.emit()
                return
            
            # Second pass: load in chunks
            with open(self.file_path, 'r', encoding=self.encoding) as f:
                chunk = []
                current_line = 0
                
                for line in f:
                    if self.is_cancelled:
                        return
                    
                    chunk.append(line.rstrip('\n'))
                    current_line += 1
                    
                    if len(chunk) >= self.chunk_size:
                        self.chunk_loaded.emit(chunk)
                        self.progress_updated.emit(current_line, self.total_lines)
                        chunk = []
                
                # Emit remaining lines
                if chunk:
                    self.chunk_loaded.emit(chunk)
                    self.progress_updated.emit(current_line, self.total_lines)
            
            self.loading_finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def cancel(self):
        self.is_cancelled = True

class AdvancedLoadingDialog(QDialog):
    """Dialog for advanced file loading with progress and options"""
    
    def __init__(self, file_path: str, file_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.file_info = file_info
        self.loader = None
        self.loaded_content = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Advanced File Loading")
        ui_settings = CONFIG.get("ui_settings", {})
        self.setMinimumSize(
            ui_settings.get("dialog_width", 600), 
            ui_settings.get("dialog_height", 500)
        )
        self.setModal(True)
        
        # Main layout with proper spacing
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # File info with better formatting
        info_group = QGroupBox("📄 File Information")
        info_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(8)
        
        # Create a grid layout for file info
        info_grid = QHBoxLayout()
        
        # Left column
        left_info = QVBoxLayout()
        left_info.addWidget(QLabel(f"📁 File: {os.path.basename(self.file_path)}"))
        left_info.addWidget(QLabel(f"📊 Size: {self.file_info.get('size_mb', 0):.2f} MB"))
        
        # Right column
        right_info = QVBoxLayout()
        right_info.addWidget(QLabel(f"📝 Lines: {self.file_info.get('lines', 'Unknown'):,}"))
        right_info.addWidget(QLabel(f"🔤 Encoding: {self.file_info.get('encoding', 'utf-8')}"))
        
        info_grid.addLayout(left_info)
        info_grid.addSpacing(20)
        info_grid.addLayout(right_info)
        info_grid.addStretch()
        
        info_layout.addLayout(info_grid)
        layout.addWidget(info_group)
        
        # Loading options with better spacing
        options_group = QGroupBox("⚙️ Loading Options")
        options_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        options_layout = QVBoxLayout(options_group)
        options_layout.setSpacing(12)
        
        # Chunk size with better layout
        chunk_layout = QHBoxLayout()
        chunk_layout.addWidget(QLabel("📦 Lines per chunk:"))
        self.chunk_spinbox = QSpinBox()
        performance = CONFIG.get("performance", {})
        min_chunk = performance.get("chunk_size_min", 100)
        max_chunk = performance.get("chunk_size_max", 10000)
        self.chunk_spinbox.setRange(min_chunk, max_chunk)
        self.chunk_spinbox.setValue(CONFIG.get("chunk_size", DEFAULT_CHUNK_SIZE))
        self.chunk_spinbox.setMinimumWidth(100)
        chunk_layout.addWidget(self.chunk_spinbox)
        chunk_layout.addStretch()
        options_layout.addLayout(chunk_layout)
        
        # Preview option
        self.preview_checkbox = QCheckBox("👁️ Show preview while loading")
        self.preview_checkbox.setChecked(True)
        options_layout.addWidget(self.preview_checkbox)
        
        layout.addWidget(options_group)
        
        # Progress section with better styling
        progress_group = QGroupBox("📈 Loading Progress")
        progress_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; }")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setSpacing(8)
        
        self.progress_label = QLabel("⏳ Ready to load")
        self.progress_label.setStyleSheet("font-weight: bold; color: #666;")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(progress_group)
        
        # Preview area with minimalistic style
        if self.preview_checkbox.isChecked():
            preview_widget = QWidget()
            preview_layout = QVBoxLayout(preview_widget)
            preview_layout.setContentsMargins(0, 0, 0, 0)
            preview_layout.setSpacing(0)

            self.preview_text = QTextEdit()
            ui_settings = CONFIG.get("ui_settings", {})
            self.preview_text.setMaximumHeight(ui_settings.get("preview_height", 150))
            self.preview_text.setReadOnly(True)
            self.preview_text.setStyleSheet("""
                QTextEdit {
                    background: #fff;
                    color: #222;
                    border: none;
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 12px;
                    padding: 8px;
                }
            """)
            preview_layout.addWidget(self.preview_text)

            layout.addWidget(preview_widget)
        
        # Buttons with better styling and spacing
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.load_button = QPushButton("🚀 Start Loading")
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.load_button.clicked.connect(self.start_loading)
        
        self.cancel_button = QPushButton("❌ Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        self.cancel_button.setEnabled(False)
        
        self.ok_button = QPushButton("📖 Open in Editor")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        
        layout.addLayout(button_layout)
    
    def start_loading(self):
        self.load_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.ok_button.setEnabled(False)
        self.loaded_content = []
        
        # Create and start loader
        self.loader = ChunkedFileLoader(
            self.file_path,
            self.chunk_spinbox.value(),
            self.file_info.get('encoding', 'utf-8')
        )
        
        self.loader.progress_updated.connect(self.update_progress)
        self.loader.chunk_loaded.connect(self.handle_chunk)
        self.loader.loading_finished.connect(self.loading_complete)
        self.loader.error_occurred.connect(self.handle_error)
        
        self.loader.start()
    
    def update_progress(self, current: int, total: int):
        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(percentage)
        self.progress_label.setText(f"Loading... {current:,} / {total:,} lines ({percentage}%)")
    
    def handle_chunk(self, chunk: list):
        self.loaded_content.extend(chunk)
        
        # Update preview if enabled
        if self.preview_checkbox.isChecked() and hasattr(self, 'preview_text'):
            preview_lines_count = CONFIG.get("preview_lines", 50)
            preview_lines = self.loaded_content[-preview_lines_count:]  # Show last N lines
            self.preview_text.setPlainText('\n'.join(preview_lines))
            
            # Scroll to bottom
            cursor = self.preview_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.preview_text.setTextCursor(cursor)
    
    def loading_complete(self):
        self.progress_bar.setValue(100)
        self.progress_label.setText("Loading complete!")
        self.load_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.ok_button.setEnabled(True)
    
    def handle_error(self, error_msg: str):
        QMessageBox.critical(self, "Loading Error", f"Failed to load file: {error_msg}")
        self.reject()
    
    def get_content(self) -> str:
        """Returns the loaded content as a string"""
        return '\n'.join(self.loaded_content)
    
    def closeEvent(self, event):
        if self.loader and self.loader.isRunning():
            self.loader.cancel()
            self.loader.wait()
        event.accept()

class AdvancedFileEditor(QWidget):
    """Minimalistic chunked editor for large files"""
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.chunks = []
        self.current_chunk_index = 0
        self.chunk_size = CONFIG.get("chunk_size", DEFAULT_CHUNK_SIZE)
        self.total_lines = 0
        self.init_ui()
        self.load_file()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Minimal top bar for navigation
        nav_bar = QWidget()
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

        self.prev_chunk_btn = QPushButton("Previous")
        self.prev_chunk_btn.setFixedHeight(24)
        self.prev_chunk_btn.setFixedWidth(80)
        self.prev_chunk_btn.setFlat(True)
        self.prev_chunk_btn.clicked.connect(self.prev_chunk)
        nav_layout.addWidget(self.prev_chunk_btn)

        self.chunk_info_label = QLabel("")
        self.chunk_info_label.setStyleSheet("color: #666; font-size: 12px;")
        nav_layout.addWidget(self.chunk_info_label)

        self.next_chunk_btn = QPushButton("Next")
        self.next_chunk_btn.setFixedHeight(24)
        self.next_chunk_btn.setFixedWidth(80)
        self.next_chunk_btn.setFlat(True)
        self.next_chunk_btn.clicked.connect(self.next_chunk)
        nav_layout.addWidget(self.next_chunk_btn)

        nav_layout.addStretch()
        nav_layout.addWidget(QLabel("Jump:"))
        self.jump_spinbox = QSpinBox()
        self.jump_spinbox.setMinimum(1)
        self.jump_spinbox.setMaximum(1)
        self.jump_spinbox.setFixedWidth(60)
        self.jump_spinbox.valueChanged.connect(self.jump_to_chunk)
        nav_layout.addWidget(self.jump_spinbox)

        layout.addWidget(nav_bar)

        # High-contrast, distraction-free text area
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: #fff;
                color: #222;
                border: none;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                padding: 12px;
            }
        """)
        layout.addWidget(self.text_edit)

        # Subtle status bar at the bottom
        self.status_bar = QLabel("")
        self.status_bar.setStyleSheet("color: #888; font-size: 11px; padding: 4px 8px;")
        layout.addWidget(self.status_bar)

    def load_file(self):
        try:
            # Count total lines
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.total_lines = sum(1 for _ in f)
            # Load in chunks
            with open(self.file_path, 'r', encoding='utf-8') as f:
                chunk = []
                for line in f:
                    chunk.append(line.rstrip('\n'))
                    if len(chunk) >= self.chunk_size:
                        self.chunks.append(chunk)
                        chunk = []
                if chunk:
                    self.chunks.append(chunk)
            self.jump_spinbox.setMaximum(len(self.chunks))
            self.update_display()
        except Exception as e:
            self.text_edit.setPlainText(f"Error loading file: {e}")

    def update_display(self):
        if not self.chunks:
            self.text_edit.setPlainText("")
            self.chunk_info_label.setText("")
            self.status_bar.setText("")
            return
        chunk = self.chunks[self.current_chunk_index]
        self.text_edit.setPlainText('\n'.join(chunk))
        start_line = self.current_chunk_index * self.chunk_size + 1
        end_line = min(start_line + len(chunk) - 1, self.total_lines)
        self.chunk_info_label.setText(f"Chunk {self.current_chunk_index + 1}/{len(self.chunks)}  |  Lines {start_line}-{end_line}")
        self.jump_spinbox.blockSignals(True)
        self.jump_spinbox.setValue(self.current_chunk_index + 1)
        self.jump_spinbox.blockSignals(False)
        self.prev_chunk_btn.setEnabled(self.current_chunk_index > 0)
        self.next_chunk_btn.setEnabled(self.current_chunk_index < len(self.chunks) - 1)
        # Minimal status bar info
        self.status_bar.setText(f"{os.path.basename(self.file_path)}  •  {self.total_lines:,} lines  •  {len(self.chunks)} chunks  •  Chunk size: {self.chunk_size}")

    def jump_to_chunk(self, chunk_number):
        if 1 <= chunk_number <= len(self.chunks):
            self.current_chunk_index = chunk_number - 1
            self.update_display()

    def prev_chunk(self):
        if self.current_chunk_index > 0:
            self.current_chunk_index -= 1
            self.update_display()

    def next_chunk(self):
        if self.current_chunk_index < len(self.chunks) - 1:
            self.current_chunk_index += 1
            self.update_display()

    def get_full_content(self) -> str:
        return '\n'.join(['\n'.join(chunk) for chunk in self.chunks])

def should_use_advanced_loading(file_path: str, threshold: int = DEFAULT_LINE_THRESHOLD) -> tuple[bool, Dict[str, Any]]:
    """Convenience function to check if advanced loading should be used"""
    analyzer = FileAnalyzer()
    analyzer.line_threshold = threshold
    return analyzer.should_use_advanced_loading(file_path)

def load_large_file(file_path: str, parent=None) -> Optional[tuple]:
    """
    Load a large file using advanced loading if needed
    Returns a tuple (content, use_advanced_editor) or None if cancelled/error
    """
    should_use, file_info = should_use_advanced_loading(file_path)
    
    if should_use:
        dialog = AdvancedLoadingDialog(file_path, file_info, parent)
        if dialog.exec_() == QDialog.Accepted:
            # Return a flag indicating this should use advanced editor
            return (None, True)  # No content, but use advanced editor
        return None
    else:
        # Use normal loading for small files
        try:
            with open(file_path, 'r', encoding=file_info.get('encoding', 'utf-8')) as f:
                content = f.read()
                return (content, False)  # Content and use normal editor
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"Failed to open file: {str(e)}")
            return None

def create_advanced_editor_tab(file_path: str, parent=None) -> Optional[QWidget]:
    """
    Create an advanced editor tab for large files
    Returns the widget to be added to a tab, or None if error
    """
    try:
        return AdvancedFileEditor(file_path, parent)
    except Exception as e:
        QMessageBox.critical(parent, "Error", f"Failed to create advanced editor: {str(e)}")
        return None 