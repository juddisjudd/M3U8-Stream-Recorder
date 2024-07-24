import sys
import os
import subprocess
import time
import json
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox, QHBoxLayout
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal

class FFmpegThread(QThread):
    ffmpeg_status = pyqtSignal(int, str)

    def __init__(self, row, ffmpeg_cmd):
        super().__init__()
        self.row = row
        self.ffmpeg_cmd = ffmpeg_cmd
        self.process = None
        self._stop_requested = False

    def run(self):
        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                self.ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                startupinfo=startupinfo
            )

            while not self._stop_requested:
                return_code = self.process.poll()
                if return_code is not None:
                    break
                
                line = self.process.stderr.readline()
                if line:
                    if "Connection closed" in line or "Server returned 404 Not Found" in line:
                        self.ffmpeg_status.emit(self.row, "Stream Ended")
                        break
                    elif "error" in line.lower():
                        self.ffmpeg_status.emit(self.row, "Error")
                        break
                time.sleep(0.1)

            if self._stop_requested:
                self.ffmpeg_status.emit(self.row, "Stopped")
            elif return_code == 0:
                self.ffmpeg_status.emit(self.row, "Completed")
            else:
                self.ffmpeg_status.emit(self.row, "Error")

        except Exception as e:
            self.ffmpeg_status.emit(self.row, f"Error: {str(e)}")

    def stop(self):
        if self.process:
            self.ffmpeg_status.emit(self.row, "Stopping")
            self._stop_requested = True

            try:
                self.process.communicate(input='q', timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

class StreamRecorder(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("M3U8 Stream Recorder")
        self.setGeometry(100, 100, 860, 512)
        self.setFixedSize(860, 512)
        
        self.streams = []
        self.initUI()
    
    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        
        self.url_input = QLineEdit(self)
        self.url_input.setPlaceholderText("Enter the M3U8 URL")
        
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Enter the Stream Name")
        
        self.add_stream_btn = QPushButton("Add Stream", self)
        self.add_stream_btn.clicked.connect(self.add_stream)

        self.clear_stopped_btn = QPushButton("Clear Stopped", self)
        self.clear_stopped_btn.clicked.connect(self.clear_stopped_streams)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_stream_btn)
        buttons_layout.addWidget(self.clear_stopped_btn)
        
        self.folder_label = QLabel("No folder selected", self)
        self.select_folder_btn = QPushButton("Select Folder", self)
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        self.stream_table = QTableWidget(self)
        self.stream_table.setColumnCount(6)
        self.stream_table.setHorizontalHeaderLabels(["Stream Name", "URL", "Status", "Duration", "FFmpeg Status", "Action"])
        self.stream_table.setColumnWidth(0, 150)
        self.stream_table.setColumnWidth(1, 300)
        self.stream_table.setColumnWidth(2, 100)
        self.stream_table.setColumnWidth(3, 100)
        self.stream_table.setColumnWidth(4, 108)
        self.stream_table.setColumnWidth(5, 75)
        
        self.layout.addWidget(self.url_input)
        self.layout.addWidget(self.name_input)
        self.layout.addLayout(buttons_layout)
        self.layout.addWidget(self.folder_label)
        self.layout.addWidget(self.select_folder_btn)
        self.layout.addWidget(self.stream_table)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_durations)
        self.timer.start(1000)
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder = folder
            self.folder_label.setText(f"Folder: {folder}")
    
    def add_stream(self):
        url = self.url_input.text().strip()
        name = self.name_input.text().strip()
        
        if not url or not name:
            QMessageBox.warning(self, "Input Error", "Both URL and Stream Name are required.")
            return
        
        if not hasattr(self, 'folder'):
            QMessageBox.warning(self, "Folder Error", "Please select a folder to save recordings.")
            return
        
        row_position = self.stream_table.rowCount()
        self.stream_table.insertRow(row_position)
        
        self.stream_table.setItem(row_position, 0, QTableWidgetItem(name))
        self.stream_table.setItem(row_position, 1, QTableWidgetItem(url))
        self.stream_table.setItem(row_position, 2, QTableWidgetItem("Stopped"))
        self.stream_table.setItem(row_position, 3, QTableWidgetItem("00h:00m:00s"))
        self.stream_table.setItem(row_position, 4, QTableWidgetItem("Idle"))
        
        action_button = QPushButton("Start", self)
        
        self.stream_table.setCellWidget(row_position, 5, action_button)
        
        action_button.clicked.connect(lambda _, row=row_position: self.toggle_stream(row))
        
        self.streams.append({
            "url": url,
            "name": name,
            "start_time": None,
            "process": None,
            "row": row_position,
            "output_path": None
        })
        
        self.url_input.clear()
        self.name_input.clear()
    
    def toggle_stream(self, row):
        stream = self.streams[row]
        if stream["process"] is None:
            self.start_stream(row)
        else:
            self.stop_stream(row)
    
    def start_stream(self, row):
        stream = self.streams[row]
        filename = f"{stream['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        output_path = os.path.join(self.folder, filename)
        stream["output_path"] = output_path
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', stream['url'],
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-movflags', '+faststart',
            output_path
        ]
        
        ffmpeg_thread = FFmpegThread(row, ffmpeg_cmd)
        ffmpeg_thread.ffmpeg_status.connect(self.update_ffmpeg_status)
        ffmpeg_thread.start()
        
        stream["start_time"] = time.time()
        stream["process"] = ffmpeg_thread
        
        self.stream_table.setItem(row, 2, QTableWidgetItem("Recording"))
        self.stream_table.setItem(row, 4, QTableWidgetItem("Recording"))
        
        action_button = self.stream_table.cellWidget(row, 5)
        action_button.setText("Stop")
    
    def stop_stream(self, row):
        stream = self.streams[row]
        
        stream["process"].stop()
        
        stream["process"] = None
        stream["start_time"] = None
        
        self.stream_table.setItem(row, 2, QTableWidgetItem("Stopped"))
        
        action_button = self.stream_table.cellWidget(row, 5)
        action_button.setText("Start")

        if stream["output_path"]:
            self.check_file_integrity(stream["output_path"])
    
    def update_ffmpeg_status(self, row, status):
        self.stream_table.setItem(row, 4, QTableWidgetItem(status))
        if status in ["Stream Ended", "Error", "Completed", "Stopped"]:
            self.stream_table.setItem(row, 2, QTableWidgetItem("Stopped"))
            
            stream = self.streams[row]
            stream["process"] = None
            stream["start_time"] = None
            
            action_button = self.stream_table.cellWidget(row, 5)
            action_button.setText("Start")

            if stream["output_path"]:
                self.check_file_integrity(stream["output_path"])
    
    def update_durations(self):
        for stream in self.streams:
            if stream["start_time"] is not None:
                elapsed_time = time.time() - stream["start_time"]
                duration = time.strftime("%Hh:%Mm:%Ss", time.gmtime(elapsed_time))
                self.stream_table.setItem(stream["row"], 3, QTableWidgetItem(duration))
    
    def clear_stopped_streams(self):
        for row in reversed(range(self.stream_table.rowCount())):
            if self.stream_table.item(row, 2).text() == "Stopped":
                self.stream_table.removeRow(row)

    def check_file_integrity(self, file_path):
        try:
            result = subprocess.run(['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', file_path], 
                                    capture_output=True, text=True)
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                duration = metadata.get('format', {}).get('duration')
                if duration:
                    return True
                else:
                    return False
            else:
                return False
        except Exception:
            return False

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = StreamRecorder()
    main_window.show()
    sys.exit(app.exec())
