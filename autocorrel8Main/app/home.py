# Import necessary PyQt5 modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QFileDialog, QMessageBox, QListWidget, QTableWidget, QTableWidgetItem, 
)
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import sys
import os
import json
from pathlib import Path
import datetime
import shutil
from overviewDash import OverviewDashBoard
from themes import DARK_THEME, LIGHT_THEME


# Dark mode by default
CURRENT_THEME = 'dark'
THEME = DARK_THEME if CURRENT_THEME == 'dark' else LIGHT_THEME


# Top navigation bar
class TopNavBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(75)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['nav_bg']};
                border-bottom: 1px solid {THEME['border']};
            }}
        """)
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(40)

        # Title label
        title = QLabel("AutoCorrel8")
        title.setStyleSheet(f"""
            color: {THEME['accent']};
            font-size: 20px;
            font-weight: bold;
            border: none;
        """)
        layout.addWidget(title)

        # Cases and tool information buttons
        self.case_button = QLabel("Cases")
        self.case_button.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            border: none;
            padding: 5px 10px;
        """)
        self.case_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.case_button)
    
        self.tool_info_button = QLabel("Tool Information")
        self.tool_info_button.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            border: none;
            padding: 5px 10px;
        """)
        self.tool_info_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.tool_info_button)

        layout.addStretch()
        self.setLayout(layout)


# Case management
class CaseManagement(QFrame):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Case Management")
        self.setFixedSize(800, 600)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
            }}
        """)

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
        description_title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        left_layout.addWidget(description_title, alignment=Qt.AlignTop)

        description_text = QLabel(
            "Case management allows you to create new cases, "
            "organize existing ones, and streamline correlation analysis. "
            "Use the options on the right to get started."
        )
        description_text.setWordWrap(True)
        description_text.setStyleSheet(f"""
            font-size: 14px;
            color: {THEME['text_secondary']};
            border: none;
        """)
        left_layout.addWidget(description_text, alignment=Qt.AlignTop)

        # Right bordered section with title + buttons
        section_frame = QFrame()
        section_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {THEME['border']};
                background-color: {THEME['surface_elevated']};
                border-radius: 6px;
            }}
        """)
        section_layout = QVBoxLayout(section_frame)
        section_layout.setContentsMargins(20, 20, 20, 20)
        section_layout.setSpacing(20)

        # Title at the top inside the bordered section
        title = QLabel("Case Management")
        title.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        section_layout.addWidget(title, alignment=Qt.AlignTop)

        section_layout.addStretch(1)

        # Centered buttons
        self.create_case_button = QLabel("Create Case")
        self.create_case_button.setFixedWidth(320)
        self.create_case_button.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_primary']};
                font-size: 14px;
                border: 1px solid {THEME['border']};
                padding: 12px;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
                background-color: {THEME['button_bg']};
            }}
            QLabel:hover {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        self.create_case_button.setCursor(Qt.PointingHandCursor)
        section_layout.addWidget(self.create_case_button, alignment=Qt.AlignCenter)

        self.open_case_button = QLabel("Open Cases")
        self.open_case_button.setFixedWidth(320)
        self.open_case_button.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_primary']};
                font-size: 14px;
                border: 1px solid {THEME['border']};
                padding: 12px;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
                background-color: {THEME['button_bg']};
            }}
            QLabel:hover {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        self.open_case_button.setCursor(Qt.PointingHandCursor)
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
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
            }}
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title
        title = QLabel("Open Cases")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        main_layout.addWidget(title, alignment=Qt.AlignTop)

        # Buttons
        button_layout = QVBoxLayout()

        select_dir_button = QPushButton("Select Case Directory")
        select_dir_button.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 20px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        select_dir_button.clicked.connect(self.select_directory)
        button_layout.addWidget(select_dir_button)
        main_layout.addLayout(button_layout)
        
        # Case list widget
        self.case_list = QListWidget()
        self.case_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {THEME['surface_elevated']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {THEME['button_bg']};
            }}
            QListWidget::item:selected {{
                background-color: {THEME['button_checked']};
                color: {THEME['accent']};
            }}
        """)
        main_layout.addWidget(self.case_list)
        
        self.case_list.itemDoubleClicked.connect(self.open_selected_case)

        # Close button at the bottom
        close_button = QPushButton("Close")
        close_button.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 20px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        close_button.clicked.connect(self.close)

        main_layout.addStretch(1)
        main_layout.addWidget(close_button, alignment=Qt.AlignRight)
        
        self.setLayout(main_layout)

    # Open selected case
    def open_selected_case(self, item):
        
        # Extract case folder from selected item text
        case_text = item.text()
        case_folder_start = case_text.find("Case Directory: ") + len("Case Directory: ")
        case_folder_end = case_text.find(" - Notes:")
        case_folder = case_text[case_folder_start:case_folder_end]

        # Open overview dashboard with the selected case folder
        self.overview_dashboard = OverviewDashBoard(case_folder)
        self.overview_dashboard.show()
        self.close()

    # Select directory
    def select_directory(self):
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
                    case_dir = os.path.join(parent_dir, folder)
                    notes = data.get("investigator", {}).get("notes", "")
                    display_text = f"Case Name: {case_name} - Case Number: (#{case_number}) - Case Directory: {case_dir} - Notes: {notes[:50]}..."
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
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
            }}
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title
        title = QLabel("New Case")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        main_layout.addWidget(title, alignment=Qt.AlignTop)

        # Case Information Section
        case_info_label = QLabel("Case Information")
        case_info_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        main_layout.addWidget(case_info_label)

        case_form = QFormLayout()
        case_form.setLabelAlignment(Qt.AlignLeft)
        case_form.setFormAlignment(Qt.AlignLeft)
        case_form.setSpacing(10)

        # Style for form labels
        label_style = f"color: {THEME['text_primary']}; border: none;"

        self.case_name = QLineEdit()
        self.case_number = QLineEdit()
        
        # Case Directory with Browse button
        self.case_directory = QLineEdit()
        self.select_dir_button = QPushButton("Browse...")
        self.select_dir_button.setStyleSheet(f"""
            QPushButton {{
                padding: 6px 12px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        self.select_dir_button.clicked.connect(self.select_directory)

        case_dir_layout = QHBoxLayout()
        case_dir_layout.addWidget(self.case_directory) 
        case_dir_layout.addWidget(self.select_dir_button) 

        # Create labels with proper styling
        dir_label = QLabel("Case Directory:")
        dir_label.setStyleSheet(label_style)
        name_label = QLabel("Case Name:")
        name_label.setStyleSheet(label_style)
        number_label = QLabel("Case Number:")
        number_label.setStyleSheet(label_style)

        case_form.addRow(dir_label, case_dir_layout)
        case_form.addRow(name_label, self.case_name)
        case_form.addRow(number_label, self.case_number)

        main_layout.addLayout(case_form)

        # Investigator Section
        investigator_label = QLabel("Investigator")
        investigator_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
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

        # Create investigator labels with styling
        inv_name_label = QLabel("Name:")
        inv_name_label.setStyleSheet(label_style)
        inv_email_label = QLabel("Email:")
        inv_email_label.setStyleSheet(label_style)
        inv_phone_label = QLabel("Phone:")
        inv_phone_label.setStyleSheet(label_style)
        inv_notes_label = QLabel("Notes:")
        inv_notes_label.setStyleSheet(label_style)

        investigator_form.addRow(inv_name_label, self.investigator_name)
        investigator_form.addRow(inv_email_label, self.investigator_email)
        investigator_form.addRow(inv_phone_label, self.investigator_phone)
        investigator_form.addRow(inv_notes_label, self.investigator_notes)

        main_layout.addLayout(investigator_form)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignRight)

        cancel_button = QPushButton("Cancel")
        finish_button = QPushButton("Next")

        button_style = f"""
            QPushButton {{
                padding: 8px 20px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """
        cancel_button.setStyleSheet(button_style)
        finish_button.setStyleSheet(button_style)

        cancel_button.clicked.connect(self.close)
        finish_button.clicked.connect(self.submit_case)

        button_layout.addWidget(cancel_button)
        button_layout.addWidget(finish_button)

        main_layout.addStretch(1)
        main_layout.addLayout(button_layout)

        # Apply input field styling
        input_style = f"""
            QLineEdit, QTextEdit {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                padding: 6px;
                border-radius: 4px;
                color: {THEME['text_primary']};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {THEME['accent']};
            }}
        """
        self.setStyleSheet(self.styleSheet() + input_style)
        
        self.setLayout(main_layout)

    # Select directory
    def select_directory(self):
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
        
        if not case_data["case_number"].isdigit():
            QMessageBox.warning(self, "Invalid Case Number", "Case Number must be numeric.")
            return
        
        metadata_path = self.create_case_folder(case_data)

        if metadata_path:
            QMessageBox.information(self, "Case Created", f"Case created successfully at:\n{metadata_path}")
            self.close()

            # Build full case folder path
            case_folder = os.path.join(case_data["directory"], f"Case_{case_data['case_number']}")

            # Open file upload popup with case folder
            self.file_upload_popup = FileUploadPopup(case_folder)
            self.file_upload_popup.show()


# Drag-and-drop file
class DropBox(QFrame):
    fileDropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Enable drag-and-drop on this widget
        self.setAcceptDrops(True)

        # Set fixed size and visual style
        self.setFixedSize(100, 100)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['button_bg']};
                border: 2px dashed {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Add a label to display instructions or uploaded file name
        self.label = QLabel("Drop files here", self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setGeometry(0, 0, 100, 100)
        self.label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 9px;
            border: none;
        """)

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
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {THEME['button_checked']};
                    border: 2px dashed {THEME['accent']};
                    border-radius: 6px;
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['button_bg']};
                border: 2px dashed {THEME['border']};
                border-radius: 6px;
            }}
        """)

    # Triggered when a file is dropped onto the widget
    def dropEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['button_bg']};
                border: 2px dashed {THEME['border']};
                border-radius: 6px;
            }}
        """)
        
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        
        file_type = self.routeFile(files[0])

        print(f"Detected file type: {file_type}")

        if file_type == "unsupported file type":
            self.label.setText("Unsupported\nfile type")
            return
            
        self.label.setText(f"Uploaded:\n{Path(files[0]).name}")
        self.fileDropped.emit(files[0])


