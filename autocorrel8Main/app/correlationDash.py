from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt 

from sharedWidgets import ButtonLayout, TopNavBar
from correlationSelection import CorrelationSelectionTable
from themes import DARK_THEME, LIGHT_THEME, THEME
import sys
from correlationVizuals import CorrelationVizuals
from correlationEngine import CorrelationEngine
from timelineCorrelation import CrossPCAPTimelineWidget
import os
import json

# Dark mode by default
CURRENT_THEME = 'dark'

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
        nav_bar.setFixedHeight(50)
        main_layout.addWidget(nav_bar)

        # Main content container
        content_container = QWidget()
        content_container.setStyleSheet(f"background-color: {THEME['background']};") 
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)    
        content_layout.setSpacing(0)
        
        # Top section - horizontal split for left panel and right panel
        top_section_layout = QHBoxLayout()
        top_section_layout.setSpacing(0)
        top_section_layout.setContentsMargins(0, 0, 0, 0)

        # Left panel - contains buttons and selection table
        left_panel = QWidget()
        left_panel.setMaximumHeight(450)  # Limit height so timeline has more room
        left_panel_layout = QVBoxLayout(left_panel)
        left_panel_layout.setContentsMargins(0, 0, 0, 0)
        left_panel_layout.setSpacing(0)

        # Navigation Buttons at the top
        button_layout = ButtonLayout("Overview", "Correlation", "Add Source")
        left_panel_layout.addWidget(button_layout)

        # Set button state
        button_layout.correlation_button.setChecked(True)
        
        # Import Correlation Engine
        self.correlation_engine = CorrelationEngine()

        # Data source overview table 
        self.correlation_selection_table = CorrelationSelectionTable(self.path)
        left_panel_layout.addWidget(self.correlation_selection_table)
        
        # Add left panel to top section
        top_section_layout.addWidget(left_panel)
        
        # Right panel - Correlation View (switches between correlation table and distribution chart)
        self.correlation_view = CorrelationVizuals()
        self.correlation_view.setMaximumHeight(450)  # Match left panel height
        top_section_layout.addWidget(self.correlation_view, 1)

        # Add top section to content - no stretch factor so it stays compact
        content_layout.addLayout(top_section_layout)

        # Bottom section - Timeline (ALWAYS visible, just blanked out in distribution mode)
        self.timeline_widget = CrossPCAPTimelineWidget()
        self.timeline_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border-top: 1px solid {THEME['border']};
            }}
        """)
        self.timeline_widget.setMinimumHeight(400)  # More room for timeline
        
        # Add timeline to content - this will expand to fill remaining space
        content_layout.addWidget(self.timeline_widget, 1)
        
        # Connect button AFTER creating correlation_view
        self.correlation_selection_table.correlation_button.clicked.connect(self.attempt_correlation)
        
        # Pass timeline widget reference to correlation view for clearing/showing
        self.correlation_view.set_timeline_widget(self.timeline_widget)

        # Add content container to main layout
        main_layout.addWidget(content_container)

    # Attempt correlation
    def attempt_correlation(self):
        # Update the selection states
        self.correlation_selection_table.update_selection_states()
        
        # Get selected fields for debugging/processing
        selected_fields = self.correlation_selection_table.get_selected_fields_by_file()
        print("Selected fields by file:", selected_fields)
        
        # Get packet data from cache or database
        packets_by_file = self.get_packets_for_selected_files(selected_fields.keys())

        # Prepare timeline data using correlation engine
        timeline_data = self.correlation_engine.prepare_timeline_data(
            packets_by_file,
            selected_fields
        )

        # Update Visualization - both correlation view and timeline
        self.correlation_view.load_timeline_data(timeline_data)
        self.timeline_widget.load_timeline_data(timeline_data)

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