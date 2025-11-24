# Import necessary PyQt5 modules
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QFrame, QLabel, QHBoxLayout, QPushButton, QSizePolicy, QToolButton, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5 import QtGui
import sys
from pathlib import Path
import datetime
import shutil
# Import normalized schema
from schemas.normalized_schema import NormalizedRecord

# Custom QFrame subclass that for drag-and-drop feature
class DropBox(QFrame):
    
    fileDropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Enable drag-and-drop on this widget
        self.setAcceptDrops(True)

        # Set up upload button
    

        # Set fixed size and visual style
        self.setFixedSize(200, 200)
        self.setStyleSheet("background-color: #d3d3d3; border: 2px solid #333;")

        # Add a label to display instructions or uploaded file name
        self.label = QLabel("Drop files here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, 200, 200)

    # File type detection
    @staticmethod
    def routeFile(file_path):
        
        ext = Path(file_path).suffix.lower()

        if ext == ".pcap":
            return "pcap"
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

        # Display if file is uploaded successfully or unsupported
        if file_type == "unsupported file type":
            self.label.setText("Unsupported file type")
            return
        # Display the first uploaded file path in the label
        self.label.setText(f"Uploaded:\n{files[0]}")

        # Emit signal with the first file path
        self.fileDropped.emit(files[0])  



class FileTable(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # Create table with 5 columns
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Filename", "Timestamp", "Path", "File Type", "Size", "Action"
        ])
        self.table.setRowCount(0)
        
        # Ensure table expands inside its container
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Ensure all columns stretch to fill avaiable space
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Hide row indexing
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)

    # Method to populate table with the file data
    def add_file_entry(self, filename, timestamp, path, file_type, size):
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(filename))
        self.table.setItem(row_position, 1, QTableWidgetItem(timestamp))
        self.table.setItem(row_position, 2, QTableWidgetItem(path))
        self.table.setItem(row_position, 3, QTableWidgetItem(file_type))
        self.table.setItem(row_position, 4, QTableWidgetItem(size))

        # Add delete button while accounting for changing row posistions
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(lambda _, row=row_position: self.delete_file_entry(row))
        self.table.setCellWidget(row_position, 5, delete_button)

    # Delete table entry
    def delete_file_entry(self, row):
        self.table.removeRow(row)



        

# Create collapsible headings e.g. 'Action' heading
class CollapsibleSection(QWidget):
    def __init__(self, title, children):
        super().__init__()
        
        self.toggle = QToolButton(text=title)
        
        # Style the collapsible sections
        self.toggle.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                color: black;
                font-weight: bold;
                padding: 8px;
                text-align: left;
            }
            QToolButton::menu-indicator {
                image: none;
            }
        """)

        # Handle selection logic
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(False)
        self.toggle.clicked.connect(self.toggle_content)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)

        for name in children:
            btn = QPushButton(name)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: black;
                    padding: 6px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #b0b0b0 ;
                }
            """)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            content_layout.addWidget(btn)

        # Hide collapsible content when not selected
        self.content.setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toggle)
        layout.addWidget(self.content)

    def toggle_content(self):
        self.content.setVisible(self.toggle.isChecked())

# Create the sidemenu bar
class SideMenu(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("SideMenu")

        # Style the sidebar
        self.setStyleSheet("""
        
            QWidget#SideMenu {
                background-color: #b0b0b0;
            }       
                           
            QLabel {
                background-color: transparent;
                color: black;
                text-align: left;
                font-weight: bold;
                font-size: 20px;
                padding: 8px;
            }
        
            QToolButton {
                background-color: transparent;
                color: black;
                font-weight: bold;
                padding: 8px;
                text-align: left;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QPushButton {
                background-color: transparent;
                color: black;
                padding: 6px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #b0b0b0;
            }
          
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Menu"))
        layout.addWidget(CollapsibleSection("Actions", [
            "File Upload", "Network", "System Log", "Registry", "Correlation"
        ]))

        layout.addWidget(CollapsibleSection("Information", [
            "Tool Information"
        ]))

        layout.addStretch()
        self.setLayout(layout)

# Main application window
class AutoCorrel8Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window title and size
        self.setWindowTitle("AutoCorrel8 Dashboard")
        self.setGeometry(100, 100, 1000, 800)

        # Create a central widget to hold layout and content
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Top-level horizontal layout: sidebar + main content
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar (15% width)
        self.sidebar = SideMenu()
        self.sidebar.setFixedWidth(int(self.width() * 0.15))
       
        main_layout.addWidget(self.sidebar)

        # Main content area (title + drop box)
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Center horizontally, top vertically
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # Title
        self.title = QLabel("AutoCorrel8 Forensics Dashboard")
        self.title.setFont(QFont("Arial", 16, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)  # Center the text within the label
        content_layout.addWidget(self.title)

        # Screen title
        self.screen_title = QLabel("File Upload")
        self.screen_title.setFont(QFont("Arial", 14, QFont.Bold))
        self.screen_title.setAlignment(Qt.AlignCenter)  # Center the text within the label
        content_layout.addWidget(self.screen_title)

        # Drop box
        self.drop_box = DropBox()
        content_layout.addWidget(self.drop_box, alignment=Qt.AlignHCenter)  # Center the box horizontally
        self.drop_box.fileDropped.connect(self.handle_dropped_file)

        # Add file table
        self.file_table = FileTable()
        content_layout.addWidget(self.file_table)
     

        main_layout.addWidget(content_area)

    # Parse pcap file into normalized schema
    def parse_pcap_to_normalized_schema(self, pcap_file_path):
        pass
        
    def save_uploaded_file(self, file_path: str, filename: str):
        # Resolve the input folder 
        input_folder = Path(__file__).resolve().parent.parent / "zeek_data" / "input"
        input_folder.mkdir(parents=True, exist_ok=True)  # ensure folder exists

        dest_path = input_folder / filename

        # Copy file safely
        with open(file_path, "rb") as src_file, open(dest_path, "wb") as dest_file:
            shutil.copyfileobj(src_file, dest_file)

        print(f"File saved to {dest_path}")
        return dest_path
        
    # Handle the data from a dropped file
    def handle_dropped_file(self, file_path):

        # Try and open the file, reading its contents and add them to the table using the add_file_entry method
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                path_obj = Path(file_path)
                filename = path_obj.name
                path = str(path_obj.resolve())
                size = f"{path_obj.stat().st_size / (1024 * 1024):.2f} MB"
                timestamp = datetime.datetime.fromtimestamp(path_obj.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                file_type = DropBox.routeFile(file_path)
                
                if file_type == "unsupported file type":
                    # Output error message 
                    print("Unsupported file type uploaded.")
                    return
                self.file_table.add_file_entry(filename, timestamp, path, file_type, size)

                
                # Save the uploaded file to the input directory
                saved_path = self.save_uploaded_file(file_path, filename)
                print(f"File {filename} uploaded and saved to {saved_path}")
                
        except Exception as e:
            print("Error reading file:", e)



# Start the application 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoCorrel8Dashboard()
    window.show()
    sys.exit(app.exec())
