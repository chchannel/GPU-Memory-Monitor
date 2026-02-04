import sys
import os
import subprocess
import psutil
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, 
                             QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QColor, QPalette, QLinearGradient, QBrush, QFont, QFontMetrics, QPainter

THEMES = {
    "light": {
        "bg": "#f5f6fa",
        "card_bg": "#ffffff",
        "border": "#dcdde1",
        "text": "#2f3640",
        "sub_text": "#7f8fa6",
        "accent": "#0984e3",
        "hover": "#f1f2f6",
        "btn_bg": "#ffffff"
    },
    "gray": {
        "bg": "#353b48",
        "card_bg": "#2f3640",
        "border": "#718093",
        "text": "#f5f6fa",
        "sub_text": "#dcdde1",
        "accent": "#00a8ff",
        "hover": "#4b4b4b",
        "btn_bg": "#2f3640"
    },
    "dark": {
        "bg": "#1e272e",
        "card_bg": "#2d3436",
        "border": "#485460",
        "text": "#ffffff",
        "sub_text": "#808e9b",
        "accent": "#ff3f34",
        "hover": "#3d3d3d",
        "btn_bg": "#2d3436"
    }
}

class ElidedLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.full_text = text

    def setText(self, text):
        self.full_text = text
        super().setText(text)
        self.update_elided_text()

    def resizeEvent(self, event):
        self.update_elided_text()
        super().resizeEvent(event)

    def update_elided_text(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self.full_text, Qt.ElideRight, self.width())
        super().setText(elided)

