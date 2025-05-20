import sys
import psutil
from PyQt5.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel, QProgressBar,
                             QHBoxLayout, QTableWidget, QTableWidgetItem, QMainWindow, QHeaderView,
                             QPushButton, QMenu, QAction, QMessageBox, QInputDialog)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QBrush
import platform
import subprocess
from datetime import datetime

DARK_STYLE = """
QMainWindow {
    background-color: #1E1E1E;
}
QWidget {
    background-color: #252526;
    color: #D4D4D4;
    font-family: Segoe UI;
    font-size: 12px;
    border: none;
}
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
}
QTabBar::tab:selected {
    background: #1E1E1E;
    border-bottom: 2px solid #007ACC;
}
QTabBar::tab:hover {
    background: #3E3E42;
}
QProgressBar {
    text-align: center;
    border: 1px solid #3E3E42;
    border-radius: 4px;
    background: #2D2D30;
    height: 22px;
}
QProgressBar::chunk {
    background: #007ACC;
    border-radius: 3px;
}
QTableWidget {
    background: #2D2D30;
    border: 1px solid #3E3E42;
    gridline-color: #3E3E42;
    selection-background-color: #37373D;
    selection-color: #FFFFFF;
}
QHeaderView::section {
    background: #2D2D30;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #3E3E42;
}
QLabel {
    color: #D4D4D4;
}
QPushButton {
    background: #3E3E42;
    border: 1px solid #3E3E42;
    border-radius: 4px;
    padding: 5px 10px;
    min-width: 80px;
}
QPushButton:hover {
    background: #4E4E52;
}
QPushButton:pressed {
    background: #2D2D30;
}
QMenu {
    background: #252526;
    border: 1px solid #3E3E42;
}
QMenu::item:selected {
    background: #37373D;
}
"""

