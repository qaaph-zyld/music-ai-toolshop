"""Main GUI window for StemSlicer"""
import os
from pathlib import Path
from typing import List, Dict
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QComboBox, QSpinBox,
    QLineEdit, QFileDialog, QTextEdit, QGroupBox, QCheckBox,
    QProgressBar, QMessageBox, QDoubleSpinBox, QSplitter
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QIcon

from .demucs_runner import DemucsRunner
from .worker import ProcessWorker
from .utils import scan_audio_files, sanitize_filename, ensure_dir


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StemSlicer - Audio Stem Separation")
        self.setMinimumSize(900, 700)
        
        self.runner = DemucsRunner()
        self.file_queue: List[Dict] = []
        self.current_processing_index = -1
        self.worker: ProcessWorker = None
        self.worker_thread: QThread = None
        
        self._init_ui()
        self._check_dependencies()
    
    def _init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Vertical)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        top_layout.addWidget(self._create_file_section())
        top_layout.addWidget(self._create_output_section())
        top_layout.addWidget(self._create_settings_section())
        top_layout.addWidget(self._create_controls_section())
        
        splitter.addWidget(top_widget)
        splitter.addWidget(self._create_log_section())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
    
    def _create_file_section(self) -> QGroupBox:
        """Create file picker section"""
        group = QGroupBox("Files")
        layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_add_files = QPushButton("Add Files...")
        self.btn_add_folder = QPushButton("Add Folder...")
        self.btn_remove = QPushButton("Remove Selected")
        self.btn_clear = QPushButton("Clear All")
        
        self.btn_add_files.clicked.connect(self._add_files)
        self.btn_add_folder.clicked.connect(self._add_folder)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear.clicked.connect(self._clear_queue)
        
        btn_layout.addWidget(self.btn_add_files)
        btn_layout.addWidget(self.btn_add_folder)
        btn_layout.addWidget(self.btn_remove)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.file_list)
        group.setLayout(layout)
        return group
    
    def _create_output_section(self) -> QGroupBox:
        """Create output settings section"""
        group = QGroupBox("Output")
        layout = QVBoxLayout()
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Output Folder:"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output folder...")
        default_output = os.path.join(os.path.expanduser("~"), "Music", "StemSlicer_Output")
        self.output_path.setText(default_output)
        
        self.btn_browse_output = QPushButton("Browse...")
        self.btn_browse_output.clicked.connect(self._browse_output)
        
        folder_layout.addWidget(self.output_path)
        folder_layout.addWidget(self.btn_browse_output)
        
        self.chk_open_folder = QCheckBox("Open output folder when done")
        self.chk_open_folder.setChecked(True)
        
        layout.addLayout(folder_layout)
        layout.addWidget(self.chk_open_folder)
        group.setLayout(layout)
        return group
    
    def _create_settings_section(self) -> QGroupBox:
        """Create separation settings section"""
        group = QGroupBox("Separation Settings")
        layout = QVBoxLayout()
        
        basic_layout = QHBoxLayout()
        
        basic_layout.addWidget(QLabel("Model:"))
        self.combo_model = QComboBox()
        self.combo_model.addItems(['htdemucs_ft', 'htdemucs', 'htdemucs_6s'])
        self.combo_model.setCurrentText('htdemucs_ft')
        basic_layout.addWidget(self.combo_model)
        
        basic_layout.addWidget(QLabel("Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(['Stems', 'Karaoke'])
        basic_layout.addWidget(self.combo_mode)
        
        basic_layout.addWidget(QLabel("Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(['Auto', 'CPU', 'CUDA'])
        basic_layout.addWidget(self.combo_device)
        self.combo_device.currentTextChanged.connect(self._on_device_changed)
        
        basic_layout.addWidget(QLabel("Quality:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(['Fast', 'Balanced', 'High', 'Ultra'])
        self.combo_quality.setCurrentText('Balanced')
        basic_layout.addWidget(self.combo_quality)
        
        basic_layout.addStretch()
        
        self.advanced_group = QGroupBox("Advanced Settings")
        self.advanced_group.setCheckable(True)
        self.advanced_group.setChecked(False)
        adv_layout = QHBoxLayout()
        
        adv_layout.addWidget(QLabel("Overlap:"))
        self.spin_overlap = QDoubleSpinBox()
        self.spin_overlap.setRange(0.0, 1.0)
        self.spin_overlap.setSingleStep(0.05)
        self.spin_overlap.setValue(0.25)
        self.spin_overlap.setToolTip("Higher values improve quality but increase processing time")
        adv_layout.addWidget(self.spin_overlap)
        
        adv_layout.addWidget(QLabel("Segment:"))
        self.spin_segment = QSpinBox()
        self.spin_segment.setRange(1, 100)
        self.spin_segment.setValue(8)
        self.spin_segment.setSpecialValueText("Default")
        self.spin_segment.setToolTip("Lower values use less GPU memory")
        adv_layout.addWidget(self.spin_segment)
        
        adv_layout.addWidget(QLabel("Jobs:"))
        self.spin_jobs = QSpinBox()
        self.spin_jobs.setRange(1, 16)
        self.spin_jobs.setValue(1)
        self.spin_jobs.setToolTip("Higher values use more RAM")
        adv_layout.addWidget(self.spin_jobs)
        
        adv_layout.addStretch()
        self.advanced_group.setLayout(adv_layout)
        
        layout.addLayout(basic_layout)
        layout.addWidget(self.advanced_group)
        group.setLayout(layout)
        return group
    
    def _create_controls_section(self) -> QGroupBox:
        """Create control buttons section"""
        group = QGroupBox("Controls")
        layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        self.btn_cancel = QPushButton("Cancel Current")
        self.btn_cancel.setEnabled(False)
        
        self.btn_start.clicked.connect(self._start_processing)
        self.btn_cancel.clicked.connect(self._cancel_processing)
        
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        
        self.lbl_current = QLabel("")
        self.lbl_current.setVisible(False)
        
        layout.addLayout(btn_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.lbl_current)
        group.setLayout(layout)
        return group
    
    def _create_log_section(self) -> QGroupBox:
        """Create log panel section"""
        group = QGroupBox("Log")
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("QTextEdit { font-family: 'Consolas', 'Courier New', monospace; }")
        
        btn_layout = QHBoxLayout()
        self.btn_copy_log = QPushButton("Copy Log")
        self.btn_copy_log.clicked.connect(self._copy_log)
        self.btn_clear_log = QPushButton("Clear Log")
        self.btn_clear_log.clicked.connect(self._clear_log)
        btn_layout.addWidget(self.btn_copy_log)
        btn_layout.addWidget(self.btn_clear_log)
        btn_layout.addStretch()
        
        layout.addWidget(self.log_text)
        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group
    
    def _check_dependencies(self):
        """Check and display dependency status"""
        status = self.runner.get_dependency_status()
        
        msg = "StemSlicer Ready\n\n"
        msg += f"FFmpeg: {'✓ Available' if status['ffmpeg'] else '✗ Not Found'}\n"
        msg += f"Demucs: {'✓ Available' if status['demucs'] else '✗ Not Found'}\n"
        msg += f"CUDA: {'✓ Available' if status['cuda'] else '✗ Not Available (CPU only)'}\n"
        
        if not status['ffmpeg'] or not status['demucs']:
            msg += "\n⚠ Missing dependencies detected!\n\n"
            
            if not status['ffmpeg']:
                msg += "FFmpeg is required for audio decoding.\n"
                msg += "Install: conda install -c conda-forge ffmpeg\n\n"
            
            if not status['demucs']:
                msg += "Demucs is required for stem separation.\n"
                msg += "Install: python -m pip install -U demucs SoundFile pyside6\n\n"
            
            msg += "The Start button will be disabled until dependencies are installed."
            self.btn_start.setEnabled(False)
            QMessageBox.warning(self, "Missing Dependencies", msg)
        else:
            self.btn_start.setEnabled(True)
        
        self._log(msg)
    
    def _on_device_changed(self, device: str):
        """Handle device selection change"""
        if device == 'CPU':
            current_quality = self.combo_quality.currentText()
            if current_quality in ['High', 'Ultra']:
                self.combo_quality.setCurrentText('Balanced')
    
    def _add_files(self):
        """Add files to queue"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.ogg *.aac);;All Files (*.*)"
        )
        
        for file_path in files:
            self._add_to_queue(file_path)
    
    def _add_folder(self):
        """Add folder contents to queue"""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            files = scan_audio_files(folder)
            self._log(f"Found {len(files)} audio files in folder")
            for file_path in files:
                self._add_to_queue(file_path)
    
    def _add_to_queue(self, file_path: str):
        """Add a file to the processing queue"""
        if any(item['path'] == file_path for item in self.file_queue):
            return
        
        self.file_queue.append({
            'path': file_path,
            'status': 'Queued',
            'name': os.path.basename(file_path)
        })
        
        item = QListWidgetItem(f"[Queued] {os.path.basename(file_path)}")
        self.file_list.addItem(item)
    
    def _remove_selected(self):
        """Remove selected files from queue"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            if 0 <= row < len(self.file_queue):
                del self.file_queue[row]
    
    def _clear_queue(self):
        """Clear all files from queue"""
        self.file_list.clear()
        self.file_queue.clear()
    
    def _browse_output(self):
        """Browse for output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_path.setText(folder)
    
    def _start_processing(self):
        """Start processing the queue"""
        if not self.file_queue:
            QMessageBox.warning(self, "No Files", "Please add files to the queue first.")
            return
        
        output_dir = self.output_path.text()
        if not output_dir:
            QMessageBox.warning(self, "No Output Folder", "Please select an output folder.")
            return
        
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self.file_queue))
        self.progress_bar.setValue(0)
        self.lbl_current.setVisible(True)
        
        self.current_processing_index = -1
        self._process_next_file()
    
    def _process_next_file(self):
        """Process the next file in queue"""
        self.current_processing_index += 1
        
        if self.current_processing_index >= len(self.file_queue):
            self._all_completed()
            return
        
        file_info = self.file_queue[self.current_processing_index]
        input_file = file_info['path']
        
        quality_map = {
            'Fast': (0, 0.10),
            'Balanced': (1, 0.25),
            'High': (2, 0.25),
            'Ultra': (4, 0.25)
        }
        
        quality = self.combo_quality.currentText()
        shifts, overlap = quality_map.get(quality, (1, 0.25))
        
        if self.advanced_group.isChecked():
            overlap = self.spin_overlap.value()
            segment = self.spin_segment.value() if self.spin_segment.value() > 1 else None
            jobs = self.spin_jobs.value()
        else:
            segment = None
            jobs = 1
        
        device = self.combo_device.currentText().lower()
        model = self.combo_model.currentText()
        two_stems = self.combo_mode.currentText() == 'Karaoke'
        
        command = self.runner.build_command(
            input_file=input_file,
            model=model,
            device=device,
            two_stems=two_stems,
            shifts=shifts,
            overlap=overlap,
            segment=segment,
            jobs=jobs
        )
        
        output_dir = self.output_path.text()
        
        self.worker_thread = QThread()
        self.worker = ProcessWorker()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker.log_output.connect(self._log)
        self.worker.progress_update.connect(self._update_progress)
        self.worker.file_completed.connect(self._on_file_completed)
        
        self.worker_thread.started.connect(
            lambda: self.worker.start_processing(
                self.current_processing_index,
                input_file,
                output_dir,
                command,
                self.runner
            )
        )
        
        self.worker_thread.start()
    
    def _update_progress(self, filename: str, status: str):
        """Update progress display"""
        self.lbl_current.setText(f"Now processing: {filename}")
    
    def _on_file_completed(self, index: int, status: str, success: bool):
        """Handle file completion"""
        if 0 <= index < len(self.file_queue):
            self.file_queue[index]['status'] = status
            item = self.file_list.item(index)
            if item:
                name = self.file_queue[index]['name']
                item.setText(f"[{status}] {name}")
        
        self.progress_bar.setValue(index + 1)
        
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
        
        if status != "Canceled":
            self._process_next_file()
        else:
            self._all_completed()
    
    def _all_completed(self):
        """Handle completion of all files"""
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_current.setText("Processing complete!")
        
        self._log("\n" + "="*60)
        self._log("All files processed!")
        
        done_count = sum(1 for f in self.file_queue if f['status'] == 'Done')
        failed_count = sum(1 for f in self.file_queue if f['status'] == 'Failed')
        canceled_count = sum(1 for f in self.file_queue if f['status'] == 'Canceled')
        
        self._log(f"Success: {done_count}, Failed: {failed_count}, Canceled: {canceled_count}")
        self._log("="*60)
        
        if self.chk_open_folder.isChecked() and done_count > 0:
            output_dir = self.output_path.text()
            if os.path.exists(output_dir):
                os.startfile(output_dir)
    
    def _cancel_processing(self):
        """Cancel current processing"""
        if self.worker:
            self.worker.cancel_current()
    
    def _log(self, message: str):
        """Add message to log"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def _copy_log(self):
        """Copy log to clipboard"""
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self.log_text.toPlainText())
        self._log("[Copied log to clipboard]")
    
    def _clear_log(self):
        """Clear log text"""
        self.log_text.clear()
