from ctypes import alignment
from PyQt5.QtWidgets import ( QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
   QScrollArea,  QComboBox,  QLabel, QSlider, QTableWidget, QHeaderView, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from datetime import  timedelta

from themes import THEME

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
    def __init__(self, pcap_name, events, start_time, end_time, height=120, pixels_per_second=50):
        super().__init__()
        self.pcap_name = pcap_name
        self.events = events
        self.start_time = start_time
        self.end_time = end_time
        self.timeline_height = height
        self.highlighted_events = []
        self.pixels_per_second = pixels_per_second
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)

        # Calculate required width based on time span
        total_duration = (self.end_time - self.start_time).total_seconds()
        required_width = int(total_duration * self.pixels_per_second) + 200
        self.setMinimumWidth(required_width)

        # Calculate event position
        self._calculate_event_positions()

    def _calculate_event_positions(self):
        if not self.events:
            return
        
        total_duration = (self.end_time - self.start_time).total_seconds()
        if total_duration == 0:
            return
        
        for event in self.events:
            elapsed = event.normalized_ts
            event.x_pos = 100 + int(elapsed * self.pixels_per_second)

    def set_highlighted_events(self, events):
        
        # Set which events should be highlighted
        self.highlighted_events = events if events else []
        self.update()  # Trigger repaint

    def clear_highlights(self):
        
        # Remove all highlights
        self.highlighted_events = []
        self.update()  # Trigger repaint

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
        
        # Draw events
        for event in self.events:
            # Check if this event should be highlighted
            if event in self.highlighted_events:
                # Draw highlighted event
                self._draw_highlighted_event(painter, event, timeline_y)
            else:
                # Draw normal event
                color = self._get_event_color(event.event_type)
                painter.setBrush(QBrush(QColor(color)))
                painter.setPen(QPen(QColor(color), 1))
                
                # Draw event marker (circle)
                painter.drawEllipse(event.x_pos - 4, timeline_y - 4, 8, 8)
    
    def _draw_highlighted_event(self, painter, event, timeline_y):
        
        # Draw a highlighted event marker
        highlight_color = QColor("#ffdd00")  
        painter.setBrush(QBrush(highlight_color))
        painter.setPen(QPen(highlight_color.darker(120), 2))
        painter.drawEllipse(event.x_pos - 7, timeline_y - 7, 14, 14)  
        
      

    def _get_event_color(self, event_type):
        colors = {
            'domain': THEME['event_domain'],
            'ip': THEME['event_ip'],
            'port': THEME['event_port'],
        }
        return colors.get(event_type, THEME['accent'])


# Timestamp axis widget
class TimestampAxis(QWidget):
    def __init__(self, start_time, end_time, height=30, pixels_per_second=50):
        super().__init__()
        self.start_time = start_time
        self.end_time = end_time
        self.pixels_per_second = pixels_per_second
        self.setMinimumHeight(height)
        self.setMaximumHeight(height)
        
        # Calculate required width
        total_duration = (self.end_time - self.start_time).total_seconds()
        required_width = int(total_duration * self.pixels_per_second) + 200
        self.setMinimumWidth(required_width)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        # Set font
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor(THEME['text_secondary']))
        
        # Calculate time markers
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Determine appropriate interval based on duration
        if total_duration <= 60:
            interval = 5
            time_format = "%H:%M:%S"
        elif total_duration <= 600:
            interval = 30
            time_format = "%H:%M:%S"
        elif total_duration <= 3600:
            interval = 60
            time_format = "%H:%M:%S"
        else:
            interval = 300
            time_format = "%H:%M:%S"
        
        # Draw time markers
        current_time = self.start_time
        while current_time <= self.end_time:
            elapsed = (current_time - self.start_time).total_seconds()
            x_pos = 100 + int(elapsed * self.pixels_per_second)
            
            # Draw tick mark
            painter.setPen(QPen(QColor(THEME['border']), 1))
            painter.drawLine(x_pos, 5, x_pos, 15)
            
            # Draw time label
            painter.setPen(QColor(THEME['text_secondary']))
            time_str = current_time.strftime(time_format)
            painter.drawText(QRect(x_pos - 40, 15, 80, 15), 
                           Qt.AlignCenter, time_str)
            
            current_time += timedelta(seconds=interval)


