from ctypes import alignment
from PyQt5.QtWidgets import ( QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
   QScrollArea,  QComboBox, QStackedWidget, QLabel, QSlider, QButtonGroup, QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from datetime import datetime, timedelta

from distributionChart import *

from themes import THEME

# Correlation section
class CorrelationVizuals(QFrame):

    def __init__(self):
        super().__init__()
        
        # Remove fixed dimensions for flexible sizing
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5) 

        # Title
        title = QLabel("Correlation View")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)

        # Frame styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Add button Layout
        button_layout = VizualButtonLayout()
        button_layout.setStyleSheet("""
            QFrame {
                border: none;
                background-color: transparent;
            }
        """)
 
        layout.addWidget(title, alignment=Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(button_layout, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Create stacked widget to switch between different views
        self.stacked_widget = QStackedWidget()

        # Correlation table shows all found correlations in table format
        self.correlation_table_widget = CorrelationTableWidget()
        
        # Distribution chart mode shows distribution chart
        self.distribution_chart_widget = DistributionChartWidget()
        
        # Cross-PCAP mode shows cross-PCAP view
        self.cross_pcap_widget = QLabel("Cross-PCAP Communication View - Coming Soon")
        self.cross_pcap_widget.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")

        # Add widgets to stack 
        self.stacked_widget.addWidget(self.correlation_table_widget)
        self.stacked_widget.addWidget(self.distribution_chart_widget)
        self.stacked_widget.addWidget(self.cross_pcap_widget)

        layout.addWidget(self.stacked_widget)

        # Store reference to timeline widget
        self.timeline_widget = None
        
        # Store timeline data
        self.timeline_data = None

        # Connect buttons to switch views
        button_layout.correlation_table_button.clicked.connect(self.show_correlation_table_mode)
        button_layout.distribution_button.clicked.connect(self.show_distribution_mode)
        button_layout.cross_pcap_button.clicked.connect(self.show_cross_pcap_mode)

        # Push everything to top
        layout.addStretch()

        self.setLayout(layout)

    def set_timeline_widget(self, timeline_widget):
        # Store reference to timeline widget for clearing/showing
        self.timeline_widget = timeline_widget
        
        # Also pass reference to correlation table widget
        self.correlation_table_widget.set_timeline_widget(timeline_widget)
    
    def show_correlation_table_mode(self):
        # Correlation table mode show correlation table in top right, timeline visible at bottom
        self.stacked_widget.setCurrentIndex(0)
        
        # Reload timeline data if available
        if self.timeline_widget and self.timeline_data:
            self.timeline_widget.load_timeline_data(self.timeline_data)
    
    def show_distribution_mode(self):
        # Distribution mode show chart in top right, timeline blanked out at bottom
        self.stacked_widget.setCurrentIndex(1)
        
    
    def show_cross_pcap_mode(self):
        # Cross-PCAP mode show cross-PCAP view in top right, timeline blanked at bottom
        self.stacked_widget.setCurrentIndex(2)
        
        # Clear timeline (make it blank)
        if self.timeline_widget:
            self.timeline_widget.clear_timeline()

    def load_timeline_data(self, timeline_data):
        # Forward timeline data to all sub-widgets
        
        # Store timeline data for later use
        self.timeline_data = timeline_data
        
        # Load data into correlation table
        self.correlation_table_widget.load_data(timeline_data)
        
        # Load data into distribution chart
        self.distribution_chart_widget.load_data(timeline_data)
        
        # Show correlation table mode by default
        self.show_correlation_table_mode()


# Correlation table widget displays all found correlations in table format
class CorrelationTableWidget(QFrame):
    
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Table title
        title = QLabel("Correlations Found")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # Create table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Type", "Value", "Sources"])
        
        # Enable single row selection
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Table styling
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['surface']};
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
        
        # Set column widths
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)  # Timestamp
        self.table.setColumnWidth(1, 100)  # Type
        self.table.setColumnWidth(2, 200)  # Value
        
        # Hide vertical header
        self.table.verticalHeader().setVisible(False)
        
        # Connect row selection to timeline highlighting
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        
        layout.addWidget(self.table)
        
        # Store timeline widget reference
        self.timeline_widget = None
        
        # Store events data for selection
        self.events_list = []
        
        self.setLayout(layout)
    
    def load_data(self, timeline_data):
        # Load correlation data into table
        self.table.setRowCount(0)  # Clear existing rows
        
        if not timeline_data:
            return
        
        # Group events by (type, value) to collect all sources
        grouped_events = {}
        
        for filename, events in timeline_data.items():
            for event in events:
                key = (event.event_type, event.value)
                
                if key not in grouped_events:
                    grouped_events[key] = {
                        'timestamp': event.timestamp,
                        'type': event.event_type,
                        'value': event.value,
                        'sources': set()
                    }
                else:
                    # Keep the earliest timestamp
                    if event.timestamp < grouped_events[key]['timestamp']:
                        grouped_events[key]['timestamp'] = event.timestamp
                
                # Add source to the set (automatically handles duplicates)
                grouped_events[key]['sources'].add(event.pcap_name)
        
        
        # Filter to only show correlations found in multiple PCAPs
        events_list = [event for event in grouped_events.values() if len(event['sources']) > 1]
        
        # Sort by timestamp
        events_list.sort(key=lambda x: x['timestamp'])
        
        # Store for selection handling
        self.events_list = events_list
        
        # Populate table
        self.table.setRowCount(len(events_list))
        for row, event in enumerate(events_list):
            # Timestamp
            timestamp_str = event['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            self.table.setItem(row, 0, QTableWidgetItem(timestamp_str))
            
            # Type
            self.table.setItem(row, 1, QTableWidgetItem(event['type']))
            
            # Value
            self.table.setItem(row, 2, QTableWidgetItem(str(event['value'])))
            
            # Sources - combine all sources with comma separation
            sources_str = ', '.join(sorted(event['sources']))
            self.table.setItem(row, 3, QTableWidgetItem(sources_str))
    
    def set_timeline_widget(self, timeline_widget):
        
        # Store reference to timeline widget for event highlighting
        self.timeline_widget = timeline_widget
    
    def on_row_selected(self):
        
        # Handle row selection and highlight corresponding event on timeline
   
        selected_rows = self.table.selectionModel().selectedRows()
      
        # Get the first selected row
        row = selected_rows[0].row()
        print(f"Selected row index: {row}")
        
        if row < len(self.events_list):
            event = self.events_list[row]
            print(f"Event to highlight: {event['type']} - {event['value']} at {event['timestamp']}")
            
            # Check if timeline widget has highlight_event method
            if hasattr(self.timeline_widget, 'highlight_event'):
                print("Calling timeline_widget.highlight_event()")
                # Highlight the event on the timeline
                # Pass timestamp, type, and value to identify the event
                self.timeline_widget.highlight_event(
                    event['timestamp'],
                    event['type'],
                    event['value']
                )
            else:
                print("ERROR: timeline_widget does not have 'highlight_event' method!")
        else:
            print(f"Row {row} is out of range (events_list has {len(self.events_list)} items)")
        


class VizualButtonLayout(QFrame):
    
    def __init__(self):
        super().__init__()
        
        # Compact height for tight layout
        self.setFixedHeight(60)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)
 
        self.setStyleSheet("""
            QFrame {
                border: none;
                background-color: transparent;
            }
        """)
        
        button_style = f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                padding: 8px 8px;
                font-size: 10px;
                font-weight: 500;
            }}
            QPushButton:checked {{
                border: 2px solid {THEME['accent']};
                background-color: {THEME['button_checked']};
                color: {THEME['accent']};
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
        """

        # Set button group
        group = QButtonGroup(self)
        group.setExclusive(True)

        # Add buttons
        self.correlation_table_button = QPushButton("Correlation Table")
        self.distribution_button = QPushButton("Distribution")
        self.cross_pcap_button = QPushButton("Cross PCAP")
    
        # Configure buttons
        for btn in (self.correlation_table_button, self.distribution_button, self.cross_pcap_button):
            btn.setCheckable(True) 
            btn.setFixedSize(115, 35)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            group.addButton(btn)

        # Set Default button selection
        self.correlation_table_button.setChecked(True)

        self.setLayout(layout)