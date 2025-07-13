"""
UI Components for Task Manager
Optimized widgets for displaying system information
"""

import psutil
import platform
import subprocess
from datetime import datetime
from typing import Dict, List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMenu, QAction, QMessageBox,
    QSizePolicy, QScrollArea, QTreeWidget, QTreeWidgetItem, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush, QPainter, QPen, QFontMetrics

from .system_monitor import SystemStats, ProcessInfo

class PerformanceWidget(QWidget):
    """Optimized performance display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self._last_update = None
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # CPU Section
        self.cpu_group = self._create_section("CPU Usage")
        self.cpu_bar = self._create_progress_bar("Total: %p%")
        self.cpu_group.layout().addWidget(self.cpu_bar)
        self.cpu_cores_layout = QVBoxLayout()
        self.cpu_group.layout().addLayout(self.cpu_cores_layout)
        layout.addWidget(self.cpu_group)
        
        # Memory Section
        self.mem_group = self._create_section("Memory Usage")
        self.ram_bar = self._create_progress_bar("Physical: %p%")
        self.mem_group.layout().addWidget(self.ram_bar)
        self.swap_bar = self._create_progress_bar("Swap: %p%")
        self.mem_group.layout().addWidget(self.swap_bar)
        layout.addWidget(self.mem_group)
        
        # Disk Section
        self.disk_group = self._create_section("Disk Usage")
        self.disk_bar = self._create_progress_bar("Main Disk: %p%")
        self.disk_group.layout().addWidget(self.disk_bar)
        layout.addWidget(self.disk_group)
        
        # Network Section
        self.net_group = self._create_section("Network")
        self.net_stats = QLabel("Sent: 0 MB/s | Received: 0 MB/s")
        self.net_group.layout().addWidget(self.net_stats)
        layout.addWidget(self.net_group)
        
    def _create_section(self, title: str) -> QWidget:
        """Create a section widget with title"""
        group = QWidget()
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(title)
        label.setStyleSheet("font-size: 14px; font-weight: bold; color: #D4D4D4;")
        group_layout.addWidget(label)
        
        return group
        
    def _create_progress_bar(self, format_str: str) -> QProgressBar:
        """Create a styled progress bar"""
        bar = QProgressBar()
        bar.setFormat(format_str)
        bar.setStyleSheet("""
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
        return bar
        
    def update_stats(self, stats: SystemStats):
        """Update performance display with new stats"""
        if self._last_update == stats.timestamp:
            return  # Avoid duplicate updates
            
        self._last_update = stats.timestamp
        
        # Update CPU
        self.cpu_bar.setValue(int(stats.cpu_percent))
        self._update_cpu_cores(stats.cpu_per_core)
        
        # Update Memory
        self.ram_bar.setValue(int(stats.memory_percent))
        self.swap_bar.setValue(int(stats.swap_percent))
        
        # Update Disk (use first disk found)
        if stats.disk_usage:
            first_disk = next(iter(stats.disk_usage.values()), None)
            if first_disk:
                self.disk_bar.setValue(int(first_disk['percent']))
        
        # Update Network
        if stats.network_stats and 'total' in stats.network_stats:
            total = stats.network_stats['total']
            sent_mb = total['sent_rate'] / (1024 * 1024)
            recv_mb = total['recv_rate'] / (1024 * 1024)
            self.net_stats.setText(f"Sent: {sent_mb:.1f} MB/s | Received: {recv_mb:.1f} MB/s")
            
    def _update_cpu_cores(self, cpu_per_core: List[float]):
        """Update individual CPU core displays"""
        # Clear existing core widgets
        while self.cpu_cores_layout.count():
            child = self.cpu_cores_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add core widgets
        for i, percent in enumerate(cpu_per_core):
            core_widget = QWidget()
            core_layout = QHBoxLayout(core_widget)
            core_layout.setContentsMargins(0, 0, 0, 0)
            core_layout.setSpacing(10)
            
            core_label = QLabel(f"Core {i+1}")
            core_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            
            core_bar = QProgressBar()
            core_bar.setValue(int(percent))
            core_bar.setFormat(f"%p%")
            core_bar.setStyleSheet("QProgressBar { height: 18px; }")
            core_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            core_layout.addWidget(core_label)
            core_layout.addWidget(core_bar)
            
            self.cpu_cores_layout.addWidget(core_widget)

