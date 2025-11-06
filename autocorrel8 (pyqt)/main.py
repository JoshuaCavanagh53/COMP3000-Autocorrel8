# Import necessary PyQt5 modules
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QFrame, QLabel
from PyQt5.QtCore import Qt
import sys
from pathlib import Path

# Custom QFrame subclass that for drag-and-drop feature
class DropBox(QFrame):
    def __init__(self):
        super().__init__()

        # Enable drag-and-drop on this widget
        self.setAcceptDrops(True)

        # Set fixed size and visual style
        self.setFixedSize(300, 300)
        self.setStyleSheet("background-color: #d3d3d3; border: 2px solid #333;")

        # Add a label to display instructions or uploaded file name
        self.label = QLabel("Drop files here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, 300, 300)

    # File type detection
    @staticmethod
    def routeFile(file_path):
        
        ext = Path(file_path).suffix.lower()

        if ext == ".pcap":
            return "zeek"
        elif ext == ".evtx":
            return "windows_event_parser"
        elif ext == ".log":
            return "syslog_parser"
        elif ext == ".sqlite":
            return "browser_parser"
        else: 
            return "unsupported file type"
        
    # Triggered when a dragged item enters the widget
    def dragEnterEvent(self, event):
        # Accept only if the dragged item contains file URLs
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    # Triggered when a file is dropped onto the widget
    def dropEvent(self, event):
        # Extract local file paths from the dropped URLs
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        
        file_type = self.routeFile(files[0])

        print(f"Detected file type: {file_type}")

        # Display the first uploaded file path in the label
        self.label.setText(f"Uploaded:\n{files[0]}")

        

# Main application window
class AutoCorrel8Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()

        # Set window title and size
        self.setWindowTitle("AutoCorrel8 Dashboard")
        self.setGeometry(100, 100, 800, 1000)

        # Create a central widget to hold layout and content
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Use a vertical layout and center its contents
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)

        # Add the drag-and-drop box to the layout
        self.drop_box = DropBox()
        layout.addWidget(self.drop_box)

# Start the application 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoCorrel8Dashboard()
    window.show()
    sys.exit(app.exec())