class ProcessUpdaterThread(QThread):
    update_signal = pyqtSignal(list)
    
    def run(self):
        processes = sorted(
            [(p.pid, p.name(), p.cpu_percent(), p.memory_info().rss) 
             for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info'])],
            key=lambda x: x[2], reverse=True
        )
        self.update_signal.emit(processes)

class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Manager")
        self.setGeometry(100, 100, 1024, 768)
        
        self.setStyleSheet(DARK_STYLE)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.performance_tab = QWidget()
        self.processes_tab = QWidget()
        self.services_tab = QWidget()
        self.disk_tab = QWidget()
        self.network_tab = QWidget()

        self.tabs.addTab(self.performance_tab, "Performance")
        self.tabs.addTab(self.processes_tab, "Processes")
        self.tabs.addTab(self.services_tab, "Services")
        self.tabs.addTab(self.disk_tab, "Disks")
        self.tabs.addTab(self.network_tab, "Network")

        self.init_performance_tab()
        self.init_processes_tab()
        self.init_services_tab()
        self.init_disk_tab()
        self.init_network_tab()

        # Status Bar
        self.status_bar = self.statusBar()
        self.update_time_label = QLabel()
        self.status_bar.addPermanentWidget(self.update_time_label)

        # Timers
        self.fast_timer = QTimer()
        self.fast_timer.timeout.connect(self.update_fast_stats)
        self.fast_timer.start(1000)

        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.update_slow_stats)
        self.slow_timer.start(5000)

        self.prev_net = psutil.net_io_counters()
        self.process_updater = ProcessUpdaterThread()
        self.process_updater.update_signal.connect(self.update_process_table)

        # Context menu for processes
        self.process_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.process_table.customContextMenuRequested.connect(self.show_process_context_menu)

    def init_performance_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # CPU Section
        cpu_group = QWidget()
        cpu_layout = QVBoxLayout()
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        self.cpu_label = QLabel("CPU Usage")
        self.cpu_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        cpu_layout.addWidget(self.cpu_label)
        
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setFormat("Total: %p%")
        self.cpu_bar.setStyleSheet("QProgressBar { height: 24px; }")
        cpu_layout.addWidget(self.cpu_bar)
        
        self.cpu_cores_layout = QVBoxLayout()
        cpu_layout.addLayout(self.cpu_cores_layout)
        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)

        # Memory Section
        mem_group = QWidget()
        mem_layout = QVBoxLayout()
        mem_layout.setContentsMargins(0, 0, 0, 0)
        self.mem_label = QLabel("Memory Usage")
        self.mem_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        mem_layout.addWidget(self.mem_label)
        
        self.ram_bar = QProgressBar()
        self.ram_bar.setFormat("Physical: %p%")
        self.ram_bar.setStyleSheet("QProgressBar { height: 24px; }")
        mem_layout.addWidget(self.ram_bar)
        
        if hasattr(psutil, 'swap_memory'):
            self.swap_bar = QProgressBar()
            self.swap_bar.setFormat("Swap: %p%")
            self.swap_bar.setStyleSheet("QProgressBar { height: 24px; }")
            mem_layout.addWidget(self.swap_bar)
        
        mem_group.setLayout(mem_layout)
        layout.addWidget(mem_group)

        # Disk Section
        disk_group = QWidget()
        disk_layout = QVBoxLayout()
        disk_layout.setContentsMargins(0, 0, 0, 0)
        self.disk_label = QLabel("Disk Usage")
        self.disk_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        disk_layout.addWidget(self.disk_label)
        
        self.disk_bar = QProgressBar()
        self.disk_bar.setFormat("Main Disk: %p%")
        self.disk_bar.setStyleSheet("QProgressBar { height: 24px; }")
        disk_layout.addWidget(self.disk_bar)
        
        disk_group.setLayout(disk_layout)
        layout.addWidget(disk_group)

        # Network Section
        net_group = QWidget()
        net_layout = QVBoxLayout()
        net_layout.setContentsMargins(0, 0, 0, 0)
        self.net_label = QLabel("Network")
        self.net_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        net_layout.addWidget(self.net_label)
        
        self.net_stats = QLabel("Sent: 0 MB | Received: 0 MB")
        net_layout.addWidget(self.net_stats)
        
        net_group.setLayout(net_layout)
        layout.addWidget(net_group)

        self.performance_tab.setLayout(layout)

    def init_processes_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.force_process_refresh)
        self.end_task_btn = QPushButton("End Task")
        self.end_task_btn.clicked.connect(self.end_selected_process)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.end_task_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Process Table
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(6)
        self.process_table.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "Memory", "Memory %", "Status"])
        self.process_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.process_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.process_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.process_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.process_table.verticalHeader().setVisible(False)
        self.process_table.setSortingEnabled(True)
        self.process_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.process_table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.process_table)
        
        self.processes_tab.setLayout(layout)

    def init_services_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.refresh_services_btn = QPushButton("Refresh")
        self.refresh_services_btn.clicked.connect(self.update_services)
        toolbar.addWidget(self.refresh_services_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Service Table
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(4)
        self.service_table.setHorizontalHeaderLabels(["Service", "Status", "Description", "PID"])
        self.service_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.service_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.service_table.verticalHeader().setVisible(False)
        self.service_table.setSortingEnabled(True)
        layout.addWidget(self.service_table)
        
        if platform.system() != 'Linux':
            self.service_table.setRowCount(1)
            self.service_table.setItem(0, 0, QTableWidgetItem("Unavailable"))
            self.service_table.setItem(0, 1, QTableWidgetItem("Only supported on Linux"))
        
        self.services_tab.setLayout(layout)

    def init_disk_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Disk Table
        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(6)
        self.disk_table.setHorizontalHeaderLabels(["Device", "Mountpoint", "Type", "Total", "Used", "Usage %"])
        self.disk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.disk_table.verticalHeader().setVisible(False)
        self.disk_table.setSortingEnabled(True)
        layout.addWidget(self.disk_table)
        
        self.disk_tab.setLayout(layout)

    def init_network_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Network Table
        self.network_table = QTableWidget()
        self.network_table.setColumnCount(6)
        self.network_table.setHorizontalHeaderLabels(["Interface", "Sent (MB)", "Recv (MB)", "Packets Sent", "Packets Recv", "Status"])
        self.network_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.network_table.verticalHeader().setVisible(False)
        self.network_table.setSortingEnabled(True)
        layout.addWidget(self.network_table)
        
        self.network_tab.setLayout(layout)

    def update_fast_stats(self):
        # CPU
        cpu_percent = psutil.cpu_percent()
        self.cpu_bar.setValue(int(cpu_percent))
        
        # CPU Cores
        self.clear_layout(self.cpu_cores_layout)
        if hasattr(psutil, 'cpu_percent'):
            per_cpu = psutil.cpu_percent(percpu=True)
            for i, percent in enumerate(per_cpu):
                core_label = QLabel(f"Core {i+1}")
                core_bar = QProgressBar()
                core_bar.setValue(int(percent))
                core_bar.setFormat(f"%p%")
                core_bar.setStyleSheet("QProgressBar { height: 18px; }")
                
                core_layout = QHBoxLayout()
                core_layout.addWidget(core_label, 1)
                core_layout.addWidget(core_bar, 4)
                self.cpu_cores_layout.addLayout(core_layout)

        # Memory
        mem = psutil.virtual_memory()
        self.ram_bar.setValue(int(mem.percent))
        
        if hasattr(psutil, 'swap_memory'):
            swap = psutil.swap_memory()
            self.swap_bar.setValue(int(swap.percent))

        # Network
        current_net = psutil.net_io_counters()
        sent = (current_net.bytes_sent - self.prev_net.bytes_sent) / (1024 ** 2)
        recv = (current_net.bytes_recv - self.prev_net.bytes_recv) / (1024 ** 2)
        self.net_stats.setText(f"Sent: {sent:.1f} MB/s | Received: {recv:.1f} MB/s")
        self.prev_net = current_net

        # Update timestamp
        self.update_time_label.setText(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

    def update_slow_stats(self):
        self.update_disks()
        self.update_network()
        if platform.system() == 'Linux':
            self.update_services()
        
        # Start process update in background thread
        if not self.process_updater.isRunning():
            self.process_updater.start()

    def update_process_table(self, processes):
        self.process_table.setSortingEnabled(False)
        self.process_table.setRowCount(len(processes))
        
        for row, (pid, name, cpu, mem_bytes) in enumerate(processes):
            # PID
            self.process_table.setItem(row, 0, QTableWidgetItem(str(pid)))
            
            # Name
            name_item = QTableWidgetItem(name)
            self.process_table.setItem(row, 1, name_item)
            
            # CPU %
            cpu_item = QTableWidgetItem(f"{cpu:.1f}")
            cpu_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if cpu > 50:
                cpu_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif cpu > 20:
                cpu_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.process_table.setItem(row, 2, cpu_item)
            
            # Memory
            mem_mb = mem_bytes / (1024 ** 2)
            mem_item = QTableWidgetItem(f"{mem_mb:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.process_table.setItem(row, 3, mem_item)
            
            # Memory %
            mem_percent = (mem_bytes / psutil.virtual_memory().total) * 100
            mem_percent_item = QTableWidgetItem(f"{mem_percent:.1f}")
            mem_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if mem_percent > 10:
                mem_percent_item.setForeground(QBrush(QColor(255, 100, 100)))
            elif mem_percent > 5:
                mem_percent_item.setForeground(QBrush(QColor(255, 200, 100)))
            self.process_table.setItem(row, 4, mem_percent_item)
            
            # Status (simplified)
            try:
                status = "Running" if psutil.Process(pid).status() == 'running' else "Other"
            except:
                status = "N/A"
            self.process_table.setItem(row, 5, QTableWidgetItem(status))
        
        self.process_table.setSortingEnabled(True)

    def update_services(self):
        try:
            if platform.system() == 'Linux':
                output = subprocess.check_output(['systemctl', 'list-units', '--type=service', '--no-pager', '--all'], text=True)
                services = [line.split(maxsplit=4) for line in output.splitlines()[1:] if line.strip()]
                
                self.service_table.setSortingEnabled(False)
                self.service_table.setRowCount(len(services))
                
                for i, parts in enumerate(services):
                    if len(parts) >= 5:
                        service = parts[0]
                        status = parts[3]
                        description = parts[4]
                        
                        # Get PID if available
                        try:
                            pid_output = subprocess.check_output(['systemctl', 'show', service, '--property=MainPID'], text=True)
                            pid = pid_output.split('=')[1].strip()
                        except:
                            pid = "N/A"
                        
                        self.service_table.setItem(i, 0, QTableWidgetItem(service))
                        self.service_table.setItem(i, 1, QTableWidgetItem(status))
                        self.service_table.setItem(i, 2, QTableWidgetItem(description))
                        self.service_table.setItem(i, 3, QTableWidgetItem(pid))
                
                self.service_table.setSortingEnabled(True)
        except Exception as e:
            self.service_table.setRowCount(1)
            self.service_table.setItem(0, 0, QTableWidgetItem("Error"))
            self.service_table.setItem(0, 1, QTableWidgetItem(str(e)))

    def update_disks(self):
        partitions = psutil.disk_partitions()
        self.disk_table.setSortingEnabled(False)
        self.disk_table.setRowCount(len(partitions))
        
        row = 0
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
                
                # Device
                self.disk_table.setItem(row, 0, QTableWidgetItem(part.device))
                
                # Mountpoint
                self.disk_table.setItem(row, 1, QTableWidgetItem(part.mountpoint))
                
                # Type
                self.disk_table.setItem(row, 2, QTableWidgetItem(part.fstype))
                
                # Total
                total_gb = usage.total / (1024 ** 3)
                self.disk_table.setItem(row, 3, QTableWidgetItem(f"{total_gb:.1f} GB"))
                
                # Used
                used_gb = usage.used / (1024 ** 3)
                self.disk_table.setItem(row, 4, QTableWidgetItem(f"{used_gb:.1f} GB"))
                
                # Usage %
                usage_item = QTableWidgetItem(f"{usage.percent}%")
                if usage.percent > 90:
                    usage_item.setForeground(QBrush(QColor(255, 100, 100)))
                elif usage.percent > 75:
                    usage_item.setForeground(QBrush(QColor(255, 200, 100)))
                self.disk_table.setItem(row, 5, usage_item)
                
                row += 1
            except (PermissionError, psutil.AccessDenied):
                continue
        
        self.disk_table.setSortingEnabled(True)

    def update_network(self):
        interfaces = psutil.net_io_counters(pernic=True)
        self.network_table.setSortingEnabled(False)
        self.network_table.setRowCount(len(interfaces))
        
        for row, (name, data) in enumerate(interfaces.items()):
            # Interface
            self.network_table.setItem(row, 0, QTableWidgetItem(name))
            
            # Sent MB
            self.network_table.setItem(row, 1, QTableWidgetItem(f"{data.bytes_sent/(1024**2):.1f}"))
            
            # Received MB
            self.network_table.setItem(row, 2, QTableWidgetItem(f"{data.bytes_recv/(1024**2):.1f}"))
            
            # Packets Sent
            self.network_table.setItem(row, 3, QTableWidgetItem(str(data.packets_sent)))
            
            # Packets Received
            self.network_table.setItem(row, 4, QTableWidgetItem(str(data.packets_recv)))
            
            # Status
            status = "Active" if data.bytes_sent + data.bytes_recv > 0 else "Inactive"
            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(QBrush(QColor(100, 255, 100)))
            self.network_table.setItem(row, 5, status_item)
        
        self.network_table.setSortingEnabled(True)

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def force_process_refresh(self):
        if not self.process_updater.isRunning():
            self.process_updater.start()

    def show_process_context_menu(self, position):
        selected_row = self.process_table.rowAt(position.y())
        if selected_row >= 0:
            pid = int(self.process_table.item(selected_row, 0).text())
            
            menu = QMenu()
            
            end_action = QAction("End Process", self)
            end_action.triggered.connect(lambda: self.end_process(pid))
            menu.addAction(end_action)
            
            details_action = QAction("Process Details", self)
            details_action.triggered.connect(lambda: self.show_process_details(pid))
            menu.addAction(details_action)
            
            menu.exec_(self.process_table.viewport().mapToGlobal(position))

    def end_selected_process(self):
        selected_items = self.process_table.selectedItems()
        if selected_items:
            pid = int(self.process_table.item(selected_items[0].row(), 0).text())
            self.end_process(pid)

    def end_process(self, pid):
        try:
            process = psutil.Process(pid)
            reply = QMessageBox.question(
                self, 'Confirm', 
                f"Are you sure you want to end process {process.name()} (PID: {pid})?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                process.terminate()
                self.force_process_refresh()
        except psutil.NoSuchProcess:
            QMessageBox.warning(self, "Error", "The process no longer exists")
        except psutil.AccessDenied:
            QMessageBox.warning(self, "Error", "Access denied. Try running as administrator/root")

    def show_process_details(self, pid):
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())
