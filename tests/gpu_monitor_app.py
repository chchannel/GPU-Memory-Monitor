import sys
import os
import subprocess
import psutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette, QLinearGradient, QBrush, QFont

class ProcessItem(QFrame):
    kill_clicked = Signal(int)

    def __init__(self, pid, name, memory, exe_path, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.setFixedHeight(80)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("ProcessItem")
        
        # Style
        self.setStyleSheet("""
            #ProcessItem {
                background-color: rgba(45, 45, 60, 150);
                border-radius: 12px;
                border: 1px solid rgba(255, 255, 255, 20);
                margin: 4px;
            }
            #ProcessItem:hover {
                background-color: rgba(60, 60, 80, 200);
                border: 1px solid rgba(140, 82, 255, 100);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        # Info Layout
        info_layout = QVBoxLayout()
        name_label = QLabel(name)
        name_label.setStyleSheet("color: white; font-size: 16px; font-weight: bold;")
        
        path_label = QLabel(exe_path)
        path_label.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 11px;")
        path_label.setWordWrap(False)
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(path_label)
        layout.addLayout(info_layout, 1)

        # Memory Info
        mem_label = QLabel(f"{memory} MB")
        mem_label.setStyleSheet("color: #00f2fe; font-size: 18px; font-weight: bold; margin-right: 20px;")
        layout.addWidget(mem_label)

        # Kill Button
        self.kill_btn = QPushButton("終了")
        self.kill_btn.setFixedSize(80, 35)
        self.kill_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0844, stop:1 #ffb199);
                border-radius: 17px;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff3b6b, stop:1 #ffc9b8);
            }
            QPushButton:pressed {
                background: #ff0844;
            }
        """)
        self.kill_btn.clicked.connect(lambda: self.kill_clicked.emit(self.pid))
        layout.addWidget(self.kill_btn)

class GPUMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPU Memory Liberator")
        self.setFixedSize(600, 850)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Container
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet("""
            #MainContainer {
                background-color: rgba(15, 15, 25, 230);
                border-radius: 30px;
                border: 1px solid rgba(255, 255, 255, 40);
            }
        """)
        self.main_layout.addWidget(self.container)
        
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(20, 30, 20, 30)
        
        # Title
        title_label = QLabel("GPU MEMORY MONITOR")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            color: #dcdde1;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 2px;
            margin-bottom: 20px;
        """)
        self.container_layout.addWidget(title_label)

        # Usage Overview Container
        self.usage_box = QFrame()
        self.usage_box.setFixedHeight(150)
        self.usage_box.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(140, 82, 255, 30), stop:1 rgba(0, 242, 254, 30));
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 20);
        """)
        usage_layout = QVBoxLayout(self.usage_box)
        
        self.total_usage_lbl = QLabel("Fetching...")
        self.total_usage_lbl.setAlignment(Qt.AlignCenter)
        self.total_usage_lbl.setStyleSheet("color: white; font-size: 48px; font-weight: 900; background: transparent; border: none;")
        
        self.gpu_name_lbl = QLabel("Detecting GPU...")
        self.gpu_name_lbl.setAlignment(Qt.AlignCenter)
        self.gpu_name_lbl.setStyleSheet("color: rgba(255,255,255,150); font-size: 14px; background: transparent; border: none;")
        
        usage_layout.addWidget(self.total_usage_lbl)
        usage_layout.addWidget(self.gpu_name_lbl)
        self.container_layout.addWidget(self.usage_box)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: rgba(255, 255, 255, 20); margin-top: 20px; margin-bottom: 10px;")
        self.container_layout.addWidget(line)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setSpacing(12)
        self.list_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        self.container_layout.addWidget(self.scroll)

        # Update Timers
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_list)
        self.timer.start(3000)

        self.refresh_list()

    def get_gpu_info(self):
        try:
            # Get GPU Name
            name_res = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
            gpu_name = name_res.stdout.strip()

            # Get Memory Usage
            mem_res = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True)
            used, total = mem_res.stdout.strip().split(',')
            percent = (int(used) / int(total)) * 100
            
            return gpu_name, int(used), int(total), int(percent)
        except:
            return "N/A", 0, 0, 0

    def get_gpu_processes(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, check=True
            )
            processes = []
            for line in result.stdout.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    try:
                        pid_str = parts[0]
                        if not pid_str.isdigit(): continue
                        pid = int(pid_str)
                        mem_str = parts[2]
                        used_mem = int(mem_str) if mem_str.isdigit() else 0
                        try:
                            p = psutil.Process(pid)
                            name = p.name()
                            exe = p.exe()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            # psutil で取得できない場合は nvidia-smi の名称をパスとして扱う
                            name = os.path.basename(parts[1])
                            exe = parts[1]
                        processes.append({"pid": pid, "name": name, "exe": exe, "memory": used_mem})
                    except: continue
            return processes
        except: return []

    def refresh_list(self):
        # Update Header
        gpu_name, used, total, percent = self.get_gpu_info()
        self.total_usage_lbl.setText(f"{percent}%")
        self.gpu_name_lbl.setText(f"{gpu_name} | {used} / {total} MB USED")

        # Update List
        # To avoid flickering, we only rebuild if needed or use a more clever approach
        # For simplicity, we clear and rebuild here
        for i in reversed(range(self.list_layout.count())): 
            widget = self.list_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        
        processes = self.get_gpu_processes()
        if not processes:
            empty_lbl = QLabel("No active GPU processes")
            empty_lbl.setAlignment(Qt.AlignCenter)
            empty_lbl.setStyleSheet("color: rgba(255,255,255,80); margin-top: 40px;")
            self.list_layout.addWidget(empty_lbl)
        else:
            for p in processes:
                item = ProcessItem(p['pid'], p['name'], p['memory'], p['exe'])
                item.kill_clicked.connect(self.kill_process)
                self.list_layout.addWidget(item)

    def kill_process(self, pid):
        try:
            p = psutil.Process(pid)
            p.terminate()
            QTimer.singleShot(500, self.refresh_list)
        except: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GPUMonitorApp()
    window.show()
    sys.exit(app.exec())
