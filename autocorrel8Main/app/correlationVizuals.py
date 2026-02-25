from ctypes import alignment
from PyQt5.QtWidgets import ( QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
   QScrollArea,  QComboBox, QStackedWidget, QLabel, QSlider, QButtonGroup, QTableWidget, QHeaderView, QTableWidgetItem, QAbstractItemView
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from collections import defaultdict
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
        self.incognito_gap_widget = IncognitoGapWidget()

        # Add widgets to stack 
        self.stacked_widget.addWidget(self.correlation_table_widget)
        self.stacked_widget.addWidget(self.distribution_chart_widget)
        self.stacked_widget.addWidget(self.incognito_gap_widget)

        layout.addWidget(self.stacked_widget)

        # Store reference to timeline widget
        self.timeline_widget = None
        
        # Store timeline data
        self.timeline_data = None

        # Connect buttons to switch views
        button_layout.correlation_table_button.clicked.connect(self.show_correlation_table_mode)
        button_layout.distribution_button.clicked.connect(self.show_distribution_mode)
        button_layout.incognito_gap_button.clicked.connect(self.show_cross_pcap_mode)

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
        
        # Title row with mode filter combo
        title_row = QHBoxLayout()
        title = QLabel("Correlations Found")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            font-weight: bold;
        """)
        title_row.addWidget(title)
        title_row.addStretch()
        
        mode_label = QLabel("Show:")
        mode_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        title_row.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(['Found in Both', 'Found Multiple Times'])
        self.mode_combo.setToolTip(
            "Found in Both, only events that appear across multiple PCAPs\n"
            "Found Multiple Times, any event with more than one occurrence"
        )
        self.mode_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 11px;
                min-width: 160px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                selection-background-color: {THEME['accent']};
            }}
        """)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        title_row.addWidget(self.mode_combo)
        layout.addLayout(title_row)
        
        # Table — Value / Type / Count / Sources
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Value", "Type", "Count", "Sources"])
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
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
        
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 200)  # Value
        self.table.setColumnWidth(1, 80)   # Type
        self.table.setColumnWidth(2, 55)   # Count
        self.table.verticalHeader().setVisible(False)
        
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        layout.addWidget(self.table)
        
        # Internal state
        self.timeline_widget = None
        self.current_rows = []       # rows currently displayed, for selection lookups
        self.grouped_both = {}       # (type, value) → entry dict — appears in 2 or more PCAPs
        self.grouped_multiple = {}   # (type, value) → entry dict — appears 2 or more times anywhere
        
        self.setLayout(layout)
    
    def load_data(self, timeline_data):

        # Receive fresh timeline data, recompute groups, and refresh the table
        if not timeline_data:
            self.grouped_both = {}
            self.grouped_multiple = {}
            self.current_rows = []
            self.table.setRowCount(0)
            return
        
        # Build per-key counts across PCAPs
        events_by_key = defaultdict(lambda: defaultdict(list))  # key, pcap, [events]
        
        for filename, events in timeline_data.items():
            for event in events:
                key = (event.event_type, event.value)
                events_by_key[key][event.pcap_name].append(event)
        
        self.grouped_both = {}
        self.grouped_multiple = {}
        
        for key, pcap_dict in events_by_key.items():
            total = sum(len(evs) for evs in pcap_dict.values())
            entry = {
                'type': key[0],
                'value': key[1],
                'key': key,
                'pcaps': dict(pcap_dict),
                'count': total,
                'sources': set(pcap_dict.keys()),
            }
            if len(pcap_dict) >= 2:
                self.grouped_both[key] = entry
            if total >= 2:
                self.grouped_multiple[key] = entry
        
        self._apply_filter()
    
    def _apply_filter(self):

        # Populate the table rows based on the current mode combo selection
        mode = self.mode_combo.currentText()
        grouped = self.grouped_both if mode == 'Found in Both' else self.grouped_multiple
        
        # Sort: count desc, then value alphabetically
        rows = sorted(grouped.values(), key=lambda x: (-x['count'], str(x['value'])))
        self.current_rows = rows
        
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        if not rows:
            self.table.setRowCount(1)
            item = QTableWidgetItem("No correlations found")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(THEME['text_secondary']))
            self.table.setItem(0, 0, item)
            self.table.setSpan(0, 0, 1, 4)
            return
        
        self.table.setRowCount(len(rows))
        for row, entry in enumerate(rows):
            # Value
            value_item = QTableWidgetItem(str(entry['value']))
            value_item.setToolTip(str(entry['value']))
            value_item.setData(Qt.UserRole, entry['key'])
            self.table.setItem(row, 0, value_item)
            
            # Type
            self.table.setItem(row, 1, QTableWidgetItem(entry['type'].upper()))
            
            # Count (colour-coded)
            count_item = QTableWidgetItem(str(entry['count']))
            count_item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if entry['count'] >= 10:
                count_item.setForeground(QColor("#FF4444"))
            elif entry['count'] >= 4:
                count_item.setForeground(QColor("#FFA500"))
            else:
                count_item.setForeground(QColor(THEME['accent']))
            self.table.setItem(row, 2, count_item)
            
            # Sources
            sources_str = ', '.join(sorted(entry['sources']))
            sources_item = QTableWidgetItem(sources_str)
            sources_item.setToolTip(sources_str)
            self.table.setItem(row, 3, sources_item)
        
        self.table.setSortingEnabled(True)
    
    def _on_mode_changed(self, label):

        # Re-filter the table and sync the timeline to show matching events
        self._apply_filter()
        if self.timeline_widget:
            self.timeline_widget.filter_mode = (
                'found_in_both' if label == 'Found in Both' else 'found_multiple_times'
            )
            self.timeline_widget._find_correlations()

    def set_timeline_widget(self, timeline_widget):

        # Store reference to the timeline widget for highlighting and panel sync
        self.timeline_widget = timeline_widget
    
    def on_row_selected(self):

        # Handle row selection, highlight matching events and open the info panel
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row >= len(self.current_rows):
            return
        
        entry = self.current_rows[row]
        
        if self.timeline_widget and hasattr(self.timeline_widget, 'highlight_group'):
            self.timeline_widget.highlight_group(entry['type'], entry['value'])
        


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
        self.incognito_gap_button = QPushButton("Incognito Gaps")
    
        # Configure buttons
        for btn in (self.correlation_table_button, self.distribution_button, self.incognito_gap_button):
            btn.setCheckable(True) 
            btn.setFixedSize(115, 35)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            group.addButton(btn)

        # Set Default button selection
        self.correlation_table_button.setChecked(True)

        self.setLayout(layout)