class ProcessTableWidget(QTableWidget):
    """Optimized process table with efficient updates"""
    
    process_terminate_requested = pyqtSignal(int)  # PID
    process_kill_requested = pyqtSignal(int)  # PID
    process_details_requested = pyqtSignal(int)  # PID
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self._process_cache = {}
        
    def init_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "Memory", "Memory %", "Status"])
        
        # Configure headers
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
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
        
    def update_processes(self, processes: List[ProcessInfo]):
        """Update process table efficiently"""
        self.setSortingEnabled(False)
        
        # Only update if there are significant changes
        current_pids = set()
        for row in range(self.rowCount()):
            pid_item = self.item(row, 0)
            if pid_item:
                current_pids.add(int(pid_item.text()))
        
        new_pids = {p.pid for p in processes}
        
        # If processes haven't changed significantly, don't update
        if len(current_pids.symmetric_difference(new_pids)) < 5:
            return
            
        self.setRowCount(len(processes))
        total_memory = psutil.virtual_memory().total
        
        for row, process in enumerate(processes):
            # PID
            self.setItem(row, 0, QTableWidgetItem(str(process.pid)))
            
            # Name
            name_item = QTableWidgetItem(process.name)
            self.setItem(row, 1, name_item)
            
            # CPU %
            cpu_item = QTableWidgetItem(f"{process.cpu_percent:.1f}")
            cpu_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if process.cpu_percent > 50:
                cpu_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif process.cpu_percent > 20:
                cpu_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.setItem(row, 2, cpu_item)
            
            # Memory
            mem_mb = process.memory_rss / (1024 ** 2)
            mem_item = QTableWidgetItem(f"{mem_mb:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 3, mem_item)
            
            # Memory %
            mem_percent_item = QTableWidgetItem(f"{process.memory_percent:.1f}")
            mem_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if process.memory_percent > 10:
                mem_percent_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif process.memory_percent > 5:
                mem_percent_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.setItem(row, 4, mem_percent_item)
            
            # Status
            self.setItem(row, 5, QTableWidgetItem(process.status))
            
        self.setSortingEnabled(True)
        
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
                
                menu.addSeparator()
                
                # Process Details
                details_action = QAction("Process Details", self)
                details_action.triggered.connect(lambda: self.process_details_requested.emit(pid))
                menu.addAction(details_action)
                
                menu.exec_(self.viewport().mapToGlobal(position))
            except Exception:
                pass

class DiskTableWidget(QTableWidget):
    """Optimized disk usage table"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels([
            "Device", "Mountpoint", "Type", "Total", "Used", "Free", "Usage %"
        ])
        
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        
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
        
    def update_disks(self, disk_usage: Dict[str, Dict]):
        """Update disk table"""
        self.setSortingEnabled(False)
        self.setRowCount(len(disk_usage))
        
        for row, (device, info) in enumerate(disk_usage.items()):
            self.setItem(row, 0, QTableWidgetItem(device))
            self.setItem(row, 1, QTableWidgetItem(info['mountpoint']))
            self.setItem(row, 2, QTableWidgetItem(info['fstype']))
            
            # Total
            total_gb = info['total'] / (1024 ** 3)
            self.setItem(row, 3, QTableWidgetItem(f"{total_gb:.1f} GB"))
            
            # Used
            used_gb = info['used'] / (1024 ** 3)
            self.setItem(row, 4, QTableWidgetItem(f"{used_gb:.1f} GB"))
            
            # Free
            free_gb = info['free'] / (1024 ** 3)
            self.setItem(row, 5, QTableWidgetItem(f"{free_gb:.1f} GB"))
            
            # Usage %
            usage_item = QTableWidgetItem(f"{info['percent']}%")
            if info['percent'] > 90:
                usage_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif info['percent'] > 75:
                usage_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.setItem(row, 6, usage_item)
            
        self.setSortingEnabled(True)

class NetworkTableWidget(QTableWidget):
    """Optimized network table"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels([
            "Interface", "Sent (MB)", "Recv (MB)", "Packets Sent", "Packets Recv", "Status"
        ])
        
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.verticalHeader().setVisible(False)
        self.setSortingEnabled(True)
        
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
        
    def update_network(self, network_stats: Dict[str, Dict]):
        """Update network table"""
        self.setSortingEnabled(False)
        
        # Filter out 'total' entry and get interface stats
        interfaces = {k: v for k, v in network_stats.items() if k != 'total'}
        self.setRowCount(len(interfaces))
        
        for row, (name, data) in enumerate(interfaces.items()):
            self.setItem(row, 0, QTableWidgetItem(name))
            self.setItem(row, 1, QTableWidgetItem(f"{data['sent_total']/(1024**2):.1f}"))
            self.setItem(row, 2, QTableWidgetItem(f"{data['recv_total']/(1024**2):.1f}"))
            self.setItem(row, 3, QTableWidgetItem(str(data['packets_sent'])))
            self.setItem(row, 4, QTableWidgetItem(str(data['packets_recv'])))
            
            status = "Active" if data['active'] else "Inactive"
            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(QBrush(QColor(100, 255, 100)))
            self.setItem(row, 5, status_item)
            
        self.setSortingEnabled(True)

