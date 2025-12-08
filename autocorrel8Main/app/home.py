# Import necessary PyQt5 modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QFileDialog, QMessageBox, QListWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import sys
import os
import json
from pathlib import Path
import datetime
import shutil


# Top navigation bar
class TopNavBar(QFrame):
    def __init__(self):
        
        # Top navigation bar setup
        super().__init__()
        self.setFixedHeight(75)
        self.setStyleSheet("background-color: ##F5F5F5; border: 1px solid #E0E0E0;")
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(40)

        # Title label
        title = QLabel("AutoCorrel8")
        title.setStyleSheet("color: black; font-size: 18px; font-weight: bold; border: none;")
        layout.addWidget(title)

        
        # Cases and tool information buttons
        self.case_button = QLabel("Cases")
        self.case_button.setStyleSheet("color: black; font-size: 14px; border: none;")
        layout.addWidget(self.case_button)
    
        self.tool_info_button = QLabel("Tool Information")
        self.tool_info_button.setStyleSheet("color: black; font-size: 14px; border: none;")
        layout.addWidget(self.tool_info_button)


        layout.addStretch()

        self.setLayout(layout)

# Case management
class CaseManagement(QFrame):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Case Management")
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: #F5F5F5; border: 1px solid #E0E0E0;")

        # Main horizontal layout for two columns
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Left description section 
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_frame.setStyleSheet("border: none;")

        description_title = QLabel("About Case Management")
        description_title.setStyleSheet("font-size: 16px; font-weight: bold; color: black; border: none;")
        left_layout.addWidget(description_title, alignment=Qt.AlignTop)

        description_text = QLabel(
            "Case management allows you to create new cases, "
            "organize existing ones, and streamline correlation analysis. "
            "Use the options on the right to get started."
        )
        description_text.setWordWrap(True)
        description_text.setStyleSheet("font-size: 14px; color: #333333; border: none;")
        left_layout.addWidget(description_text, alignment=Qt.AlignTop)

        # Right bordered section with title + buttons
        section_frame = QFrame()
        section_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #A0A0A0;
                background-color: #FFFFFF;
            }
        """)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(20, 20, 20, 20)
        section_layout.setSpacing(20)

        # Title at the top inside the bordered section
        title = QLabel("Case Management")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: black; border: none;")
        section_layout.addWidget(title, alignment=Qt.AlignTop)

        section_layout.addStretch(1)

        # Centered buttons
        self.create_case_button = QLabel("Create Case")
        self.create_case_button.setFixedWidth(320)
        self.create_case_button.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 14px;
                border: 1px solid #A0A0A0;
                padding: 12px;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
            QLabel:hover { background-color: #F5F5F5; }
        """)
        section_layout.addWidget(self.create_case_button, alignment=Qt.AlignCenter)

        self.open_case_button = QLabel("Open Cases")
        self.open_case_button.setFixedWidth(320)
        self.open_case_button.setStyleSheet("""
            QLabel {
                color: black;
                font-size: 14px;
                border: 1px solid #A0A0A0;
                padding: 12px;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
            QLabel:hover { background-color: #F5F5F5; }
        """)
        section_layout.addWidget(self.open_case_button, alignment=Qt.AlignCenter)

        section_layout.addStretch(1)

        # Add both left and right sections to main layout
        main_layout.addWidget(left_frame, stretch=1)     
        main_layout.addWidget(section_frame, stretch=2)  

        # Create create function
        def create_case(event):
            self.close()
            self.create_case_popup = CreateCase()
            self.create_case_popup.show()

        # Create open function
        def open_cases(event):
            self.close()
            self.open_cases_popup = OpenCases()
            self.open_cases_popup.show()

        # Connect case button to open popup
        self.create_case_button.mousePressEvent = create_case
        self.open_case_button.mousePressEvent = open_cases
        
        self.setLayout(main_layout)

