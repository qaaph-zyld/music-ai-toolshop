"""Worker thread for processing audio files with Demucs"""
import os
import subprocess
from datetime import datetime
from typing import Optional
from PySide6.QtCore import QObject, Signal, QProcess


class ProcessWorker(QObject):
    """Worker that runs Demucs subprocess and emits signals for UI updates"""
    
    log_output = Signal(str)
    progress_update = Signal(str, str)
    file_completed = Signal(int, str, bool)
    all_completed = Signal()
    
    def __init__(self):
        super().__init__()
        self.process: Optional[QProcess] = None
        self.current_file_index = -1
        self.is_cancelled = False
        self.start_time: Optional[datetime] = None
    
    def start_processing(
        self,
        file_index: int,
        input_file: str,
        output_dir: str,
        command: list,
        runner
    ):
        """Start processing a single file"""
        self.current_file_index = file_index
        self.is_cancelled = False
        self.start_time = datetime.now()
        
        filename = os.path.basename(input_file)
        self.progress_update.emit(filename, "Running")
        self.log_output.emit(f"\n{'='*60}")
        self.log_output.emit(f"Processing: {filename}")
        self.log_output.emit(f"Command: {' '.join(command)}")
        self.log_output.emit(f"Output directory: {output_dir}")
        self.log_output.emit(f"{'='*60}\n")
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.process = QProcess()
        self.process.setWorkingDirectory(output_dir)
        
        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(lambda exit_code, exit_status: self._handle_finished(
            exit_code, exit_status, input_file, output_dir, runner
        ))
        
        self.process.start(command[0], command[1:])
    
    def _handle_stdout(self):
        """Handle standard output from process"""
        if self.process:
            data = self.process.readAllStandardOutput().data()
            try:
                text = data.decode('utf-8', errors='replace')
                self.log_output.emit(text)
            except Exception as e:
                self.log_output.emit(f"[Decode error: {e}]")
    
    def _handle_stderr(self):
        """Handle standard error from process"""
        if self.process:
            data = self.process.readAllStandardError().data()
            try:
                text = data.decode('utf-8', errors='replace')
                self.log_output.emit(text)
            except Exception as e:
                self.log_output.emit(f"[Decode error: {e}]")
    
    def _handle_finished(self, exit_code: int, exit_status, input_file: str, output_dir: str, runner):
        """Handle process completion"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        if self.is_cancelled:
            self.log_output.emit(f"\n[CANCELLED] Processing was cancelled by user")
            status = "Canceled"
            success = False
        elif exit_code == 0:
            self.log_output.emit(f"\n[SUCCESS] Completed in {duration:.1f} seconds")
            status = "Done"
            success = True
            
            try:
                model = 'htdemucs_ft'
                expected_output = runner.get_output_path(output_dir, model, input_file)
                self.log_output.emit(f"Output location: {expected_output}")
            except Exception as e:
                self.log_output.emit(f"Note: {e}")
        else:
            self.log_output.emit(f"\n[FAILED] Process exited with code {exit_code}")
            status = "Failed"
            success = False
        
        self.file_completed.emit(self.current_file_index, status, success)
        self.process = None
    
    def cancel_current(self):
        """Cancel the currently running process"""
        if self.process and self.process.state() == QProcess.Running:
            self.is_cancelled = True
            self.log_output.emit("\n[CANCELLING] Stopping process...")
            self.process.terminate()
            
            self.process.waitForFinished(3000)
            
            if self.process.state() == QProcess.Running:
                self.log_output.emit("[FORCE KILL] Process did not terminate, killing...")
                self.process.kill()
                self.process.waitForFinished(1000)
