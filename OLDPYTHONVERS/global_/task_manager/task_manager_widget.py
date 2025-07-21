"""
Main Task Manager Widget
Integrates all task manager components into a tabbed interface
"""

import psutil
import platform
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QScrollArea, QSplitter, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush, QPainter, QPen

from .system_monitor import SystemMonitor, ProcessMonitor, SystemStats, ProcessInfo
from .ui_components import (
    PerformanceWidget, ProcessTableWidget, DiskTableWidget, 
    NetworkTableWidget, SensorsTreeWidget
)

class TaskManagerWidget(QWidget):
    """Main task manager widget with tabbed interface"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.system_monitor = SystemMonitor(update_interval=1000)
        self.process_monitor = ProcessMonitor(update_interval=3000)
        
        self.init_ui()
        self.connect_signals()
        self.start_monitoring()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3E3E42;
                background: #252526;
                margin-top: -1px;
            }
            QTabBar::tab {
                background: #2D2D30;
                padding: 8px 12px;
                border: 1px solid #3E3E42;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                color: #D4D4D4;
            }
            QTabBar::tab:selected {
                background: #1E1E1E;
                border-bottom: 2px solid #007ACC;
            }
            QTabBar::tab:hover {
                background: #3E3E42;
            }
        """)
        
        # Create tabs
        self.create_performance_tab()
        self.create_processes_tab()
        self.create_disks_tab()
        self.create_network_tab()
        self.create_sensors_tab()
        
        layout.addWidget(self.tabs)
        
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
        self.refresh_btn = QPushButton("Refresh All")
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
        
    def create_performance_tab(self):
        """Create the performance monitoring tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.performance_widget = PerformanceWidget()
        scroll.setWidget(self.performance_widget)
        layout.addWidget(scroll)
        
        self.tabs.addTab(tab, "Performance")
        
    def create_processes_tab(self):
        """Create the processes tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.refresh_processes_btn = QPushButton("Refresh")
        self.refresh_processes_btn.setStyleSheet("""
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
        self.refresh_processes_btn.clicked.connect(self.refresh_processes)
        toolbar.addWidget(self.refresh_processes_btn)
        
        self.end_task_btn = QPushButton("End Task")
        self.end_task_btn.setStyleSheet("""
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
        self.end_task_btn.clicked.connect(self.end_selected_process)
        toolbar.addWidget(self.end_task_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Process table
        self.process_table = ProcessTableWidget()
        layout.addWidget(self.process_table)
        
        self.tabs.addTab(tab, "Processes")
        
    def create_disks_tab(self):
        """Create the disks tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.disk_table = DiskTableWidget()
        layout.addWidget(self.disk_table)
        
        self.tabs.addTab(tab, "Disks")
        
    def create_network_tab(self):
        """Create the network tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.network_table = NetworkTableWidget()
        layout.addWidget(self.network_table)
        
        self.tabs.addTab(tab, "Network")
        
    def create_sensors_tab(self):
        """Create the sensors tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.sensors_tree = SensorsTreeWidget()
        layout.addWidget(self.sensors_tree)
        
        self.tabs.addTab(tab, "Sensors")
        
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
        self.process_table.process_details_requested.connect(self.show_process_details)
        
    def start_monitoring(self):
        """Start all monitoring"""
        self.system_monitor.start_monitoring()
        self.process_monitor.start_monitoring()
        
    def stop_monitoring(self):
        """Stop all monitoring"""
        self.system_monitor.stop_monitoring()
        self.process_monitor.stop_monitoring()
        
    def on_system_stats_updated(self, stats: SystemStats):
        """Handle system stats updates"""
        self.performance_widget.update_stats(stats)
        self.disk_table.update_disks(stats.disk_usage)
        self.network_table.update_network(stats.network_stats)
        self.update_time_label.setText(f"Last update: {stats.timestamp.strftime('%H:%M:%S')}")
        
    def on_processes_updated(self, processes: List[ProcessInfo]):
        """Handle process list updates"""
        self.process_table.update_processes(processes)
        
    def on_monitor_error(self, error_msg: str):
        """Handle monitoring errors"""
        print(f"Task Manager Error: {error_msg}")
        
    def refresh_all(self):
        """Refresh all data"""
        # Force immediate updates
        self.system_monitor._update_stats()
        self.process_monitor._update_processes()
        
    def refresh_processes(self):
        """Refresh process list"""
        self.process_monitor._update_processes()
        
    def end_selected_process(self):
        """End the selected process"""
        selected_items = self.process_table.selectedItems()
        if selected_items:
            try:
                pid = int(self.process_table.item(selected_items[0].row(), 0).text())
                self.terminate_process(pid)
            except Exception:
                pass
                
    def terminate_process(self, pid: int):
        """Terminate a process"""
        try:
            process = psutil.Process(pid)
            reply = QMessageBox.question(
                self, 'Confirm',
                f"Are you sure you want to end process {process.name()} (PID: {pid})?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.process_monitor.terminate_process(pid):
                    QMessageBox.information(self, "Success", f"Process {process.name()} terminated")
                else:
                    QMessageBox.warning(self, "Error", "Failed to terminate process")
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Error", "The process no longer exists")
        except psutil.AccessDenied:
            QMessageBox.warning(self, "Error", "Access denied. Try running as administrator/root")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to terminate process: {str(e)}")
            
    def kill_process(self, pid: int):
        """Force kill a process"""
        try:
            process = psutil.Process(pid)
            reply = QMessageBox.question(
                self, 'Confirm',
                f"Are you sure you want to force kill process {process.name()} (PID: {pid})?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                if self.process_monitor.kill_process(pid):
                    QMessageBox.information(self, "Success", f"Process {process.name()} killed")
                else:
                    QMessageBox.warning(self, "Error", "Failed to kill process")
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Error", "The process no longer exists")
        except psutil.AccessDenied:
            QMessageBox.warning(self, "Error", "Access denied. Try running as administrator/root")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to kill process: {str(e)}")
            
    def show_process_details(self, pid: int):
        """Show detailed process information"""
        try:
            process = psutil.Process(pid)
            info = f"""
            <b>Process Information:</b><br><br>
            <table>
                <tr><td>Name:</td><td>{process.name()}</td></tr>
                <tr><td>PID:</td><td>{pid}</td></tr>
                <tr><td>Status:</td><td>{process.status()}</td></tr>
                <tr><td>CPU %:</td><td>{process.cpu_percent():.1f}%</td></tr>
                <tr><td>Memory:</td><td>{process.memory_info().rss / (1024**2):.1f} MB</td></tr>
                <tr><td>Memory %:</td><td>{(process.memory_info().rss / psutil.virtual_memory().total) * 100:.1f}%</td></tr>
                <tr><td>Create Time:</td><td>{datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
                <tr><td>Executable:</td><td>{process.exe()}</td></tr>
                <tr><td>Command Line:</td><td>{' '.join(process.cmdline())}</td></tr>
            </table>
            """
            msg = QMessageBox()
            msg.setWindowTitle(f"Process Details - {process.name()}")
            msg.setTextFormat(Qt.RichText)
            msg.setText(info)
            msg.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not get process details: {str(e)}")
            
    def closeEvent(self, event):
        """Handle widget close event"""
        self.stop_monitoring()
        super().closeEvent(event) 