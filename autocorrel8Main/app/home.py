# Import necessary PyQt5 modules
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QGraphicsDropShadowEffect)
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
        cases_info = QLabel("Cases")
        cases_info.setStyleSheet("color: black; font-size: 14px; border: none;")
        layout.addWidget(cases_info)
    
        tool_info = QLabel("Tool Information")
        tool_info.setStyleSheet("color: black; font-size: 14px; border: none;")
        layout.addWidget(tool_info)


        layout.addStretch()

        self.setLayout(layout)

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


# Start the application 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoCorrel8Dashboard()
    window.show()
    sys.exit(app.exec())
