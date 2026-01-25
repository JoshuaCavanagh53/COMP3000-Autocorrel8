from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt 

from sharedWidgets import ButtonLayout
from correlationSelection import CorrelationSelectionTable
from themes import DARK_THEME, LIGHT_THEME
import sys
from correlationVizuals import CorrelationVizuals
from correlationEngine import CorrelationEngine
import os
import json

# Dark mode by default
CURRENT_THEME = 'dark'
THEME = DARK_THEME if CURRENT_THEME == 'dark' else LIGHT_THEME

# Top navigation bar
class TopNavBar(QFrame):
    def __init__(self):
        super().__init__()
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

        # Cases button
        self.case_button = QLabel("Cases")
        self.case_button.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            border: none;
            padding: 5px 10px;
        """)
        self.case_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.case_button)
    
        # Tool information button
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


# Correlation Dashboard Main Window
class CorrelationDashboard(QMainWindow):
    def __init__(self, path):
        super().__init__()
        
        # Store the current case path
        self.path = path
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

        # Top navigation bar
        nav_bar = TopNavBar()
        main_layout.addWidget(nav_bar)
        nav_bar.setFixedHeight(55)

        # Main content container
        content_container = QWidget()
        content_container.setStyleSheet(f"background-color: {THEME['background']};") 
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 15, 20, 20)  
        content_layout.setSpacing(15)  
        
        # Navigation Buttons at the top
        button_layout = ButtonLayout("Overview", "Correlation", "Add Source")
        content_layout.addWidget(button_layout, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Import Correlation Engine
        self.correlation_engine = CorrelationEngine()

        # Create horizontal layout for table and visualization
        self.selection_boxes_layout = QHBoxLayout()
        self.selection_boxes_layout.setSpacing(15)

        # Data source overview table 
        self.correlation_selection_table = CorrelationSelectionTable(self.path)
        self.selection_boxes_layout.addWidget(self.correlation_selection_table, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        # Connect button AFTER creating correlation_view
        self.correlation_selection_table.correlation_button.clicked.connect(self.attempt_correlation)
        
        # Correlation View 
        self.correlation_view = CorrelationVizuals()
        self.selection_boxes_layout.addWidget(self.correlation_view, alignment=Qt.AlignTop | Qt.AlignRight)

        # Hide correlation view initially
        self.correlation_view.hide()

        # Add the horizontal layout to content
        content_layout.addLayout(self.selection_boxes_layout)

        # Add content container to main layout
        main_layout.addWidget(content_container)

        # Build from the top down
        content_layout.addStretch()

    # Attempt correlation
    def attempt_correlation(self):
        # Update the selection states
        self.correlation_selection_table.update_selection_states()
        
        # Get selected fields for debugging/processing
        selected_fields = self.correlation_selection_table.get_selected_fields_by_file()
        print("Selected fields by file:", selected_fields)
        
        packets_by_file = self.get_packets_for_selected_files(selected_fields.keys())

        timeline_data = self.correlation_engine.prepare_timeline_data(
            packets_by_file,
            selected_fields
        )

        # Update Visualization
        self.correlation_view.timeline_widget.load_timeline_data(timeline_data)

        # Show correlation view
        self.correlation_view.show()

    def get_packets_for_selected_files(self, filenames):

            # Get packet data from database or cache for selected files

            packets_by_file = {}

            for filename in filenames:

                # Try to load from cache first
                cache_path = os.path.join("packetFiles", f"{filename}_packets.json")

                if os.path.exists(cache_path):
                    with open(cache_path, "r") as f:
                        packets_by_file[filename] = json.load(f)
                else:
                    # Get from database
                    pass
            
            return packets_by_file
            



# Start the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CorrelationDashboard(path="C:\\Users\\jjc19\\OneDrive\\Documents\\Cases\\Case_1")
    window.show()
    sys.exit(app.exec())
        