class ProcessItem(QFrame):
    def __init__(self, pid, name, memory, exe_path, theme, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.setFixedHeight(40)
        self.setObjectName("ProcessItem")
        self.theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 2, 10, 2)
        layout.setSpacing(10)

        self.name_label = ElidedLabel(name)
        self.name_label.setMinimumWidth(30)
        layout.addWidget(self.name_label, 1)

        self.mem_label = QLabel(f"{memory} MB")
        self.mem_label.setFixedWidth(70)
        self.mem_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.mem_label)
        
        self.apply_theme_style()

    def apply_theme_style(self):
        c = THEMES[self.theme]
        self.setStyleSheet(f"""
            #ProcessItem {{
                background-color: {c['card_bg']};
                border-radius: 6px;
                border: 1px solid {c['border']};
                margin: 1px;
            }}
            #ProcessItem:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.name_label.setStyleSheet(f"color: {c['text']}; font-size: 13px; font-weight: 600; background: transparent; border: none;")
        self.mem_label.setStyleSheet(f"color: {c['accent']}; font-size: 13px; font-weight: bold; background: transparent; border: none;")

    def update_data(self, memory):
        self.mem_label.setText(f"{memory} MB")
        
    def update_theme(self, theme):
        self.theme = theme
        self.apply_theme_style()

class GPUWorker(QThread):
    data_ready = Signal(dict)

    def run(self):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        while True:
            try:
                name_res = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], 
                                         capture_output=True, text=True, creationflags=flags)
                gpu_name = name_res.stdout.strip()
                mem_res = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], 
                                        capture_output=True, text=True, creationflags=flags)
                used, total = mem_res.stdout.strip().split(',')
                percent = (int(used) / int(total)) * 100
                gpu_info = (gpu_name, int(used), int(total), int(percent))

                cmd = "Get-Counter '\\GPU Process Memory(*)\\Local Usage' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CounterSamples | ForEach-Object { '{0}::{1}' -f $_.Path, $_.CookedValue }"
                res = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, creationflags=flags)
                
                pid_mem_map = {}
                for line in res.stdout.strip().split('\n'):
                    if '::' not in line: continue
                    path, value = line.split('::')
                    try:
                        match = re.search(r'pid_(\d+)', path)
                        if match:
                            pid = int(match.group(1))
                            mb_val = float(value) / (1024 * 1024)
                            pid_mem_map[pid] = pid_mem_map.get(pid, 0) + mb_val
                    except: continue

                processes = []
                for pid, mem_mb in pid_mem_map.items():
                    if mem_mb < 0.1: continue
                    try:
                        p = psutil.Process(pid)
                        processes.append({"pid": pid, "name": p.name(), "exe": p.exe(), "memory": int(mem_mb)})
                    except: continue

                self.data_ready.emit({'gpu_info': gpu_info, 'processes': processes})
            except: pass
            self.msleep(3000)

class GPUMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPUメモリ監視ツール")
        self.setMinimumSize(220, 180)
        self.resize(380, 600)
        
        self.current_theme = "light"
        self.theme_list = ["light", "gray", "dark"]
        self.sort_by = "memory"
        self.process_widgets = {}
        self.last_processes = []
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header Box
        self.usage_box = QFrame()
        self.usage_box.setFixedHeight(95)
        usage_layout = QVBoxLayout(self.usage_box)
        usage_layout.setSpacing(0)
        
        self.total_usage_lbl = QLabel("0%")
        self.total_usage_lbl.setAlignment(Qt.AlignCenter)
        self.gpu_name_lbl = QLabel("検出中...")
        self.gpu_name_lbl.setAlignment(Qt.AlignCenter)
        
        usage_layout.addWidget(self.total_usage_lbl)
        usage_layout.addWidget(self.gpu_name_lbl)
        self.main_layout.addWidget(self.usage_box)

        # Control Row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setContentsMargins(0, 5, 0, 5)
        ctrl_layout.setSpacing(4)
        
        self.pin_btn = self._create_ctrl_btn("📌", "常に最前面に表示", True)
        self.pin_btn.clicked.connect(self.toggle_always_on_top)
        ctrl_layout.addWidget(self.pin_btn)

        self.compact_btn = self._create_ctrl_btn("🔳", "コンパクトモード", True)
        self.compact_btn.clicked.connect(self.toggle_compact_mode)
        ctrl_layout.addWidget(self.compact_btn)

        self.theme_btn = self._create_ctrl_btn("🎨", "テーマ切り替え", False)
        self.theme_btn.clicked.connect(self.rotate_theme)
        ctrl_layout.addWidget(self.theme_btn)

        self.compact_usage_lbl = QLabel("GPU: - %")
        self.compact_usage_lbl.hide()
        ctrl_layout.addWidget(self.compact_usage_lbl)
        
        ctrl_layout.addStretch()

        self.sort_mem_btn = self._create_ctrl_btn("使用量", "使用量でソート", False)
        self.sort_name_btn = self._create_ctrl_btn("名前", "名前でソート", False)
        self.sort_mem_btn.clicked.connect(lambda: self.set_sort("memory"))
        self.sort_name_btn.clicked.connect(lambda: self.set_sort("name"))
        ctrl_layout.addWidget(self.sort_mem_btn)
        ctrl_layout.addWidget(self.sort_name_btn)
        self.main_layout.addLayout(ctrl_layout)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.list_layout = QVBoxLayout(self.scroll_content)
        self.list_layout.setSpacing(3)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll)

        self.empty_lbl = QLabel("GPUアプリ未検出")
        self.empty_lbl.setAlignment(Qt.AlignCenter)
        self.list_layout.addWidget(self.empty_lbl)
        self.empty_lbl.hide()

        self.apply_theme()

        self.worker = GPUWorker()
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.start()

    def _create_ctrl_btn(self, text, tip, checkable):
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setCheckable(checkable)
        btn.setFixedSize(30, 28)
        return btn

    def rotate_theme(self):
        idx = (self.theme_list.index(self.current_theme) + 1) % len(self.theme_list)
        self.current_theme = self.theme_list[idx]
        self.apply_theme()
        for w in self.process_widgets.values():
            w.update_theme(self.current_theme)

    def apply_theme(self):
        c = THEMES[self.current_theme]
        self.central_widget.setStyleSheet(f"background-color: {c['bg']};")
        self.usage_box.setStyleSheet(f"background-color: {c['card_bg']}; border-radius: 12px; border: 1px solid {c['border']};")
        self.total_usage_lbl.setStyleSheet(f"color: {c['text']}; font-size: 28px; font-weight: 950; border: none; background: transparent;")
        self.gpu_name_lbl.setStyleSheet(f"color: {c['sub_text']}; font-size: 10px; border: none; background: transparent;")
        
        btn_style = f"""
            QPushButton {{ background-color: {c['card_bg']}; border: 1px solid {c['border']}; border-radius: 6px; color: {c['text']}; font-size: 10px; }}
            QPushButton:hover {{ background-color: {c['hover']}; }}
            QPushButton:checked {{ background-color: {c['text']}; color: {c['card_bg']}; border: 1px solid {c['text']}; }}
        """
        for btn in [self.pin_btn, self.compact_btn, self.theme_btn, self.sort_mem_btn, self.sort_name_btn]:
            btn.setStyleSheet(btn_style)
            
        self.compact_usage_lbl.setStyleSheet(f"color: {c['text']}; font-weight: bold; font-size: 11px;")
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.scroll_content.setStyleSheet("background: transparent;")
        self.empty_lbl.setStyleSheet(f"color: {c['sub_text']}; margin-top: 50px;")
        self.request_refresh()

    def toggle_always_on_top(self):
        if self.pin_btn.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def toggle_compact_mode(self):
        if self.compact_btn.isChecked():
            self.usage_box.hide()
            self.compact_usage_lbl.show()
            self.main_layout.setContentsMargins(5, 5, 5, 5)
        else:
            self.usage_box.show()
            self.compact_usage_lbl.hide()
            self.main_layout.setContentsMargins(15, 15, 15, 15)
            self.resize(380, 600)

    def set_sort(self, key):
        self.sort_by = key
        self.request_refresh()

    def request_refresh(self):
        self.update_ui_list(self.last_processes)

    def on_data_ready(self, data):
        gpu_name, used, total, percent = data['gpu_info']
        self.total_usage_lbl.setText(f"{percent}%")
        self.gpu_name_lbl.setText(f"{gpu_name}\n{used} / {total} MB 使用中")
        self.compact_usage_lbl.setText(f"GPU: {percent}%")
        self.last_processes = data['processes']
        self.update_ui_list(self.last_processes)

    def update_ui_list(self, processes):
        c = THEMES[self.current_theme]
        active_style = f"background-color: {c['text']}; color: {c['card_bg']}; border-radius: 6px; font-size: 10px;"
        normal_style = f"background-color: {c['card_bg']}; border: 1px solid {c['border']}; border-radius: 6px; color: {c['text']}; font-size: 10px;"
        
        if self.sort_by == "memory":
            processes.sort(key=lambda x: x['memory'], reverse=True)
            self.sort_mem_btn.setStyleSheet(active_style)
            self.sort_name_btn.setStyleSheet(normal_style)
        else:
            processes.sort(key=lambda x: x['name'].lower())
            self.sort_name_btn.setStyleSheet(active_style)
            self.sort_mem_btn.setStyleSheet(normal_style)

        display_list = processes
        new_pids = set(p['pid'] for p in display_list)
        old_pids = set(self.process_widgets.keys())

        for pid in old_pids - new_pids:
            widget = self.process_widgets.pop(pid)
            self.list_layout.removeWidget(widget)
            widget.deleteLater()

        for idx, p in enumerate(display_list):
            pid = p['pid']
            if pid in self.process_widgets:
                widget = self.process_widgets[pid]
                widget.update_data(p['memory'])
                if self.list_layout.indexOf(widget) != idx:
                    self.list_layout.removeWidget(widget)
                    self.list_layout.insertWidget(idx, widget)
            else:
                widget = ProcessItem(pid, p['name'], p['memory'], p['exe'], self.current_theme, self.scroll_content)
                self.process_widgets[pid] = widget
                self.list_layout.insertWidget(idx, widget)
        self.empty_lbl.setVisible(len(display_list) == 0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GPUMonitorApp()
    window.show()
    sys.exit(app.exec())
