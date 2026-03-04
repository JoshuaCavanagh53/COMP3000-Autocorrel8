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
from browserLogParser import BrowserLogParser
from correlationEngine import GapDetector
from timelineCorrelation import *



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

        self.showMaximized()  # Start maximized

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
        
        # Right panel, Correlation View (switches between correlation table and distribution chart)
        self.correlation_view = CorrelationVizuals()
        self.correlation_view.setMaximumHeight(450)  # Match left panel height
        top_section_layout.addWidget(self.correlation_view, 1)


        # Cache packets 
        self._packet_cache = {}

        # Add top section to content, no stretch factor so it stays compact
        content_layout.addLayout(top_section_layout)

        # Bottom section, Timeline 
        self.timeline_widget = CrossPCAPTimelineWidget()
        self.timeline_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border-top: 1px solid {THEME['border']};
            }}
        """)
        self.timeline_widget.setMinimumHeight(400)
        content_layout.addWidget(self.timeline_widget, 1)  
    
        # Connect button after creating correlation_view
        self.correlation_selection_table.correlation_button.clicked.connect(self.attempt_correlation)
        
        # Pass timeline widget reference to correlation view for clearing/showing
        self.correlation_view.set_timeline_widget(self.timeline_widget)

        self.incognito_button = QPushButton("Detect Incognito Gaps")
        
        # Incognito gap widget
        self.incognito_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['button_checked']};
            }}
        """)
        self.incognito_button.clicked.connect(self.detect_incognito_gaps)  
        left_panel_layout.addWidget(self.incognito_button)

        # Add content container to main layout
        main_layout.addWidget(content_container)

    # Attempt correlation
    def attempt_correlation(self):
        
        # Clear stale caches when re-running
        self._cached_browser_events = None
        self._cached_gaps = None
        if hasattr(self, '_cached_browser_events'):
            del self._cached_browser_events
        if hasattr(self, '_cached_gaps'):
            del self._cached_gaps

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
        self._last_timeline_data = timeline_data # Cache for later use in gap detection
        self.correlation_view.load_timeline_data(timeline_data)
        self.timeline_widget.load_timeline_data(timeline_data)

    def get_packets_for_selected_files(self, filenames):
        
        packets_by_file = {}
        for filename in filenames:
            if filename in self._packet_cache:
                packets_by_file[filename] = self._packet_cache[filename]
                continue
            cache_path = os.path.join("packetFiles", f"{filename}_packets.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    data = json.load(f)
                self._packet_cache[filename] = data
                packets_by_file[filename] = data
        return packets_by_file
    
    def detect_incognito_gaps(self):

        # Use cached timeline if available, otherwise recompute
        pcap_timeline = getattr(self, '_last_timeline_data', None)
        
        if not pcap_timeline:
            selected_fields = self.correlation_selection_table.get_selected_fields_by_file()
            packets_by_file = self.get_packets_for_selected_files(selected_fields.keys())
            pcap_timeline = self.correlation_engine.prepare_timeline_data(
                packets_by_file,
                selected_fields
            )

        # Extract domain events from PCAPs
        pcap_domain_events = []
        for filename, events in pcap_timeline.items():
            domain_events = [e for e in events if e.event_type == 'domain']
            pcap_domain_events.extend(domain_events)

        # Use cached browser events if available
        if not hasattr(self, '_cached_browser_events'):
            self._cached_browser_events = self.get_browser_history_events()

        browser_events = self._cached_browser_events

        if not browser_events:
            print("No browser history found! Upload a History.db file to evidence folder.\n")
            return

        # Use cached gaps if timeline and browser events haven't changed
        if not hasattr(self, '_cached_gaps'):
            detector = GapDetector(time_window_seconds=60)
            self._cached_gaps = detector.find_gaps_grouped(pcap_domain_events, browser_events)

        grouped_gaps = self._cached_gaps

        if not grouped_gaps:
            print("No gaps detected - all network traffic matches browser history\n")
            return

        # Load gaps into correlation view
        self.correlation_view.incognito_gap_widget.load_gaps(grouped_gaps)

        # Load PCAP events into timeline
        self.timeline_widget.load_timeline_data(pcap_timeline)

        # Load gaps into timeline as dedicated lane
        self.timeline_widget.load_incognito_gaps(
            grouped_gaps,
            self.correlation_view.incognito_gap_widget
        )
        

    def get_browser_history_events(self):
        
        # Load and parse browser history from evidence folder
        
        evidence_dir = os.path.join(self.path, "evidence")
        browser_events = []
        
        # Look for browser history files
        for filename in os.listdir(evidence_dir):
            if filename.endswith(('.sqlite', '.db')) and 'history' in filename.lower():
                
                history_path = os.path.join(evidence_dir, filename)
                print(f"Found browser history: {filename}")
                
                # Parse it
                parser = BrowserLogParser()
                events = parser.parse_browser_history('chrome', history_path)
                browser_events.extend(events)
                
                print(f"✓ Parsed {len(events)} entries from {filename}")
        
        return browser_events

# Start the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CorrelationDashboard(path="C:\\Users\\jjc19\\OneDrive\\Documents\\Cases\\Case_13")
    window.show()
    sys.exit(app.exec())