# Open existing cases pop up
class OpenCases(QFrame):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open Cases")
        self.setFixedSize(600, 400)
        self.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title
        title = QLabel("Open Cases")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: black; border: none;")
        main_layout.addWidget(title, alignment=Qt.AlignTop)

        # Buttons
        button_layout = QVBoxLayout()

        select_dir_button = QPushButton("Select Case Directory")
        select_dir_button.setStyleSheet("padding: 8px 20px;")
        select_dir_button.clicked.connect(self.select_directory)
        button_layout.addWidget(select_dir_button)
        main_layout.addLayout(button_layout)
        
        # Case list widget
        self.case_list = QListWidget()
        self.case_list.setStyleSheet("background-color: white; border: 1px solid #A0A0A0;")
        main_layout.addWidget(self.case_list)
        
        # Close button at the bottom
        close_button = QPushButton("Close")
        close_button.setStyleSheet("padding: 8px 20px;")
        close_button.clicked.connect(self.close)

        main_layout.addStretch(1)
        main_layout.addWidget(close_button, alignment=Qt.AlignRight)

        self.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                font-size: 14px;
                color: black;
            }
            QFrame, QWidget {
                background-color: #F5F5F5;  
            }
        """)
        
        self.setLayout(main_layout)

    # Select directory
    def select_directory(self):
        # Let user choose the parent folder
        directory = QFileDialog.getExistingDirectory(self, "Select Case Directory")
        if directory:
            self.load_cases(directory)

    def load_cases(self, parent_dir):
        self.case_list.clear()

        if not os.path.exists(parent_dir):
            QMessageBox.information(self, "No Cases", f"Folder not found:\n{parent_dir}")
            return

        # List all subfolders
        case_folders = [f for f in os.listdir(parent_dir)
                        if os.path.isdir(os.path.join(parent_dir, f))]

        if not case_folders:
            QMessageBox.information(self, "No Cases", "No case folders found in the selected directory.")
            return

        for folder in case_folders:
            metadata_path = os.path.join(parent_dir, folder, "metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        data = json.load(f)
                    case_name = data.get("case_name", "Unknown")
                    case_number = data.get("case_number", "Unknown")
                    notes = data.get("investigator", {}).get("notes", "")
                    # Format display text
                    display_text = f"Case Name: {case_name} - Case Number: (#{case_number}) - Notes: {notes[:50]}..."
                    self.case_list.addItem(display_text)
                except Exception as e:
                    self.case_list.addItem(f"{folder} (error reading metadata)")
            else:
                self.case_list.addItem(f"{folder} (no metadata.json)")



# Create new case pop up
class CreateCase(QFrame):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New Case")
        self.setFixedSize(800, 650)
        self.setStyleSheet("background-color: #F5F5F5; border: 1px solid #CCCCCC;")

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title
        title = QLabel("New Case")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: black; border: none;")
        main_layout.addWidget(title, alignment=Qt.AlignTop)

        # Case Information Section
        case_info_label = QLabel("Case Information")
        case_info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: black; border: none;")
        main_layout.addWidget(case_info_label)

        case_form = QFormLayout()
        case_form.setLabelAlignment(Qt.AlignLeft)
        case_form.setFormAlignment(Qt.AlignLeft)
        case_form.setSpacing(10)

        self.case_name = QLineEdit()
        self.case_number = QLineEdit()
        
        # Case Directory with Browse button
        self.case_directory = QLineEdit()
        self.select_dir_button = QPushButton("Browse...")
        self.select_dir_button.clicked.connect(self.select_directory)

        case_dir_layout = QHBoxLayout()
        case_dir_layout.addWidget(self.case_directory) 
        case_dir_layout.addWidget(self.select_dir_button) 

        case_form.addRow("Case Directory:", case_dir_layout)

        case_form.addRow("Case Name:", self.case_name)
        case_form.addRow("Case Number:", self.case_number)
        

        main_layout.addLayout(case_form)

        # Investigator Section
        investigator_label = QLabel("Investigator")
        investigator_label.setStyleSheet("font-size: 16px; font-weight: bold; color: black; border: none;")
        main_layout.addWidget(investigator_label)

        investigator_form = QFormLayout()
        investigator_form.setLabelAlignment(Qt.AlignLeft)
        investigator_form.setFormAlignment(Qt.AlignLeft)
        investigator_form.setSpacing(10)

        self.investigator_name = QLineEdit()
        self.investigator_email = QLineEdit()
        self.investigator_phone = QLineEdit()
        self.investigator_notes = QTextEdit()
        self.investigator_notes.setFixedHeight(80)

        investigator_form.addRow("Name:", self.investigator_name)
        investigator_form.addRow("Email:", self.investigator_email)
        investigator_form.addRow("Phone:", self.investigator_phone)
        investigator_form.addRow("Notes:", self.investigator_notes)
        

        main_layout.addLayout(investigator_form)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignRight)

        cancel_button = QPushButton("Cancel")
        finish_button = QPushButton("Finish")

        cancel_button.setStyleSheet("padding: 8px 20px; ")
        finish_button.setStyleSheet("padding: 8px 20px;")

        cancel_button.clicked.connect(self.close)
        finish_button.clicked.connect(self.submit_case)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(finish_button)

        main_layout.addStretch(1)
        main_layout.addLayout(button_layout)

        self.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
                font-size: 14px;
                color: black;
            }
            QFrame, QWidget {
                background-color: #F5F5F5;  
            }
            QLineEdit, QTextEdit {
                background-color: white;   
                border: 1px solid #A0A0A0;
                padding: 6px;
                border-radius: 4px;
            }
        """)
        
        self.setLayout(main_layout)

    # Select directory
    def select_directory(self):
        
        # Open file dialog to select directory
        directory = QFileDialog.getExistingDirectory(self, "Select Case Directory")
        if directory:
            self.case_directory.setText(directory) 

    def create_case_folder(self, case_data):
        
        parent_dir = case_data["directory"]
        case_folder = os.path.join(parent_dir, f"Case_{case_data['case_number']}")

        # Check for duplicate case number
        if os.path.exists(case_folder):
            QMessageBox.warning(self, "Duplicate Case", "A case with this number already exists.")
            return None
    
        # Create folder + subfolders
        os.makedirs(os.path.join(case_folder, "evidence"), exist_ok=True)
        os.makedirs(os.path.join(case_folder, "reports"), exist_ok=True)
        os.makedirs(os.path.join(case_folder, "notes"), exist_ok=True)

        
        # Save metadata.json
        metadata_path = os.path.join(case_folder, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(case_data, f, indent=4)

        return metadata_path
    
    def submit_case(self):
        
        # Create case folder
        case_data = {
            "directory": self.case_directory.text(),
            "case_name": self.case_name.text(),
            "case_number": self.case_number.text(),
            "investigator": {
                "name": self.investigator_name.text(),
                "email": self.investigator_email.text(),
                "phone": self.investigator_phone.text(),
                "notes": self.investigator_notes.toPlainText()
            },
            "created_at": datetime.datetime.now().isoformat()
        }

        # Validate required fields
        if not case_data["case_name"] or not case_data["case_number"] or not case_data["directory"]:
            QMessageBox.warning(self, "Missing Information", "Case Name, Number, and Directory are required.")
            return

        if not os.path.isdir(case_data["directory"]):
            QMessageBox.warning(self, "Invalid Directory", "Please select a valid directory.")
            return
        
        
        metadata_path = self.create_case_folder(case_data)

        if metadata_path:
            QMessageBox.information(self, "Case Created", f"Case created successfully at:\n{metadata_path}")
            self.close()




# Main application window
class AutoCorrel8Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set window title and size
        self.setWindowTitle("AutoCorrel8 Dashboard")
        self.setGeometry(100, 100, 1920, 1080)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Main content + description container
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(5)  

        # Top navigation bar
        top_nav = TopNavBar()
        main_layout.addWidget(top_nav)

        # Main content + description container
        content_container = QWidget()
        content_container.setStyleSheet("background-color: #F5F5F5;") 
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 20, 0, 0)  
        content_layout.setSpacing(10)
        content_layout.setAlignment(Qt.AlignCenter)      

        # Main content area
        content_area = QLabel("Welcome to AutoCorrel8 Dashboard")
        content_area.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        content_area.setAlignment(Qt.AlignCenter)

        # Description label
        description = QLabel(
            "AutoCorrel8 is an automated tool for correlation analysis. "
            "Click on 'Cases' to manage your datasets or 'Tool Information' to learn more."
        )
        description.setStyleSheet("color: black; font-size: 16px;")
        description.setAlignment(Qt.AlignCenter)

        # Add both to the content layout
        content_layout.addWidget(content_area)
        content_layout.addWidget(description)

        # Add the container to the main layout
        main_layout.addWidget(content_container)

        # Function to open case creation popup
        def open_case_creation_popup(event):
            self.case_popup = CaseManagement()
            self.case_popup.show()

        # Connect case button to open popup
        top_nav.case_button.mousePressEvent = open_case_creation_popup


        



# Start the application 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoCorrel8Dashboard()
    window.show()
    sys.exit(app.exec())
