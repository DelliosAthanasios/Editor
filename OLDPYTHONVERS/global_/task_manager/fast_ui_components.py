"""
Ultra-Fast UI Components for Task Manager
Optimized for real-time updates with minimal redraws and efficient rendering
"""

import time
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMenu, QAction, QMessageBox,
    QSizePolicy, QFrame, QGridLayout, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect
from PyQt5.QtGui import QFont, QColor, QBrush, QPainter, QPen, QFontMetrics

from .high_performance_monitor import FastSystemStats, FastProcessInfo

class FastPerformanceWidget(QWidget):
    """Ultra-fast performance display with minimal redraws"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_update = 0
        self._update_threshold = 0.1  # Only update if 100ms have passed
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # CPU Section - Single progress bar for performance
        self.cpu_label = QLabel("CPU Usage")
        self.cpu_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #D4D4D4;")
        layout.addWidget(self.cpu_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("Total: %p%")
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                background: #2D2D30;
                height: 24px;
                color: #D4D4D4;
            }
            QProgressBar::chunk {
                background: #007ACC;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.cpu_bar)
        
        # Memory Section
        self.mem_label = QLabel("Memory Usage")
        self.mem_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #D4D4D4;")
        layout.addWidget(self.mem_label)
        
        self.ram_bar = QProgressBar()
        self.ram_bar.setFormat("Physical: %p%")
        self.ram_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                background: #2D2D30;
                height: 24px;
                color: #D4D4D4;
            }
            QProgressBar::chunk {
                background: #007ACC;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.ram_bar)
        
        # Memory details
        self.mem_details = QLabel("0 GB / 0 GB (0% available)")
        self.mem_details.setStyleSheet("color: #D4D4D4; font-size: 11px;")
        layout.addWidget(self.mem_details)
        
        layout.addStretch()
        
    def update_stats(self, stats: FastSystemStats):
        """Update performance display with throttling"""
        current_time = time.time()
        if current_time - self._last_update < self._update_threshold:
            return  # Skip update if too frequent
            
        self._last_update = current_time
        
        # Update CPU
        cpu_value = int(stats.cpu_percent)
        if self.cpu_bar.value() != cpu_value:
            self.cpu_bar.setValue(cpu_value)
        
        # Update Memory
        mem_value = int(stats.memory_percent)
        if self.ram_bar.value() != mem_value:
            self.ram_bar.setValue(mem_value)
        
        # Update memory details
        used_gb = stats.memory_used / (1024 ** 3)
        total_gb = stats.memory_total / (1024 ** 3)
        available_gb = stats.memory_available / (1024 ** 3)
        
        details_text = f"{used_gb:.1f} GB / {total_gb:.1f} GB ({available_gb:.1f} GB available)"
        if self.mem_details.text() != details_text:
            self.mem_details.setText(details_text)

class FastProcessTableWidget(QTableWidget):
    """Ultra-fast process table with efficient updates"""
    
    process_terminate_requested = pyqtSignal(int)  # PID
    process_kill_requested = pyqtSignal(int)  # PID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_update = 0
        self._update_threshold = 0.5  # Only update if 500ms have passed
        self._process_cache = {}
        self.init_ui()
        
    def init_ui(self):
        self.setColumnCount(5)  # Reduced columns for performance
        self.setHorizontalHeaderLabels(["PID", "Name", "Memory", "Memory %", "Status"])
        
        # Configure headers
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(False)  # Disable sorting for performance
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Styling
        self.setStyleSheet("""
            QTableWidget {
                background: #2D2D30;
                border: 1px solid #3E3E42;
                gridline-color: #3E3E42;
                selection-background-color: #37373D;
                selection-color: #FFFFFF;
                color: #D4D4D4;
            }
            QHeaderView::section {
                background: #2D2D30;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #3E3E42;
                color: #D4D4D4;
            }
        """)
        
    def update_processes(self, processes: List[FastProcessInfo]):
        """Update process table efficiently"""
        current_time = time.time()
        if current_time - self._last_update < self._update_threshold:
            return  # Skip update if too frequent
            
        self._last_update = current_time
        
        # Only update if there are significant changes
        current_pids = set()
        for row in range(self.rowCount()):
            pid_item = self.item(row, 0)
            if pid_item:
                current_pids.add(int(pid_item.text()))
        
        new_pids = {p.pid for p in processes}
        
        # If processes haven't changed significantly, don't update
        if len(current_pids.symmetric_difference(new_pids)) < 3:
            return
            
        # Update table
        self.setRowCount(len(processes))
        
        for row, process in enumerate(processes):
            # PID
            self.setItem(row, 0, QTableWidgetItem(str(process.pid)))
            
            # Name
            name_item = QTableWidgetItem(process.name)
            self.setItem(row, 1, name_item)
            
            # Memory
            mem_mb = process.memory_rss / (1024 ** 2)
            mem_item = QTableWidgetItem(f"{mem_mb:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 2, mem_item)
            
            # Memory %
            mem_percent_item = QTableWidgetItem(f"{process.memory_percent:.1f}")
            mem_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if process.memory_percent > 10:
                mem_percent_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif process.memory_percent > 5:
                mem_percent_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.setItem(row, 3, mem_percent_item)
            
            # Status
            self.setItem(row, 4, QTableWidgetItem(process.status))
        
    def _show_context_menu(self, position):
        """Show context menu for selected process"""
        selected_row = self.rowAt(position.y())
        if selected_row >= 0:
            try:
                pid = int(self.item(selected_row, 0).text())
                menu = QMenu(self)
                
                # End Process
                end_action = QAction("End Process", self)
                end_action.triggered.connect(lambda: self.process_terminate_requested.emit(pid))
                menu.addAction(end_action)
                
                # Kill Process
                kill_action = QAction("Kill Process", self)
                kill_action.triggered.connect(lambda: self.process_kill_requested.emit(pid))
                menu.addAction(kill_action)
                
                menu.exec_(self.viewport().mapToGlobal(position))
            except Exception:
                pass

class FastTaskManagerWidget(QWidget):
    """Ultra-fast task manager widget with minimal lag"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.init_monitors()
        self.connect_signals()
        self.start_monitoring()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Performance widget (always visible)
        self.performance_widget = FastPerformanceWidget()
        layout.addWidget(self.performance_widget)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #3E3E42;")
        layout.addWidget(separator)
        
        # Process table
        self.process_table = FastProcessTableWidget()
        layout.addWidget(self.process_table)
        
        # Status bar
        self.status_bar = QFrame()
        self.status_bar.setStyleSheet("background: #2D2D30; border-top: 1px solid #3E3E42;")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        self.update_time_label = QLabel("Last update: --:--:--")
        self.update_time_label.setStyleSheet("color: #D4D4D4; font-size: 11px;")
        status_layout.addWidget(self.update_time_label)
        
        status_layout.addStretch()
        
        # Control buttons
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3E3E42;
                border: 1px solid #3E3E42;
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 80px;
                color: #D4D4D4;
            }
            QPushButton:hover {
                background: #4E4E52;
            }
            QPushButton:pressed {
                background: #2D2D30;
            }
        """)
        self.refresh_btn.clicked.connect(self.refresh_all)
        status_layout.addWidget(self.refresh_btn)
        
        layout.addWidget(self.status_bar)
        
    def init_monitors(self):
        """Initialize high-performance monitors with proper fallback"""
        try:
            from .high_performance_monitor import HighPerformanceMonitor, FastProcessMonitor
            
            # System monitor with very fast updates
            self.system_monitor = HighPerformanceMonitor(update_interval=500)  # 500ms updates for stability
            
            # Process monitor
            self.process_monitor = FastProcessMonitor(update_interval=2000)  # 2s updates for stability
            
            print("Using high-performance monitors")
            
        except ImportError as e:
            print(f"High-performance monitors not available: {e}")
            # Fallback to psutil-based monitors
            try:
                from .system_monitor import SystemMonitor, ProcessMonitor
                self.system_monitor = SystemMonitor(update_interval=500)
                self.process_monitor = ProcessMonitor(update_interval=2000)
                print("Using standard psutil-based monitors")
            except ImportError as e2:
                print(f"Standard monitors also not available: {e2}")
                # Final fallback - create dummy monitors
                self._create_dummy_monitors()
        
    def _create_dummy_monitors(self):
        """Create dummy monitors when no monitoring is available"""
        from PyQt5.QtCore import QObject, pyqtSignal, QTimer
        
        class DummySystemMonitor(QObject):
            stats_updated = pyqtSignal(object)
            error_occurred = pyqtSignal(str)
            
            def __init__(self, update_interval=1000):
                super().__init__()
                self._timer = QTimer()
                self._timer.timeout.connect(self._emit_dummy_stats)
                self._timer.start(update_interval)
            
            def _emit_dummy_stats(self):
                from .high_performance_monitor import FastSystemStats
                stats = FastSystemStats(
                    cpu_percent=0.0,
                    cpu_per_core=[0.0],
                    memory_percent=0.0,
                    memory_used=0,
                    memory_total=0,
                    memory_available=0,
                    timestamp=time.time()
                )
                self.stats_updated.emit(stats)
            
            def start_monitoring(self):
                pass
            
            def stop_monitoring(self):
                self._timer.stop()
        
        class DummyProcessMonitor(QObject):
            processes_updated = pyqtSignal(list)
            error_occurred = pyqtSignal(str)
            
            def __init__(self, update_interval=2000):
                super().__init__()
                self._timer = QTimer()
                self._timer.timeout.connect(self._emit_dummy_processes)
                self._timer.start(update_interval)
            
            def _emit_dummy_processes(self):
                from .high_performance_monitor import FastProcessInfo
                processes = [
                    FastProcessInfo(
                        pid=0,
                        name="No monitoring available",
                        cpu_percent=0.0,
                        memory_rss=0,
                        memory_percent=0.0,
                        status="Unknown"
                    )
                ]
                self.processes_updated.emit(processes)
            
            def start(self):
                pass
            
            def stop_monitoring(self):
                self._timer.stop()
            
            def terminate_process(self, pid):
                return False
            
            def kill_process(self, pid):
                return False
        
        self.system_monitor = DummySystemMonitor(update_interval=1000)
        self.process_monitor = DummyProcessMonitor(update_interval=2000)
        print("Using dummy monitors - no system monitoring available")
    
    def connect_signals(self):
        """Connect all signal handlers"""
        # System monitor signals
        self.system_monitor.stats_updated.connect(self.on_system_stats_updated)
        self.system_monitor.error_occurred.connect(self.on_monitor_error)
        
        # Process monitor signals
        self.process_monitor.processes_updated.connect(self.on_processes_updated)
        self.process_monitor.error_occurred.connect(self.on_monitor_error)
        
        # Process table signals
        self.process_table.process_terminate_requested.connect(self.terminate_process)
        self.process_table.process_kill_requested.connect(self.kill_process)
        
    def start_monitoring(self):
        """Start all monitoring"""
        self.system_monitor.start_monitoring()
        self.process_monitor.start()  # QThread uses start() method
        
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.system_monitor.stop_monitoring()
        self.process_monitor.stop_monitoring()
        
    def on_system_stats_updated(self, stats):
        """Handle system stats updates"""
        self.performance_widget.update_stats(stats)
        
        # Update timestamp
        if hasattr(stats, 'timestamp'):
            if isinstance(stats.timestamp, float):
                timestamp_str = time.strftime('%H:%M:%S', time.localtime(stats.timestamp))
            else:
                timestamp_str = stats.timestamp.strftime('%H:%M:%S')
            self.update_time_label.setText(f"Last update: {timestamp_str}")
        
    def on_processes_updated(self, processes):
        """Handle process list updates"""
        self.process_table.update_processes(processes)
        
    def on_monitor_error(self, error_msg: str):
        """Handle monitoring errors"""
        print(f"Fast Task Manager Error: {error_msg}")
        
    def refresh_all(self):
        """Refresh all data"""
        # Force immediate updates
        if hasattr(self.system_monitor, '_update_stats'):
            self.system_monitor._update_stats()
        
    def terminate_process(self, pid: int):
        """Terminate a process"""
        try:
            reply = QMessageBox.question(
                self, 'Confirm',
                f"Are you sure you want to end process (PID: {pid})?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.process_monitor.terminate_process(pid):
                    QMessageBox.information(self, "Success", f"Process terminated")
                else:
                    QMessageBox.warning(self, "Error", "Failed to terminate process")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to terminate process: {str(e)}")
            
    def kill_process(self, pid: int):
        """Force kill a process"""
        try:
            reply = QMessageBox.question(
                self, 'Confirm',
                f"Are you sure you want to force kill process (PID: {pid})?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.process_monitor.kill_process(pid):
                    QMessageBox.information(self, "Success", f"Process killed")
                else:
                    QMessageBox.warning(self, "Error", "Failed to kill process")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to kill process: {str(e)}")
            
    def closeEvent(self, event):
        """Handle widget close event"""
        self.stop_monitoring()
        super().closeEvent(event) 