# Visualization for gaps
class IncognitoGapWidget(QFrame):

    # Display detected incognito browsing gaps
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Table title
        title = QLabel("Potential Incognito Gaps Detected")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)


        # Table 
        self.gap_table = QTableWidget()
        self.gap_table.setColumnCount(7) 
        self.gap_table.setHorizontalHeaderLabels([
            "Domain", "Score", "Count", "Category", "First Seen", "Last Seen", "Duration"
        ])
        
        self.gap_table.setStyleSheet(f"""
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
        
        # Column widths
        self.gap_table.setColumnWidth(0, 220)  # Domain
        self.gap_table.setColumnWidth(1, 50)   # Score
        self.gap_table.setColumnWidth(2, 50)   # Count
        self.gap_table.setColumnWidth(3, 140)  # Category
        self.gap_table.setColumnWidth(4, 140)  # First Seen
        self.gap_table.setColumnWidth(5, 140)  # Last Seen
        self.gap_table.setColumnWidth(6, 80)   # Duration
        self.gap_table.horizontalHeader().setStretchLastSection(True)
        
        # Hide vertical header
        self.gap_table.verticalHeader().setVisible(False)

        layout.addWidget(self.gap_table)
        self.setLayout(layout)

    def load_gaps(self, gap_data):
       
        # Display gap events in table 
        # Clear existing
        self.gap_table.setRowCount(0)
        
        if not gap_data:
            return
        
        # Populate table
        self.gap_table.setRowCount(len(gap_data))
        
        for row, gap in enumerate(gap_data):
            
            # Column Domain
            domain_item = QTableWidgetItem(gap['domain'])
            self.gap_table.setItem(row, 0, domain_item)
            
            # Column Score 
            score = gap['suspiciousness']
            score_item = QTableWidgetItem(str(score))
            
            if score >= 60:
                score_item.setForeground(QColor("#FF4444"))
            elif score >= 30:
                score_item.setForeground(QColor("#FFA500"))
            else:
                score_item.setForeground(QColor("#888888"))
            
            self.gap_table.setItem(row, 1, score_item)
            
            # Column Count
            count_item = QTableWidgetItem(str(gap['count']))
            self.gap_table.setItem(row, 2, count_item)
            
            # Column Category
            category_item = QTableWidgetItem(gap['category'])
            self.gap_table.setItem(row, 3, category_item)
            
            # Column First Seen
            first_seen_str = gap['first_seen'].strftime('%Y-%m-%d %H:%M:%S')
            first_seen_item = QTableWidgetItem(first_seen_str)
            self.gap_table.setItem(row, 4, first_seen_item)
            
            # Column Last Seen
            last_seen_str = gap['last_seen'].strftime('%Y-%m-%d %H:%M:%S')
            last_seen_item = QTableWidgetItem(last_seen_str)
            self.gap_table.setItem(row, 5, last_seen_item)
            
            # Column Duration 
            duration = gap['last_seen'] - gap['first_seen']
            total_seconds = int(duration.total_seconds())
            
            # Duration
            if total_seconds == 0:
                duration_str = "< 1s" 
            elif total_seconds < 60:
                duration_str = f"{total_seconds}s"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                if seconds == 0:
                    duration_str = f"{minutes}m"
                else:
                    duration_str = f"{minutes}m {seconds}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                if minutes == 0:
                    duration_str = f"{hours}h"
                else:
                    duration_str = f"{hours}h {minutes}m"
            
            duration_item = QTableWidgetItem(duration_str)
            self.gap_table.setItem(row, 6, duration_item)