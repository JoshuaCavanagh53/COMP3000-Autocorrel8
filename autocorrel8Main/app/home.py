# Import necessary PyQt5 modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit, QTextEdit,
    QPushButton, QVBoxLayout, QHBoxLayout, QFormLayout, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import sys
from pathlib import Path
import datetime
import shutil


# Top navigation bar
class TopNavBar(QFrame):
    def __init__(self):
        
        # Top navigation bar setup
        super().__init__()
        self.setFixedHeight(75)
        self.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E0E0E0;")
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
        self.setStyleSheet("background-color: white; border: 1px solid #E0E0E0;")

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

        # Connect case button to open popup
        self.create_case_button.mousePressEvent = create_case
        
        self.setLayout(main_layout)

# Create new case pop up
class CreateCase(QFrame):
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New Case")
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: white; border: 1px solid #CCCCCC;")

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
        self.case_directory = QLineEdit()

        case_form.addRow("Case Name:", self.case_name)
        case_form.addRow("Case Number:", self.case_number)
        case_form.addRow("Case Directory:", self.case_directory)

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
                background-color: white;   /* keep window background white */
            }
            QLineEdit, QTextEdit {
                background-color: white;   /* keep inputs white */
                border: 1px solid #A0A0A0;
                padding: 6px;
                border-radius: 4px;
            }
        """)
        
        self.setLayout(main_layout)

    def submit_case(self):
        # Placeholder for submission logic
        print("Case submitted!")
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
        content_container.setStyleSheet("background-color: white;") 
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
