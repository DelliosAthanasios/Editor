import sys
import psutil
import platform
import subprocess
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QLabel, QProgressBar,
    QHBoxLayout, QTableWidget, QTableWidgetItem, QMainWindow, QHeaderView,
    QPushButton, QMenu, QAction, QMessageBox, QSizePolicy, QScrollArea, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QDateTime, QMutex, QMutexLocker, QRectF
from PyQt5.QtGui import QFont, QColor, QBrush, QPainter, QPen

# Try to import sensors_temperatures from psutil or fallback to None
try:
    from psutil import sensors_temperatures
except ImportError:
    sensors_temperatures = None

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
QChart {
    background-color: #252526;
    border: 1px solid #3E3E42;
}
QTreeWidget {
    background: #252526;
    color: #D4D4D4;
    border: 1px solid #3E3E42;
}
QTreeWidget::item {
    background: #252526;
}
QTreeWidget::item:selected {
    background: #37373D;
    color: #FFFFFF;
}
"""

class ProcessUpdaterThread(QThread):
    update_signal = pyqtSignal(list)

    def run(self):
        try:
            psutil.cpu_percent(interval=None)
            processes = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status']):
                try:
                    info = p.info
                    processes.append(
                        (
                            info['pid'],
                            info['name'],
                            info['cpu_percent'],
                            info['memory_info'].rss if info.get('memory_info') else 0,
                            info.get('status', 'N/A')
                        )
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            processes.sort(key=lambda x: x[2], reverse=True)
            self.update_signal.emit(processes)
        except Exception as e:
            print("ProcessUpdaterThread error:", e)

class ServiceUpdaterThread(QThread):
    update_signal = pyqtSignal(list)

    def run(self):
        try:
            if platform.system() == 'Linux':
                output = subprocess.check_output(
                    ['systemctl', '--no-pager', '--all', '--type=service', '--no-legend'],
                    text=True, timeout=5
                )
                services = []
                for line in output.splitlines():
                    if line.strip():
                        parts = line.split(None, 4)
                        if len(parts) >= 5:
                            service = parts[0]
                            load_status = parts[1]
                            active_status = parts[2]
                            sub_status = parts[3]
                            description = parts[4]
                            # Get MainPID if possible
                            try:
                                pid_output = subprocess.check_output(
                                    ['systemctl', 'show', service, '--property=MainPID'],
                                    text=True, timeout=2
                                )
                                pid = pid_output.split('=')[1].strip()
                            except Exception:
                                pid = "N/A"
                            services.append((service, active_status, description, pid))
                self.update_signal.emit(services)
            elif platform.system() == 'Windows':
                # Use 'sc query' on Windows
                output = subprocess.check_output(['sc', 'query', 'type=', 'service', 'state=', 'all'], text=True)
                services = []
                lines = output.splitlines()
                service = status = pid = desc = ""
                for line in lines:
                    if line.strip().startswith("SERVICE_NAME:"):
                        service = line.split(":", 1)[1].strip()
                    elif line.strip().startswith("STATE"):
                        status = line.split(":", 1)[1].strip().split(" ")[1]
                    elif line.strip().startswith("PID"):
                        pid = line.split(":", 1)[1].strip()
                    elif line.strip() == "":
                        if service:
                            services.append((service, status, desc, pid))
                        service = status = pid = desc = ""
                    elif line.strip().startswith("DISPLAY_NAME:"):
                        desc = line.split(":", 1)[1].strip()
                if service:
                    services.append((service, status, desc, pid))
                self.update_signal.emit(services)
            else:
                self.update_signal.emit([("Unavailable", "Not supported", "", "")])
        except Exception as e:
            self.update_signal.emit([("Error", str(e), "", "")])

class CpuSketchWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(400)
        self.cpuinfo = None
        self.cpu_percent = []
        self.core_temps = []
        self.err = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1500)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def get_cpuinfo(self):
        cpuinfo = {
            'physical_cores': psutil.cpu_count(logical=False) or 1,
            'logical_cores': psutil.cpu_count(logical=True),
            'brand': platform.processor(),
        }
        try:
            if platform.system() == 'Linux':
                output = subprocess.check_output(['lscpu'], text=True, timeout=2)
                for line in output.splitlines():
                    if "Model name" in line and not cpuinfo['brand']:
                        cpuinfo['brand'] = line.split(":", 1)[1].strip()
            elif platform.system() == 'Windows':
                try:
                    import wmi
                    c = wmi.WMI()
                    for processor in c.Win32_Processor():
                        cpuinfo['brand'] = processor.Name
                except Exception:
                    pass
        except Exception:
            pass
        return cpuinfo

    def get_core_temperatures(self):
        temps = []
        try:
            if hasattr(psutil, "sensors_temperatures"):
                sensors = psutil.sensors_temperatures()
            elif sensors_temperatures:
                sensors = sensors_temperatures()
            else:
                sensors = {}
            for key in sensors:
                entries = sensors[key]
                for entry in entries:
                    if hasattr(entry, "label") and entry.label and (
                        "Core" in entry.label or "Tccd" in entry.label or "Package" in entry.label
                    ):
                        temps.append((entry.label, entry.current))
            if not temps and sensors:
                for key in sensors:
                    for entry in sensors[key]:
                        temps.append((getattr(entry, "label", key), getattr(entry, "current", 0)))
        except Exception:
            pass
        return temps

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)
        try:
            self.cpuinfo = self.get_cpuinfo()
            # Try-catch for cpu_percent to avoid "Cpu can not be mapped"
            try:
                self.cpu_percent = psutil.cpu_percent(percpu=True)
            except Exception:
                self.cpu_percent = []
            self.core_temps = self.get_core_temperatures()
            self.err = None
            if self.cpuinfo['logical_cores'] is None or not self.cpu_percent:
                raise Exception("CPU info or usage unavailable")
            self.draw_cpu_sketch(painter, rect)
        except Exception as e:
            painter.setPen(QPen(QColor(255, 100, 100)))
            painter.setFont(QFont("Segoe UI", 18, QFont.Bold))
            painter.drawText(rect, Qt.AlignCenter, "Cpu can not be mapped")
            self.err = str(e)

    def draw_cpu_sketch(self, painter, rect):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(40, 45, 80, 230))
        painter.drawRoundedRect(rect, 18, 18)

        chip_rect = QRectF(rect.x() + 40, rect.y() + 50, rect.width() - 80, rect.height() - 100)
        painter.setPen(QPen(QColor(120, 200, 220, 140), 5))
        painter.setBrush(QColor(30, 30, 50, 40))
        painter.drawRoundedRect(chip_rect, 20, 20)

        import random
        painter.setPen(QPen(QColor(110, 170, 200, 80), 2))
        random.seed(0)
        for i in range(80):
            x1 = chip_rect.x() + random.randint(0, int(chip_rect.width()))
            y1 = chip_rect.y() + random.randint(0, int(chip_rect.height()))
            x2 = chip_rect.x() + random.randint(0, int(chip_rect.width()))
            y2 = chip_rect.y() + random.randint(0, int(chip_rect.height()))
            painter.drawLine(x1, y1, x2, y2)

        painter.setPen(QColor(180, 180, 255))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(rect.x() + 15, rect.y() + 33, self.cpuinfo.get('brand', "CPU"))

        logicals = self.cpuinfo['logical_cores']
        core_temp_labels = {label: temp for label, temp in self.core_temps}
        grid_cols = min(logicals, 8)
        grid_rows = (logicals + grid_cols - 1) // grid_cols if logicals else 1
        core_w = (chip_rect.width() - 20 * (grid_cols + 1)) / grid_cols if grid_cols else 20
        core_h = (chip_rect.height() - 20 * (grid_rows + 1)) / grid_rows if grid_rows else 20
        painter.setFont(QFont("Segoe UI", 9))
        for idx in range(logicals or 0):
            row = idx // grid_cols if grid_cols else 0
            col = idx % grid_cols if grid_cols else idx
            x = chip_rect.x() + 20 + col * (core_w + 20)
            y = chip_rect.y() + 20 + row * (core_h + 20)
            percent = self.cpu_percent[idx] if idx < len(self.cpu_percent) else 0
            temp_label = f"Core {idx}" if f"Core {idx}" in core_temp_labels else None
            temp = core_temp_labels.get(temp_label, None)
            color = QColor(
                int(150 + percent * 1.05),
                int(220 - percent * 1.6),
                int(100 - percent * 0.5),
                200
            )
            painter.setPen(QPen(QColor(180, 210, 255, 110), 2))
            painter.setBrush(color)
            painter.drawRoundedRect(x, y, core_w, core_h, 9, 9)
            painter.setPen(QColor(230, 230, 255))
            painter.drawText(x + 6, y + 19, f"CPU {idx+1}")
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(
                x + 6, y + 37,
                f"{percent:.1f}%" + (f" | {temp}°C" if temp is not None else "")
            )
            bar_w = core_w - 15
            bar_h = 9
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(120, 120, 120, 60))
            painter.drawRect(x + 6, y + core_h - 21, bar_w, bar_h)
            painter.setBrush(QColor(100, 220, 100, 180))
            painter.drawRect(x + 6, y + core_h - 21, int(bar_w * percent / 100), bar_h)
            if temp is not None:
                painter.setBrush(QColor(220, 120, 100, 180))
                painter.drawRect(x + 6, y + core_h - 10, int(bar_w * min(1.0, temp / 100)), 7)
                painter.setPen(QColor(230, 200, 200))
                painter.setFont(QFont("Segoe UI", 7))
                painter.drawText(
                    x + bar_w - 32, y + core_h - 2,
                    f"{temp}°C"
                )

        legend_x = chip_rect.x()
        legend_y = chip_rect.y() + chip_rect.height() + 18
        painter.setPen(QColor(130, 220, 110))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawRect(legend_x, legend_y, 13, 10)
        painter.drawText(legend_x + 18, legend_y + 10, "CPU Usage")
        painter.setPen(QColor(220, 120, 100))
        painter.drawRect(legend_x + 90, legend_y, 13, 10)
        painter.drawText(legend_x + 108, legend_y + 10, "Temperature")

class SensorsTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Sensor", "Value", "Min", "Max"])
        self.setColumnCount(4)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet("QTreeWidget { font-size: 11px; }")
        self.setMinimumWidth(550)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)
        self.refresh()

    def refresh(self):
        self.clear()
        # Try to group by chip and by sensor type
        try:
            sensors = None
            if hasattr(psutil, "sensors_temperatures"):
                sensors = psutil.sensors_temperatures(fahrenheit=False)
            elif sensors_temperatures:
                sensors = sensors_temperatures()
            if not sensors:
                root = QTreeWidgetItem(self, ["No sensor data available"])
                self.addTopLevelItem(root)
                return
            for chip_name, entries in sensors.items():
                chip_root = QTreeWidgetItem(self, [chip_name])
                chip_root.setExpanded(True)
                subtypes = {}
                for entry in entries:
                    label = getattr(entry, "label", "") or ""
                    cur = getattr(entry, "current", "")
                    high = getattr(entry, "high", "")
                    critical = getattr(entry, "critical", "")
                    minv = getattr(entry, "min", "")
                    maxv = getattr(entry, "max", "")
                    subtypes.setdefault("Temperatures", []).append((label, cur, minv, maxv))
                for subtype, values in subtypes.items():
                    subtype_root = QTreeWidgetItem(chip_root, [subtype])
                    subtype_root.setExpanded(True)
                    for val in values:
                        it = QTreeWidgetItem(subtype_root, [str(x) for x in val])
            # Fans (Linux only, if implemented)
            try:
                fans = None
                if hasattr(psutil, "sensors_fans"):
                    fans = psutil.sensors_fans()
                if fans:
                    fans_root = QTreeWidgetItem(self, ["Fans"])
                    for chip, fan_entries in fans.items():
                        chip_node = QTreeWidgetItem(fans_root, [chip])
                        for fan in fan_entries:
                            label = getattr(fan, "label", "")
                            cur = getattr(fan, "current", "")
                            minv = getattr(fan, "min", "")
                            maxv = getattr(fan, "max", "")
                            QTreeWidgetItem(chip_node, [label, str(cur), str(minv), str(maxv)])
            except Exception:
                pass
        except Exception:
            self.clear()
            root = QTreeWidgetItem(self, ["Error: Could not read sensors"])
            self.addTopLevelItem(root)

class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Task Manager")
        self.setGeometry(100, 100, 1200, 850)
        self.setStyleSheet(DARK_STYLE)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.cpu_map_tab = QWidget()
        self.performance_tab = QWidget()
        self.processes_tab = QWidget()
        self.services_tab = QWidget()
        self.disk_tab = QWidget()
        self.network_tab = QWidget()
        self.sensors_tab = QWidget()

        self.tabs.addTab(self.cpu_map_tab, "CPU Map")
        self.tabs.addTab(self.performance_tab, "Performance")
        self.tabs.addTab(self.processes_tab, "Processes")
        self.tabs.addTab(self.services_tab, "Services")
        self.tabs.addTab(self.disk_tab, "Disks")
        self.tabs.addTab(self.network_tab, "Network")
        self.tabs.addTab(self.sensors_tab, "Sensors")

        self.init_cpu_map_tab()
        self.init_performance_tab()
        self.init_processes_tab()
        self.init_services_tab()
        self.init_disk_tab()
        self.init_network_tab()
        self.init_sensors_tab()

        self.status_bar = self.statusBar()
        self.update_time_label = QLabel()
        self.status_bar.addPermanentWidget(self.update_time_label)

        self.fast_timer = QTimer()
        self.fast_timer.timeout.connect(self.update_fast_stats)
        self.fast_timer.start(1000)

        self.slow_timer = QTimer()
        self.slow_timer.timeout.connect(self.update_slow_stats)
        self.slow_timer.start(3000)

        self.prev_net = psutil.net_io_counters()
        self.initial_net = psutil.net_io_counters()
        self.process_updater = None
        self.service_updater = None

        self.process_mutex = QMutex()

        self.process_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.process_table.customContextMenuRequested.connect(self.show_process_context_menu)
        self.process_table.itemSelectionChanged.connect(self.on_process_selection)
        self._proc_detail_mutex = QMutex()
        self._last_selected_pid = None

    def init_cpu_map_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        scroll = QScrollArea()
        self.cpu_sketch_widget = CpuSketchWidget()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.cpu_sketch_widget)
        layout.addWidget(scroll)
        self.cpu_map_tab.setLayout(layout)

    def init_sensors_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        self.sensors_tree = SensorsTreeWidget()
        layout.addWidget(self.sensors_tree)
        self.sensors_tab.setLayout(layout)

    def init_performance_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.cpu_group = QWidget()
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
        self.cpu_group.setLayout(cpu_layout)
        layout.addWidget(self.cpu_group)

        self.mem_group = QWidget()
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
        self.mem_group.setLayout(mem_layout)
        layout.addWidget(self.mem_group)

        self.disk_group = QWidget()
        disk_layout = QVBoxLayout()
        disk_layout.setContentsMargins(0, 0, 0, 0)
        self.disk_label = QLabel("Disk Usage")
        self.disk_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        disk_layout.addWidget(self.disk_label)
        self.disk_bar = QProgressBar()
        self.disk_bar.setFormat("Main Disk: %p%")
        self.disk_bar.setStyleSheet("QProgressBar { height: 24px; }")
        disk_layout.addWidget(self.disk_bar)
        self.disk_group.setLayout(disk_layout)
        layout.addWidget(self.disk_group)

        self.net_group = QWidget()
        net_layout = QVBoxLayout()
        net_layout.setContentsMargins(0, 0, 0, 0)
        self.net_label = QLabel("Network")
        self.net_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        net_layout.addWidget(self.net_label)
        self.net_stats = QLabel("Sent: 0 MB | Received: 0 MB")
        net_layout.addWidget(self.net_stats)
        self.net_group.setLayout(net_layout)
        layout.addWidget(self.net_group)
        self.performance_tab.setLayout(layout)

    def init_processes_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.force_process_refresh)
        self.end_task_btn = QPushButton("End Task")
        self.end_task_btn.clicked.connect(self.end_selected_process)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.end_task_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
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
        toolbar = QHBoxLayout()
        self.refresh_services_btn = QPushButton("Refresh")
        self.refresh_services_btn.clicked.connect(self.update_services)
        toolbar.addWidget(self.refresh_services_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(4)
        self.service_table.setHorizontalHeaderLabels(["Service", "Status", "Description", "PID"])
        self.service_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.service_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.service_table.verticalHeader().setVisible(False)
        self.service_table.setSortingEnabled(True)
        layout.addWidget(self.service_table)
        self.services_tab.setLayout(layout)

    def init_disk_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.disk_table = QTableWidget()
        self.disk_table.setColumnCount(10)
        self.disk_table.setHorizontalHeaderLabels([
            "Device", "Mountpoint", "Type", "Total", "Used", "Free", "Usage %",
            "Reads", "Writes", "IO Time"
        ])
        self.disk_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.disk_table.verticalHeader().setVisible(False)
        self.disk_table.setSortingEnabled(True)
        layout.addWidget(self.disk_table)
        self.disk_tab.setLayout(layout)

    def init_network_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.network_table = QTableWidget()
        self.network_table.setColumnCount(6)
        self.network_table.setHorizontalHeaderLabels([
            "Interface", "Sent (MB)", "Recv (MB)", "Packets Sent", "Packets Recv", "Status"
        ])
        self.network_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.network_table.verticalHeader().setVisible(False)
        self.network_table.setSortingEnabled(True)
        layout.addWidget(self.network_table)
        self.network_tab.setLayout(layout)
        self.init_network_chart()

    def init_network_chart(self):
        from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
        self.network_chart = QChart()
        self.network_chart.setTheme(QChart.ChartThemeDark)
        self.network_chart.legend().setVisible(False)
        self.sent_series = QLineSeries()
        self.recv_series = QLineSeries()
        self.sent_series.setName("Sent")
        self.recv_series.setName("Received")
        self.sent_series.setColor(QColor(100, 200, 255))
        self.recv_series.setColor(QColor(255, 100, 100))
        self.network_chart.addSeries(self.sent_series)
        self.network_chart.addSeries(self.recv_series)
        self.axisX = QDateTimeAxis()
        self.axisX.setFormat("hh:mm:ss")
        self.axisX.setTitleText("Time")
        self.axisY = QValueAxis()
        self.axisY.setTitleText("MB/s")
        self.network_chart.addAxis(self.axisX, Qt.AlignBottom)
        self.network_chart.addAxis(self.axisY, Qt.AlignLeft)
        self.sent_series.attachAxis(self.axisX)
        self.sent_series.attachAxis(self.axisY)
        self.recv_series.attachAxis(self.axisX)
        self.recv_series.attachAxis(self.axisY)
        chart_view = QChartView(self.network_chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        self.network_tab.layout().insertWidget(0, chart_view)

    def update_fast_stats(self):
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            self.cpu_bar.setValue(int(cpu_percent))
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
                    core_layout.setContentsMargins(0, 0, 0, 0)
                    core_layout.setSpacing(10)
                    core_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    core_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    core_layout.addWidget(core_label)
                    core_layout.addWidget(core_bar)
                    core_widget = QWidget()
                    core_widget.setLayout(core_layout)
                    core_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self.cpu_cores_layout.addWidget(core_widget)
            mem = psutil.virtual_memory()
            self.ram_bar.setValue(int(mem.percent))
            if hasattr(psutil, 'swap_memory'):
                swap = psutil.swap_memory()
                self.swap_bar.setValue(int(swap.percent))
            current_net = psutil.net_io_counters()
            sent = (current_net.bytes_sent - self.prev_net.bytes_sent) / (1024 ** 2)
            recv = (current_net.bytes_recv - self.prev_net.bytes_recv) / (1024 ** 2)
            self.net_stats.setText(f"Sent: {sent:.1f} MB/s | Received: {recv:.1f} MB/s")
            self.prev_net = current_net
            self.update_time_label.setText(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
        except Exception:
            pass

    def update_slow_stats(self):
        try:
            self.update_disks()
            self.update_network()
            self.update_services()
            with QMutexLocker(self.process_mutex):
                if self.process_updater is None or not self.process_updater.isRunning():
                    self.process_updater = ProcessUpdaterThread()
                    self.process_updater.update_signal.connect(self.update_process_table)
                    self.process_updater.start()
            self.update_disk_io_stats()
        except Exception:
            pass

    def update_disk_io_stats(self):
        try:
            disk_io = psutil.disk_io_counters(perdisk=True)
            for row in range(self.disk_table.rowCount()):
                device = self.disk_table.item(row, 0)
                if device and device.text() in disk_io:
                    io = disk_io[device.text()]
                    self.disk_table.setItem(row, 7, QTableWidgetItem(str(io.read_count)))
                    self.disk_table.setItem(row, 8, QTableWidgetItem(str(io.write_count)))
                    self.disk_table.setItem(row, 9, QTableWidgetItem(f"{io.read_time + io.write_time}ms"))
        except Exception:
            pass

    def update_process_table(self, processes):
        try:
            self.process_table.setSortingEnabled(False)
            self.process_table.setRowCount(len(processes))
            total_mem = psutil.virtual_memory().total
            for row, (pid, name, cpu, mem_bytes, status) in enumerate(processes):
                self.process_table.setItem(row, 0, QTableWidgetItem(str(pid)))
                name_item = QTableWidgetItem(name)
                self.process_table.setItem(row, 1, name_item)
                cpu_item = QTableWidgetItem(f"{cpu:.1f}")
                cpu_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if cpu > 50:
                    cpu_item.setForeground(QBrush(QColor(255, 100, 100)))
                elif cpu > 20:
                    cpu_item.setForeground(QBrush(QColor(255, 200, 100)))
                self.process_table.setItem(row, 2, cpu_item)
                mem_mb = mem_bytes / (1024 ** 2)
                mem_item = QTableWidgetItem(f"{mem_mb:.1f} MB")
                mem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.process_table.setItem(row, 3, mem_item)
                mem_percent = (mem_bytes / total_mem) * 100 if total_mem else 0
                mem_percent_item = QTableWidgetItem(f"{mem_percent:.1f}")
                mem_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if mem_percent > 10:
                    mem_percent_item.setForeground(QBrush(QColor(255, 100, 100)))
                elif mem_percent > 5:
                    mem_percent_item.setForeground(QBrush(QColor(255, 200, 100)))
                self.process_table.setItem(row, 4, mem_percent_item)
                self.process_table.setItem(row, 5, QTableWidgetItem(str(status)))
            self.process_table.setSortingEnabled(True)
        except Exception:
            pass

    def update_service_table(self, services):
        try:
            self.service_table.setSortingEnabled(False)
            self.service_table.setRowCount(len(services))
            for i, (service, status, description, pid) in enumerate(services):
                self.service_table.setItem(i, 0, QTableWidgetItem(service))
                self.service_table.setItem(i, 1, QTableWidgetItem(status))
                self.service_table.setItem(i, 2, QTableWidgetItem(description))
                self.service_table.setItem(i, 3, QTableWidgetItem(pid))
            self.service_table.setSortingEnabled(True)
        except Exception:
            pass

    def update_services(self):
        # Always use the QThread-based updater for async
        if self.service_updater is None or not self.service_updater.isRunning():
            self.service_updater = ServiceUpdaterThread()
            self.service_updater.update_signal.connect(self.update_service_table)
            self.service_updater.start()

    def update_disks(self):
        try:
            partitions = psutil.disk_partitions()
            self.disk_table.setSortingEnabled(False)
            self.disk_table.setRowCount(len(partitions))
            row = 0
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    self.disk_table.setItem(row, 0, QTableWidgetItem(part.device))
                    self.disk_table.setItem(row, 1, QTableWidgetItem(part.mountpoint))
                    self.disk_table.setItem(row, 2, QTableWidgetItem(part.fstype))
                    total_gb = usage.total / (1024 ** 3)
                    self.disk_table.setItem(row, 3, QTableWidgetItem(f"{total_gb:.1f} GB"))
                    used_gb = usage.used / (1024 ** 3)
                    self.disk_table.setItem(row, 4, QTableWidgetItem(f"{used_gb:.1f} GB"))
                    free_gb = usage.free / (1024 ** 3)
                    self.disk_table.setItem(row, 5, QTableWidgetItem(f"{free_gb:.1f} GB"))
                    usage_item = QTableWidgetItem(f"{usage.percent}%")
                    if usage.percent > 90:
                        usage_item.setForeground(QBrush(QColor(255, 100, 100)))
                    elif usage.percent > 75:
                        usage_item.setForeground(QBrush(QColor(255, 200, 100)))
                    self.disk_table.setItem(row, 6, usage_item)
                    row += 1
                except (PermissionError, psutil.AccessDenied):
                    continue
            self.disk_table.setSortingEnabled(True)
        except Exception:
            pass

    def update_network(self):
        try:
            interfaces = psutil.net_io_counters(pernic=True)
            self.network_table.setSortingEnabled(False)
            self.network_table.setRowCount(len(interfaces))
            for row, (name, data) in enumerate(interfaces.items()):
                self.network_table.setItem(row, 0, QTableWidgetItem(name))
                self.network_table.setItem(row, 1, QTableWidgetItem(f"{data.bytes_sent/(1024**2):.1f}"))
                self.network_table.setItem(row, 2, QTableWidgetItem(f"{data.bytes_recv/(1024**2):.1f}"))
                self.network_table.setItem(row, 3, QTableWidgetItem(str(data.packets_sent)))
                self.network_table.setItem(row, 4, QTableWidgetItem(str(data.packets_recv)))
                status = "Active" if data.bytes_sent + data.bytes_recv > 0 else "Inactive"
                status_item = QTableWidgetItem(status)
                if status == "Active":
                    status_item.setForeground(QBrush(QColor(100, 255, 100)))
                self.network_table.setItem(row, 5, status_item)
            self.network_table.setSortingEnabled(True)
            self.update_network_chart()
        except Exception:
            pass

    def update_network_chart(self):
        try:
            now = datetime.now()
            sent = (self.prev_net.bytes_sent - self.initial_net.bytes_sent) / (1024 ** 2)
            recv = (self.prev_net.bytes_recv - self.initial_net.bytes_recv) / (1024 ** 2)
            if self.sent_series.count() > 60:
                self.sent_series.removePoints(0, 1)
                self.recv_series.removePoints(0, 1)
            ms_epoch = int(now.timestamp() * 1000)
            self.sent_series.append(ms_epoch, sent)
            self.recv_series.append(ms_epoch, recv)
            start = QDateTime.fromMSecsSinceEpoch(int((now - timedelta(seconds=60)).timestamp() * 1000))
            end = QDateTime.fromMSecsSinceEpoch(ms_epoch)
            self.axisX.setRange(start, end)
        except Exception:
            pass

    def clear_layout(self, layout):
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def force_process_refresh(self):
        with QMutexLocker(self.process_mutex):
            if self.process_updater is None or not self.process_updater.isRunning():
                self.process_updater = ProcessUpdaterThread()
                self.process_updater.update_signal.connect(self.update_process_table)
                self.process_updater.start()

    def show_process_context_menu(self, position):
        selected_row = self.process_table.rowAt(position.y())
        if selected_row >= 0:
            try:
                pid = int(self.process_table.item(selected_row, 0).text())
                menu = QMenu()
                end_action = QAction("End Process", self)
                end_action.triggered.connect(lambda: self.end_process(pid))
                menu.addAction(end_action)
                details_action = QAction("Process Details", self)
                details_action.triggered.connect(lambda: self.show_process_details(pid))
                menu.addAction(details_action)
                menu.exec_(self.process_table.viewport().mapToGlobal(position))
            except Exception:
                pass

    def on_process_selection(self):
        pass

    def end_selected_process(self):
        selected_items = self.process_table.selectedItems()
        if selected_items:
            try:
                pid = int(self.process_table.item(selected_items[0].row(), 0).text())
                self.end_process(pid)
            except Exception:
                pass

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
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to terminate process: {str(e)}")

    def show_process_details(self, pid):
        def show():
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
        QTimer.singleShot(1, show)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(DARK_STYLE)
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())