class SensorsTreeWidget(QTreeWidget):
    """Optimized sensors display widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self._last_update = None
        
    def init_ui(self):
        self.setHeaderLabels(["Sensor", "Value", "Min", "Max"])
        self.setColumnCount(4)
        self.setFont(QFont("Segoe UI", 10))
        self.setMinimumWidth(550)
        
        # Styling
        self.setStyleSheet("""
            QTreeWidget {
                background: #252526;
                color: #D4D4D4;
                border: 1px solid #3E3E42;
                font-size: 11px;
            }
            QTreeWidget::item {
                background: #252526;
            }
            QTreeWidget::item:selected {
                background: #37373D;
                color: #FFFFFF;
            }
        """)
        
    def update_sensors(self, sensors_data: Optional[Dict] = None):
        """Update sensors display"""
        if self._last_update == sensors_data:
            return
            
        self._last_update = sensors_data
        self.clear()
        
        try:
            if sensors_data is None:
                # Try to get sensors data
                try:
                    if hasattr(psutil, "sensors_temperatures"):
                        sensors_data = psutil.sensors_temperatures(fahrenheit=False)
                    else:
                        sensors_data = {}
                except Exception:
                    sensors_data = {}
            
            if not sensors_data:
                root = QTreeWidgetItem(self, ["No sensor data available"])
                self.addTopLevelItem(root)
                return
                
            for chip_name, entries in sensors_data.items():
                chip_root = QTreeWidgetItem(self, [chip_name])
                chip_root.setExpanded(True)
                
                for entry in entries:
                    label = getattr(entry, "label", "") or ""
                    current = getattr(entry, "current", "")
                    min_val = getattr(entry, "min", "")
                    max_val = getattr(entry, "max", "")
                    
                    item = QTreeWidgetItem(chip_root, [
                        str(label),
                        f"{current}°C" if current else "",
                        f"{min_val}°C" if min_val else "",
                        f"{max_val}°C" if max_val else ""
                    ])
                    
        except Exception:
            self.clear()
            root = QTreeWidgetItem(self, ["Error: Could not read sensors"])
            self.addTopLevelItem(root) 