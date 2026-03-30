"""StemSlicer - Main application entry point"""
import sys
from PySide6.QtWidgets import QApplication
from .ui_main import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("StemSlicer")
    app.setOrganizationName("StemSlicer")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
