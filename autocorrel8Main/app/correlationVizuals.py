from PyQt5.QtWidgets import ( QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
   QScrollArea,  QComboBox, QStackedWidget, QLabel
)
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from datetime import datetime, timedelta

from themes import THEME



# Correlation section
class CorrelationVizuals(QFrame):

    def __init__(self):
        super().__init__()
        self.setFixedHeight(800)
        self.setFixedWidth(1450)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
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

        # Create stacked widget
        self.stacked_widget =  QStackedWidget()

        # Create different view widgets
        self.timeline_widget = CrossPCAPTimelineWidget()
        self.host_interaction_widget = QLabel("Host Interaction View - Coming Soon")
        self.host_interaction_widget.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")
        self.cross_pcap_widget = QLabel("Cross-PCAP Communication View - Coming Soon")
        self.cross_pcap_widget.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")
        
        # Add widgets to stack 
        self.stacked_widget.addWidget(self.timeline_widget)
        self.stacked_widget.addWidget(self.host_interaction_widget)
        self.stacked_widget.addWidget(self.cross_pcap_widget)

        layout.addWidget(self.stacked_widget)

        # Connect buttons to switch views
        button_layout.timeline_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        button_layout.host_interaction_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        button_layout.cross_pcap_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))


        # Push everything to top
        layout.addStretch()

        self.setLayout(layout)

# Represents one event in a timeline
class TimelineEvent:
    def __init__(self, timestamp, event_type, value, pcap_name):
        self.timestamp = timestamp
        self.event_type = event_type
        self.value = value
        self.pcap_name = pcap_name
        self.x_pos = 0

# Timeline for a single PCAP file
class PCAPTimeline(QWidget):
    def __init__(self, pcap_name, events, start_time, end_time, height=80):
        super().__init__()
        self.pcap_name = pcap_name
        self.events = events
        self.start_time = start_time
        self.end_time = end_time
        self.timeline_height = height
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)

        # Calculate event position
        self._calculate_event_positions()

    # Calculate the x position for each event based on its timestamp
    def _calculate_event_positions(self):
        if not self.events:
            return
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        if total_duration == 0:
            return
        
        for event in self.events:
            elapsed = (event.timestamp - self.start_time).total_seconds()

            available_width = self.width() - 120
            event.x_pos = 100 + int((elapsed / total_duration) * available_width)

    # Add events to the timeline
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        # Draw PCAP name
        painter.setPen(QColor(THEME['text_primary']))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRect(10, 10, 85, 20), Qt.AlignLeft | Qt.AlignVCenter, self.pcap_name)
        
        # Draw timeline bar
        timeline_y = self.timeline_height // 2
        painter.setPen(QPen(QColor(THEME['border']), 2))
        painter.drawLine(100, timeline_y, self.width() - 20, timeline_y)
        
        # Recalculate positions in case of resize
        self._calculate_event_positions()
        
        # Draw events
        for event in self.events:
            color = self._get_event_color(event.event_type)
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(color), 1))
            
            # Draw event marker (circle)
            painter.drawEllipse(event.x_pos - 4, timeline_y - 4, 8, 8)
    
    def _get_event_color(self, event_type):
     
        colors = {
            'domain': THEME['event_domain'],
            'ip': THEME['event_ip'],
            'port': THEME['event_port'],
        }
        return colors.get(event_type, THEME['accent'])
    
    def resizeEvent(self, event):
   
        self._calculate_event_positions()
        super().resizeEvent(event)


class CrossPCAPTimelineWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.pcap_timelines = []
        self.correlations = []  # List of correlated event pairs
        self.filter_type = 'domain'  # Current filter type
        self.time_threshold = 5.0  # Seconds within which events are considered correlated
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)
        
        self._init_ui()
        self._load_sample_data()
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header with title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Cross-PCAP Timeline Correlation")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter type selector
        filter_label = QLabel("Filter by:")
        filter_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(['domain', 'ip', 'port', 'protocol'])
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 5px 10px;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                selection-background-color: {THEME['accent']};
            }}
        """)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.filter_combo)
        
        # Time threshold input
        threshold_label = QLabel("Time threshold (s):")
        threshold_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(threshold_label)
        
        self.threshold_combo = QComboBox()
        self.threshold_combo.addItems(['1', '5', '10', '30', '60'])
        self.threshold_combo.setCurrentText('5')
        self.threshold_combo.setStyleSheet(self.filter_combo.styleSheet())
        self.threshold_combo.currentTextChanged.connect(self._on_threshold_changed)
        header_layout.addWidget(self.threshold_combo)
        
        # Refresh button
        refresh_btn = QPushButton("Find Correlations")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #3a8eef;
            }}
        """)
        refresh_btn.clicked.connect(self._find_correlations)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Scroll area for timelines
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {THEME['timeline_bg']};
            }}
        """)
        
        # Container for timelines
        self.timeline_container = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setSpacing(2)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll.setWidget(self.timeline_container)
        layout.addWidget(scroll)
        
        # Correlation info panel
        self.info_label = QLabel("No correlations found")
        self.info_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
            padding: 10px;
            background-color: {THEME['timeline_bg']};
            border-radius: 4px;
        """)
        layout.addWidget(self.info_label)
    
    # Sample data for testing
    def _load_sample_data(self):
        """Load sample PCAP data for demonstration"""
        # Create sample timeline data
        base_time = datetime.now() - timedelta(hours=1)
        
        # PCAP 1
        events1 = [
            TimelineEvent(base_time + timedelta(seconds=10), 'domain', 'malicious.com', 'capture1.pcap'),
            TimelineEvent(base_time + timedelta(seconds=30), 'ip', '192.168.1.100', 'capture1.pcap'),
            TimelineEvent(base_time + timedelta(seconds=45), 'domain', 'evil.net', 'capture1.pcap'),
            TimelineEvent(base_time + timedelta(seconds=120), 'domain', 'suspicious.org', 'capture1.pcap'),
        ]
        
        # PCAP 2
        events2 = [
            TimelineEvent(base_time + timedelta(seconds=12), 'domain', 'malicious.com', 'capture2.pcap'),
            TimelineEvent(base_time + timedelta(seconds=50), 'ip', '192.168.1.200', 'capture2.pcap'),
            TimelineEvent(base_time + timedelta(seconds=125), 'domain', 'suspicious.org', 'capture2.pcap'),
        ]
        
        # PCAP 3
        events3 = [
            TimelineEvent(base_time + timedelta(seconds=8), 'domain', 'malicious.com', 'capture3.pcap'),
            TimelineEvent(base_time + timedelta(seconds=60), 'port', '443', 'capture3.pcap'),
            TimelineEvent(base_time + timedelta(seconds=130), 'domain', 'suspicious.org', 'capture3.pcap'),
        ]
        
        # Find global time range
        all_events = events1 + events2 + events3
        start_time = min(e.timestamp for e in all_events)
        end_time = max(e.timestamp for e in all_events)
        
        # Create timeline widgets
        self.pcap_timelines = [
            PCAPTimeline('capture1.pcap', events1, start_time, end_time),
            PCAPTimeline('capture2.pcap', events2, start_time, end_time),
            PCAPTimeline('capture3.pcap', events3, start_time, end_time),
        ]
        
        # Add to layout
        for timeline in self.pcap_timelines:
            self.timeline_layout.addWidget(timeline)
        
        self.timeline_layout.addStretch()
        
        # Find initial correlations
        self._find_correlations()
    
    def _on_filter_changed(self, filter_type):
        """Handle filter type change"""
        self.filter_type = filter_type
        self._find_correlations()
    
    def _on_threshold_changed(self, threshold):
        """Handle time threshold change"""
        self.time_threshold = float(threshold)
        self._find_correlations()
    
    def _find_correlations(self):
        """Find correlated events across PCAPs"""
        self.correlations = []
        
        # Collect all events of the selected type
        all_events = []
        for timeline in self.pcap_timelines:
            for event in timeline.events:
                if event.event_type == self.filter_type:
                    all_events.append(event)
        
        # Find events with matching values within time threshold
        for i, event1 in enumerate(all_events):
            for event2 in all_events[i+1:]:
                # Check if same value but different PCAPs
                if (event1.value == event2.value and 
                    event1.pcap_name != event2.pcap_name):
                    
                    # Check time difference
                    time_diff = abs((event1.timestamp - event2.timestamp).total_seconds())
                    if time_diff <= self.time_threshold:
                        self.correlations.append((event1, event2, time_diff))
        
        # Update info label
        if self.correlations:
            info_text = f"Found {len(self.correlations)} correlation(s):\n"
            for event1, event2, time_diff in self.correlations[:5]:  # Show first 5
                info_text += f"• {event1.value} in {event1.pcap_name} and {event2.pcap_name} (Δ{time_diff:.1f}s)\n"
            if len(self.correlations) > 5:
                info_text += f"... and {len(self.correlations) - 5} more"
        else:
            info_text = f"No correlations found for {self.filter_type} within {self.time_threshold}s"
        
        self.info_label.setText(info_text)
        
        # Trigger repaint to show correlation lines
        self.update()
    
    def paintEvent(self, event):
        """Draw correlation lines between events"""
        super().paintEvent(event)
        
        if not self.correlations:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw correlation lines
        pen = QPen(QColor(THEME['correlation_line']), 2, Qt.DashLine)
        painter.setPen(pen)
        
        for event1, event2, time_diff in self.correlations:
            # Find the timeline widgets for these events
            timeline1 = next((t for t in self.pcap_timelines if t.pcap_name == event1.pcap_name), None)
            timeline2 = next((t for t in self.pcap_timelines if t.pcap_name == event2.pcap_name), None)
            
            if timeline1 and timeline2:
                # Convert to global coordinates
                pt1 = timeline1.mapTo(self, QPoint(event1.x_pos, timeline1.height() // 2))
                pt2 = timeline2.mapTo(self, QPoint(event2.x_pos, timeline2.height() // 2))
                
                painter.drawLine(pt1, pt2)

    # Load real timeline data
    def load_timeline_data(self, timeline_data):

        # Clear existing timelines
        for i in reversed(range(self.timeline_layout.count())):
            widget = self.timeline_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.pcap_timelines = []

        # find global time range across all files
        all_events = []
        for events in timeline_data.values():
            all_events.extend(events)

        if not all_events:
            # Show no data message
            no_data_label = QLabel("No events found for selected fields")
            no_data_label.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px")
            self.timeline_layout.addWidget(no_data_label)
            return
        
        start_time = min(e.timestamp for e in all_events)
        end_time = max(e.timestamp for e in all_events)

        # Create timeline for each file
        for pcap_name, events in sorted(timeline_data.items()):
            if events: # Only create timeline if there are events
                timeline = PCAPTimeline(pcap_name, events, start_time, end_time)
                self.pcap_timelines.append(timeline)
                self.timeline_layout.addWidget(timeline)

        self.timeline_layout.addStretch()

        # Find correlations
        self._find_correlations()

class VizualButtonLayout(QFrame):
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(75)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(15)
 
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
                border-radius: 4px;
                padding: 10px 10px;
                font-size: 13px;
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

        # Add buttons
        self.timeline_button = QPushButton("Timeline")
        self.timeline_button.setStyleSheet(button_style)
        self.timeline_button.setFixedHeight(40)
        self.timeline_button.setFixedWidth(120)
        self.timeline_button.setCheckable(True)
        
        # Case overview checked by default
        self.timeline_button.setChecked(True)

        self.timeline_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.timeline_button)

        self.host_interaction_button = QPushButton("Host interaction")
        self.host_interaction_button.setStyleSheet(button_style)
        self.host_interaction_button.setFixedHeight(40)
        self.host_interaction_button.setFixedWidth(120)
        self.host_interaction_button.setCheckable(True)
        self.host_interaction_button.setCursor(Qt.PointingHandCursor)
        
        
        layout.addWidget(self.host_interaction_button)

        self.cross_pcap_button = QPushButton("Cross PCAP Interaction")
        self.cross_pcap_button.setStyleSheet(button_style)
        self.cross_pcap_button.setFixedHeight(40)
        self.cross_pcap_button.setFixedWidth(120)
        self.cross_pcap_button.setCheckable(True)
        self.cross_pcap_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.cross_pcap_button)

        self.setLayout(layout)