# File upload pop up
class FileUploadPopup(QFrame):
    def __init__(self, case_folder):
        super().__init__()
        
        self.case_folder = case_folder

        self.setWindowTitle("Upload Files")
        self.setFixedSize(600, 500)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
            }}
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(25)

        # Title
        title = QLabel("Upload Files")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {THEME['text_primary']};
            border: none;
        """)
        main_layout.addWidget(title, alignment=Qt.AlignTop)

        # Add drop box
        self.drop_box = DropBox()
        self.drop_box.fileDropped.connect(self.handle_file_dropped)

        # Upload button
        upload_button = QPushButton("Select Files to Upload")
        upload_button.setStyleSheet(f"""
            QPushButton {{
                padding: 8px 20px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """)
        upload_button.clicked.connect(self.upload_files)
        main_layout.addWidget(upload_button)

        main_layout.addWidget(self.drop_box, alignment=Qt.AlignCenter)

        # Table of uploaded file paths
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(["Uploaded File Paths", "File Size (MB)"])
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.setColumnWidth(0, 450)  
        self.file_table.setColumnWidth(1, 100)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['surface_elevated']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                gridline-color: {THEME['border']};
            }}
            QTableWidget::item {{
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {THEME['button_checked']};
                color: {THEME['accent']};
            }}
            QHeaderView::section {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                padding: 5px;
                border: 1px solid {THEME['border']};
                font-weight: bold;
            }}
        """)
        main_layout.addWidget(self.file_table)

        # Buttons at the bottom
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        button_layout.setAlignment(Qt.AlignRight)

        close_button = QPushButton("Close")
        finish_button = QPushButton("Finish")

        button_style = f"""
            QPushButton {{
                padding: 8px 20px;
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """
        close_button.setStyleSheet(button_style)
        finish_button.setStyleSheet(button_style)

        button_layout.addWidget(close_button)
        button_layout.addWidget(finish_button)


        close_button.clicked.connect(self.close)
        finish_button.clicked.connect(self.open_new_screen)

        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def open_new_screen(self):
            current_case_path = self.case_folder
            self.new_window = CorrelationDashBoard(current_case_path)
            self.new_window.show()
            self.close()

    def handle_file_dropped(self, file_path):
            current_rows = self.file_table.rowCount()
            self.file_table.setRowCount(current_rows + 1)

            row = current_rows
            
            # File path
            self.file_table.setItem(row, 0, QTableWidgetItem(file_path))

            self.save_files_to_evidence()

            # File size in MB
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                self.file_table.setItem(row, 1, QTableWidgetItem(f"{size_mb:.2f}"))
            except Exception:
                self.file_table.setItem(row, 1, QTableWidgetItem("Error"))

    def upload_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files to Upload")
        
        file_type = self.routeFile(files[0]) if files else None

        if file_type == "unsupported file type":
            self.drop_box.label.setText("Unsupported file type")
            return
        
        if files:
            current_rows = self.file_table.rowCount()
            self.file_table.setRowCount(current_rows + len(files))

            for i, file_path in enumerate(files):
                row = current_rows + i
                
                # File path
                self.file_table.setItem(row, 0, QTableWidgetItem(file_path))

                # File size in MB
                try:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    self.file_table.setItem(row, 1, QTableWidgetItem(f"{size_mb:.2f}"))
                except Exception:
                    self.file_table.setItem(row, 1, QTableWidgetItem("Error"))

            self.save_files_to_evidence()

    # Save files to evidence folder
    def save_files_to_evidence(self):
        
        evidence_dir = os.path.join(self.case_folder, "evidence")
        os.makedirs(evidence_dir, exist_ok=True)

        for row in range(self.file_table.rowCount()):
            file_path_item = self.file_table.item(row, 0)
            if file_path_item:
                file_path = file_path_item.text()
                try:
                    shutil.copy(file_path, evidence_dir)
                except Exception as e:
                    print(f"Error copying {file_path} to evidence folder: {e}")

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
        content_container.setStyleSheet(f"background-color: {THEME['background']};")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 20, 0, 0)  
        content_layout.setSpacing(10)
        content_layout.setAlignment(Qt.AlignCenter)      

        # Main content area
        content_area = QLabel("Welcome to AutoCorrel8 Dashboard")
        content_area.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {THEME['text_primary']};")
        content_area.setAlignment(Qt.AlignCenter)

        # Description label
        description = QLabel(
            "AutoCorrel8 is an automated tool for correlation analysis. "
            "Click on 'Cases' to manage your datasets or 'Tool Information' to learn more."
        )
        description.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 16px;")
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