# Overlay widget for drawing correlation lines on top
class CorrelationOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.correlations = []
        self.pcap_timelines = []
        self.scroll_area = None
        self._initialized = False
        
        # Make the widget transparent to mouse events
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        # Make background transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
    
    def set_data(self, correlations, pcap_timelines, scroll_area):
        
        # Update the correlation data and trigger repaint
        self.correlations = correlations if correlations else []
        self.pcap_timelines = pcap_timelines if pcap_timelines else []
        self.scroll_area = scroll_area
        self._initialized = True
        self.update()
    
    def paintEvent(self, event):

        # Draw correlation lines
        # Safety checks
        if not self._initialized:
            return
        if not self.correlations:
            return
        if not self.scroll_area:
            return
        if not self.pcap_timelines:
            return
        
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw correlation lines
            pen = QPen(QColor(THEME.get('correlation_line', '#FF6B6B')), 2, Qt.DashLine)
            painter.setPen(pen)
            
            # Get scroll offset safely
            h_scrollbar = self.scroll_area.horizontalScrollBar()
            scroll_offset = h_scrollbar.value() if h_scrollbar else 0
            
            for event1, event2, time_diff in self.correlations:
                try:
                    # Find the timeline widgets for these events
                    timeline1 = next((t for t in self.pcap_timelines if t.pcap_name == event1.pcap_name), None)
                    timeline2 = next((t for t in self.pcap_timelines if t.pcap_name == event2.pcap_name), None)
                    
                    if not timeline1 or not timeline2:
                        continue
                    
                    if not timeline1.isVisible() or not timeline2.isVisible():
                        continue
                    
                    # Get positions in timeline coordinates
                    x1 = event1.x_pos - scroll_offset
                    y1_widget = timeline1.mapTo(self.parent(), QPoint(0, timeline1.height() // 2))
                    y1 = y1_widget.y()

                    x2 = event2.x_pos - scroll_offset
                    y2_widget = timeline2.mapTo(self.parent(), QPoint(0, timeline2.height() // 2))
                    y2 = y2_widget.y()

                    
                    # Only draw if at least one point is visible
          
                    painter.drawLine(x1, y1, x2, y2)
                        
                except Exception as e:
                    # Skip this correlation if there's an error
                    print(f"Error drawing correlation line: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error in paintEvent: {e}")


class CrossPCAPTimelineWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.pcap_timelines = []
        self.timestamp_axis = None
        self.correlations = []
        self.filter_type = 'domain'
        self.time_threshold = 5.0
        self.pixels_per_second = 50
        self.overlay = None
        self.selected_events = []
        
        # Secure domains
        self.safe_domains = [
            # Operating system & update infrastructure
            "windowsupdate.com",
            "microsoft.com",
            "msftncsi.com",
            "apple.com",
            "icloud.com",
            "ubuntu.com",
            "canonical.com",

            # DNS providers
            "google.com",
            "googleapis.com",
            "gstatic.com",
            "cloudflare.com",
            "cloudflare-dns.com",
            "quad9.net",
            "opendns.com",

            # CDNs
            "akamai.net",
            "akamaihd.net",
            "fastly.net",
            "cloudfront.net",
            "edgesuite.net",
            "cdn.jsdelivr.net",

            # Browsers & search engines
            "bing.com",
            "duckduckgo.com",
            "mozilla.org",
            "firefox.com",
            "chrome.com",

            # Cloud platforms
            "amazonaws.com",
            "azure.com",
            "azureedge.net",
            "googleusercontent.com",
            "dropbox.com",

            # Time sync
            "ntp.org",
            "pool.ntp.org",
            "time.windows.com",

            # Analytics / ads (high volume, usually benign)
            "doubleclick.net",
            "googletagmanager.com",
            "google-analytics.com",
            "facebook.com",
            "fbcdn.net",

            # Security vendors
            "symantec.com",
            "kaspersky.com",
            "crowdstrike.com",
            "avast.com",
            "bitdefender.com",
        ]

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)
        
        self._init_ui()
        
    
    def _init_ui(self):
        
        # Initialize the UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(25)
        
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
        
        # Zoom/density control
        zoom_label = QLabel("Timeline zoom:")
        zoom_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(200)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setMaximumWidth(150)
        self.zoom_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {THEME['border']};
                height: 4px;
                background: {THEME['button_bg']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {THEME['accent']};
                width: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
        """)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        header_layout.addWidget(self.zoom_slider)
        
        self.zoom_value_label = QLabel("50px/s")
        self.zoom_value_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; min-width: 60px;")
        header_layout.addWidget(self.zoom_value_label)
        
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
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
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
        
        # Horizontal scroll area for timelines
        self.scroll = QScrollArea()
        self.scroll.setMinimumHeight(240)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {THEME['timeline_bg']};
            }}
            QScrollBar:horizontal {{
                height: 12px;
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:horizontal {{
                background: {THEME['border']};
                border-radius: 6px;
                min-width: 40px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {THEME['text_secondary']};
            }}
        """)
        
        # Container for timelines
        self.timeline_container = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_container)
        self.timeline_layout.setSpacing(2)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll.setWidget(self.timeline_container)
        
        layout.addWidget(self.scroll)
        
        # Correlation results section
        correlation_header = QHBoxLayout()
        
        correlation_title = QLabel("Correlations Found:")
        correlation_title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: bold;
        """)
        correlation_header.addWidget(correlation_title)
        
        self.correlation_count_label = QLabel("0 correlations")
        self.correlation_count_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
        """)
        correlation_header.addWidget(self.correlation_count_label)
        
        correlation_header.addStretch()
        
        layout.addLayout(correlation_header)
        
        # Scrollable correlation table
        self.correlation_table = QTableWidget()
        self.correlation_table.setColumnCount(4)
        self.correlation_table.setHorizontalHeaderLabels(['Value', 'PCAP 1', 'PCAP 2', 'Time Δ (s)'])
        self.correlation_table.setMaximumHeight(180)
        self.correlation_table.setMinimumHeight(120)
        self.correlation_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.correlation_table.setSelectionMode(QTableWidget.SingleSelection)
        self.correlation_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.correlation_table.setAlternatingRowColors(True)
        self.correlation_table.setSortingEnabled(True)
        self.correlation_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['timeline_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                gridline-color: {THEME['border']};
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
                color: white;
            }}
            QTableWidget::item:alternate {{ 
                background-color: #3a3a3a;  /* Lighter gray to contrast every other row */
            }}
            QTableWidget::item:selected {{
                background-color: {THEME['accent']};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: rgba(70, 130, 180, 0.2);
            }}
            QHeaderView::section {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_secondary']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {THEME['border']};
                font-weight: bold;
                font-size: 11px;
            }}
            QHeaderView::section:hover {{
                background-color: {THEME['border']};
            }}
            QScrollBar:vertical {{
                width: 12px;
                background: {THEME['timeline_bg']};
            }}
            QScrollBar::handle:vertical {{
                background: {THEME['border']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {THEME['text_secondary']};
            }}
        """)
        
        # Set column widths
        header = self.correlation_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Value column stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # PCAP 1
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # PCAP 2
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Time delta
        
        # Connect selection to highlighting
        self.correlation_table.itemSelectionChanged.connect(self._on_correlation_selected)
    
        layout.addWidget(self.correlation_table)
    
    def showEvent(self, event):
        
        # Create overlay when widget is shown
        super().showEvent(event)
        if not self.overlay:
            self._create_overlay()
    
    def _create_overlay(self):
        
        # Create the overlay widget
        try:
            if self.overlay:
                self.overlay.deleteLater()
            
            self.overlay = CorrelationOverlay(self.scroll.viewport())
            self.overlay.setGeometry(self.scroll.viewport().rect())
            self.overlay.show()
            self.overlay.raise_()
            
            # Connect scroll events
            if self.scroll.horizontalScrollBar():
                self.scroll.horizontalScrollBar().valueChanged.connect(self._update_overlay)
            if self.scroll.verticalScrollBar():
                self.scroll.verticalScrollBar().valueChanged.connect(self._update_overlay)
                
        except Exception as e:
            print(f"Error creating overlay: {e}")
    
    def resizeEvent(self, event):
        
        # Update overlay size when widget is resized
        super().resizeEvent(event)
        if self.overlay:
            try:
                self.overlay.setGeometry(self.scroll.viewport().rect())
                self._update_overlay()
            except Exception as e:
                print(f"Error in resizeEvent: {e}")
    
    def _update_overlay(self):
        
        # Update overlay position and trigger repaint
        if self.overlay:
            try:
                self.overlay.setGeometry(self.scroll.viewport().rect())
                self.overlay.set_data(self.correlations, self.pcap_timelines, self.scroll)
            except Exception as e:
                print(f"Error updating overlay: {e}")
    
    def _on_zoom_changed(self, value):
        
        # Handle zoom slider change
        self.pixels_per_second = value
        self.zoom_value_label.setText(f"{value}px/s")
        self._rebuild_timelines()
    
    def _rebuild_timelines(self):
        
        # Rebuild all timelines with new zoom level
        if not self.pcap_timelines:
            return
        
        try:
            # Get the data from existing timelines
            timeline_data = {}
            for timeline in self.pcap_timelines:
                timeline_data[timeline.pcap_name] = timeline.events
            

            # Find global time range
            all_events = []
            for events in timeline_data.values():
                all_events.extend(events)
            
            if not all_events:
                return
            
            for pcap_name, events in timeline_data.items():
                base = min(e.timestamp for e in events)
                for e in events:
                    e.normalized_ts = (e.timestamp - base).total_seconds()

            start_time = min(e.timestamp for e in all_events)
            end_time = max(e.timestamp for e in all_events)
            
            # Clear existing widgets
            for i in reversed(range(self.timeline_layout.count())):
                widget = self.timeline_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            
            self.pcap_timelines = []
            
            # Recreate timelines with new zoom
            for pcap_name, events in sorted(timeline_data.items()):
                if events:
                    timeline = PCAPTimeline(pcap_name, events, start_time, end_time, 
                                           pixels_per_second=self.pixels_per_second)
                    self.pcap_timelines.append(timeline)
                    self.timeline_layout.addWidget(timeline)
            

            # Add timestamp axis at the bottom
            self.timestamp_axis = TimestampAxis(start_time, end_time, 
                                               pixels_per_second=self.pixels_per_second)
            self.timeline_layout.addWidget(self.timestamp_axis)
            
            self.timeline_layout.addStretch()
            
            # Update overlay
            QTimer.singleShot(50, self._update_overlay)
            
        except Exception as e:
            print(f"Error rebuilding timelines: {e}")
    
    
    def _on_filter_changed(self, filter_type):
        
        # Handle filter type change
        self.filter_type = filter_type
        self._find_correlations()
    
    
    def _find_correlations(self):
        
        # Find correlated events across PCAPs
        try:
            self.correlations = []
            
            # Collect all events of the selected type
            all_events = []
            for timeline in self.pcap_timelines:
                for event in timeline.events:
                    if event.event_type == self.filter_type:
                        
                        # Only filter for important protocols
                        if self.filter_type == 'protocol':
                            # Only correlate application-layer protocols
                            important_protocols = {'HTTP', 'HTTPS', 'DNS', 'TLS', 'SSH', 'FTP', 'SMTP'}
                            if event.value not in important_protocols:
                                continue

                        all_events.append(event)
            
            # Find events with matching values 
            for i, event1 in enumerate(all_events):
                for event2 in all_events[i+1:]:
                    # Check if same value but different PCAPs
                    if (event1.value == event2.value and 
                        event1.pcap_name != event2.pcap_name):
                        
                        # Check time difference
                        time_diff = abs((event1.timestamp - event2.timestamp).total_seconds())
                        self.correlations.append((event1, event2, time_diff))
            
            # Sort correlations by time difference
            self.correlations.sort(key=lambda x: x[2])
            
            # Update count label
            count = len(self.correlations)
            self.correlation_count_label.setText(f"{count} correlation{'s' if count != 1 else ''}")
            
            # Clear and populate table
            self.correlation_table.setRowCount(0)
            self.correlation_table.setSortingEnabled(False)  # Disable while populating
            
            if self.correlations:
                self.correlation_table.setRowCount(len(self.correlations))
                
                for row, (event1, event2, time_diff) in enumerate(self.correlations):
                    # Value column
                    value_item = QTableWidgetItem(str(event1.value))
                    value_item.setToolTip(f"Full value: {event1.value}")
                    self.correlation_table.setItem(row, 0, value_item)
                    
                    # PCAP 1 column
                    pcap1_item = QTableWidgetItem(event1.pcap_name)
                    pcap1_item.setToolTip(f"File: {event1.pcap_name}")
                    self.correlation_table.setItem(row, 1, pcap1_item)
                    
                    # PCAP 2 column
                    pcap2_item = QTableWidgetItem(event2.pcap_name)
                    pcap2_item.setToolTip(f"File: {event2.pcap_name}")
                    self.correlation_table.setItem(row, 2, pcap2_item)
                    
                    # Time difference column
                    time_item = QTableWidgetItem(f"{time_diff:.2f}")
                    time_item.setData(Qt.UserRole, time_diff)  # Store numeric value for sorting
                    time_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    time_item.setToolTip(f"Time difference: {time_diff:.2f} seconds")
                    self.correlation_table.setItem(row, 3, time_item)
                
                # Re-enable sorting
                self.correlation_table.setSortingEnabled(True)
                
            else:
                # Show a "no results" message in the table
                self.correlation_table.setRowCount(1)
                no_results_item = QTableWidgetItem(f"No correlations found for {self.filter_type}")
                no_results_item.setTextAlignment(Qt.AlignCenter)
                no_results_item.setForeground(QColor(THEME['text_secondary']))
                self.correlation_table.setItem(0, 0, no_results_item)
                self.correlation_table.setSpan(0, 0, 1, 4)  # Span across all columns
            
            # Update overlay with new correlations
            self._update_overlay()
            
        except Exception as e:
            print(f"Error finding correlations: {e}")
    
    def _on_correlation_selected(self):
        try:
            selected_rows = self.correlation_table.selectedIndexes()
            if not selected_rows or not self.correlations:
                # Clear all highlights if nothing selected
                for timeline in self.pcap_timelines:
                    timeline.clear_highlights()
                return
            
            row = selected_rows[0].row()
            if row < len(self.correlations):
                event1, event2, time_diff = self.correlations[row]
                
                # Find and highlight events on their respective timelines
                for timeline in self.pcap_timelines:
                    if timeline.pcap_name == event1.pcap_name:
                        timeline.set_highlighted_events([event1])
                    elif timeline.pcap_name == event2.pcap_name:
                        timeline.set_highlighted_events([event2])
                    else:
                        timeline.clear_highlights()  # Clear other timelines
                
        except Exception as e:
            print(f"Error handling correlation selection: {e}")

    def load_timeline_data(self, timeline_data):
        
        # Load timeline data from external source
        try:
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

            # Normalize timestamps per PCAP 
            for pcap_name, events in timeline_data.items():
                if not events:
                    continue
                base = min(e.timestamp for e in events)
                for e in events:
                    e.normalized_ts = (e.timestamp - base).total_seconds()


            if not all_events:
                # Show no data message
                no_data_label = QLabel("No events found for selected fields")
                no_data_label.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px")
                self.timeline_layout.addWidget(no_data_label)
                
                # Clear correlation table
                self.correlation_table.setRowCount(0)
                self.correlation_count_label.setText("0 correlations")
                return
            
            start_time = min(e.timestamp for e in all_events)
            end_time = max(e.timestamp for e in all_events)

            # Create timeline for each file
            for pcap_name, events in sorted(timeline_data.items()):
                if events:
                    timeline = PCAPTimeline(pcap_name, events, start_time, end_time,
                                           pixels_per_second=self.pixels_per_second)
                    self.pcap_timelines.append(timeline)
                    self.timeline_layout.addWidget(timeline)

            # Add timestamp axis
            self.timestamp_axis = TimestampAxis(start_time, end_time,
                                               pixels_per_second=self.pixels_per_second)
            self.timeline_layout.addWidget(self.timestamp_axis)

            self.timeline_layout.addStretch()

            # Ensure overlay is created
            if not self.overlay:
                QTimer.singleShot(100, self._create_overlay)

            # Find correlations
            QTimer.singleShot(150, self._find_correlations)
            
        except Exception as e:
            print(f"Error loading timeline data: {e}")