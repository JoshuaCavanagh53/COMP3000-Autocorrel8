from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QFrame, QComboBox, QTableWidget, QHeaderView, QTableWidgetItem,
    QScrollArea, QCheckBox
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath
from collections import Counter
import math

from themes import THEME


class PieChartWidget(QWidget):
   
    def __init__(self, title="Distribution", show_legend=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.data = []  
        self.show_legend = show_legend
        self.hovered_slice = None
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        
        # Chart positioning
        self.chart_center_x = 0
        self.chart_center_y = 0
        self.chart_radius = 0
        
    def set_data(self, data_dict, color_map=None):
        
        # Set the data for the pie chart
    
        if not data_dict:
            self.data = []
            self.update()
            return
        
        # Default color palette
        default_colors = [
            '#4682B4',  # Steel Blue
            '#32CD32',  # Lime Green
            '#FFD700',  # Gold
            '#FF6347',  # Tomato
            '#9370DB',  # Medium Purple
            '#20B2AA',  # Light Sea Green
            '#FF69B4',  # Hot Pink
            '#FFA500',  # Orange
            '#87CEEB',  # Sky Blue
            '#98FB98',  # Pale Green
        ]
        
        # Sort by value 
        sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        
        self.data = []
        for i, (label, value) in enumerate(sorted_items):
            if color_map and label in color_map:
                color = color_map[label]
            else:
                color = default_colors[i % len(default_colors)]
            self.data.append((label, value, color))
        
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), QColor(THEME['timeline_bg']))
        
        if not self.data:
            # Draw "No Data" message
            painter.setPen(QColor(THEME['text_secondary']))
            font = QFont()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "No data to display")
            return
        
        # Calculate total
        total = sum(value for _, value, _ in self.data)
        if total == 0:
            return
        
        # Calculate chart dimensions
        width = self.width()
        height = self.height()
        
        # Reserve space for legend on the right if enabled
        legend_width = 200 if self.show_legend else 0
        chart_width = width - legend_width - 40
        chart_height = height - 80  # Space for title
        
        # Chart positioning
        chart_size = min(chart_width, chart_height)
        self.chart_radius = chart_size // 2 - 20
        self.chart_center_x = 20 + chart_size // 2
        self.chart_center_y = 60 + chart_size // 2
        
        # Draw title
        painter.setPen(QColor(THEME['text_primary']))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(QRect(0, 10, width, 30), Qt.AlignCenter, self.title)
        
        # Draw pie slices
        start_angle = 90 * 16  # Start at top 
        
        for i, (label, value, color) in enumerate(self.data):
            # Calculate slice angle
            percentage = value / total
            span_angle = int(percentage * 360 * 16)
            
            # Draw slice
            slice_color = QColor(color)
            
            # Highlight hovered slice
            if self.hovered_slice == i:
                slice_color = slice_color.lighter(120)
                # Draw slightly larger for hover effect
                hover_offset = 5
                offset_angle = (start_angle + span_angle // 2) / 16
                offset_x = int(hover_offset * math.cos(math.radians(offset_angle)))
                offset_y = int(-hover_offset * math.sin(math.radians(offset_angle)))
                
                painter.setBrush(QBrush(slice_color))
                painter.setPen(QPen(QColor(THEME['border']), 2))
                painter.drawPie(
                    self.chart_center_x - self.chart_radius + offset_x,
                    self.chart_center_y - self.chart_radius + offset_y,
                    self.chart_radius * 2,
                    self.chart_radius * 2,
                    start_angle,
                    span_angle
                )
            else:
                painter.setBrush(QBrush(slice_color))
                painter.setPen(QPen(QColor(THEME['border']), 1))
                painter.drawPie(
                    self.chart_center_x - self.chart_radius,
                    self.chart_center_y - self.chart_radius,
                    self.chart_radius * 2,
                    self.chart_radius * 2,
                    start_angle,
                    span_angle
                )
            
            # Draw percentage label on slice if it's large enough
            if percentage > 0.05:  # Only show label if > 5%
                label_angle = (start_angle + span_angle // 2) / 16
                label_radius = self.chart_radius * 0.7
                label_x = self.chart_center_x + int(label_radius * math.cos(math.radians(label_angle)))
                label_y = self.chart_center_y - int(label_radius * math.sin(math.radians(label_angle)))
                
                # Draw percentage
                painter.setPen(QColor('white'))
                percent_font = QFont()
                percent_font.setPointSize(10)
                percent_font.setBold(True)
                painter.setFont(percent_font)
                percent_text = f"{percentage * 100:.1f}%"
                painter.drawText(QRect(label_x - 40, label_y - 10, 80, 20), 
                               Qt.AlignCenter, percent_text)
            
            start_angle -= span_angle
        
        # Draw legend if enabled
        if self.show_legend:
            self._draw_legend(painter, legend_width, width, height)
    
    def _draw_legend(self, painter, legend_width, total_width, total_height):
        """Draw the legend on the right side"""
        legend_x = total_width - legend_width + 10
        legend_y = 60
        
        painter.setPen(QColor(THEME['text_primary']))
        legend_font = QFont()
        legend_font.setPointSize(9)
        painter.setFont(legend_font)
        
        total = sum(value for _, value, _ in self.data)
        
        for i, (label, value, color) in enumerate(self.data):
            y_pos = legend_y + i * 30
            
            # Draw color box
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(QPen(QColor(THEME['border']), 1))
            painter.drawRect(legend_x, y_pos, 15, 15)
            
            # Draw label
            painter.setPen(QColor(THEME['text_primary']))
            percentage = (value / total) * 100
            legend_text = f"{label[:20]}"  # Truncate long labels
            painter.drawText(legend_x + 20, y_pos + 12, legend_text)
            
            # Draw count and percentage
            painter.setPen(QColor(THEME['text_secondary']))
            count_text = f"{value} ({percentage:.1f}%)"
            painter.drawText(legend_x + 20, y_pos + 24, count_text)
    
    def mouseMoveEvent(self, event):
        
        # Handle mouse hover for slice highlighting
        if not self.data:
            return
        
        # Calculate mouse position relative to chart center
        dx = event.x() - self.chart_center_x
        dy = event.y() - self.chart_center_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Check if mouse is over the pie chart
        if distance <= self.chart_radius:
            # Calculate angle
            angle = math.degrees(math.atan2(-dy, dx))
            if angle < 0:
                angle += 360
            
            # Normalize to start from top (90 degrees)
            angle = (90 - angle) % 360
            
            # Find which slice is hovered
            total = sum(value for _, value, _ in self.data)
            current_angle = 0
            
            for i, (label, value, color) in enumerate(self.data):
                percentage = value / total
                slice_angle = percentage * 360
                
                if current_angle <= angle < current_angle + slice_angle:
                    if self.hovered_slice != i:
                        self.hovered_slice = i
                        self.update()
                    return
                
                current_angle += slice_angle
        
        # Mouse not over any slice
        if self.hovered_slice is not None:
            self.hovered_slice = None
            self.update()


class DistributionChartWidget(QFrame):
   
    # Complete widget for displaying distribution analysis with pie chart and data table

    def __init__(self):
        super().__init__()
        self.current_data_type = 'protocol'
        self.pcap_data = {}  # Store data from all PCAPs
        self.show_correlated_only = True 
        
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
        layout.setSpacing(15)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Distribution Analysis")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Data type selector
        type_label = QLabel("Analyze:")
        type_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(['protocol', 'domain', 'ip', 'port'])
        self.type_combo.setStyleSheet(f"""
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
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        header_layout.addWidget(self.type_combo)
        
        self.correlated_checkbox = QCheckBox("Show correlated only")
        self.correlated_checkbox.setChecked(True)
        self.correlated_checkbox.setStyleSheet(f"""
            QCheckBox {{
                color: {THEME['text_primary']};
                font-size: 12px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {THEME['border']};
                border-radius: 3px;
                background-color: {THEME['button_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {THEME['accent']};
                border-color: {THEME['accent']};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iMTIiIHZpZXdCb3g9IjAgMCAxMiAxMiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDNMNC41IDguNUwyIDYiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPgo=);
            }}
            QCheckBox::indicator:hover {{
                border-color: {THEME['accent']};
            }}
        """)
        self.correlated_checkbox.stateChanged.connect(self._on_filter_changed)
        header_layout.addWidget(self.correlated_checkbox)
        
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
        refresh_btn.clicked.connect(self._update_chart)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)
        
        # Content area with chart and table side by side
        content_layout = QHBoxLayout()
        
        # Pie chart
        self.pie_chart = PieChartWidget(title="Protocol Distribution", show_legend=True)
        self.pie_chart.setMinimumWidth(450)
        content_layout.addWidget(self.pie_chart, stretch=3)
        
        # Data table
        table_container = QVBoxLayout()
        
        table_title = QLabel("Detailed Breakdown")
        table_title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: bold;
        """)
        table_container.addWidget(table_title)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(3)
        self.data_table.setHorizontalHeaderLabels(['Item', 'Count', 'Percentage'])
        self.data_table.setMinimumWidth(350)
        self.data_table.setMaximumHeight(400)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.SingleSelection)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(True)
        self.data_table.setStyleSheet(f"""
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
            }}
            QTableWidget::item:alternate {{
                background-color: #3a3a3a;
            }}
            QTableWidget::item:selected {{
                background-color: {THEME['accent']};
                color: white;
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
        """)
        
        # Set column widths
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        table_container.addWidget(self.data_table)
        content_layout.addLayout(table_container, stretch=2)
        
        layout.addLayout(content_layout)
        
        # Summary statistics at the bottom
        stats_layout = QHBoxLayout()
        
        self.total_label = QLabel("Total Items: 0")
        self.total_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
            padding: 5px;
        """)
        stats_layout.addWidget(self.total_label)
        
        stats_layout.addStretch()
        
        self.unique_label = QLabel("Unique Values: 0")
        self.unique_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
            padding: 5px;
        """)
        stats_layout.addWidget(self.unique_label)
        
        layout.addLayout(stats_layout)
    
    def _on_type_changed(self, data_type):
        
        # Handle data type change
        self.current_data_type = data_type
        self._update_chart()
    
    def _on_filter_changed(self):
        
        # Handle correlation filter toggle
        self.show_correlated_only = self.correlated_checkbox.isChecked()
        self._update_chart()
    
    def _update_chart(self):
        
        # Update the chart and table with current data
        if not self.pcap_data:
            return
        
        # Aggregate data across all PCAPs
        all_values = []
        pcap_values = {}  # Track which values appear in which PCAPs
        
        for pcap_name, events in self.pcap_data.items():
            pcap_values[pcap_name] = set()
            for event in events:
                if event.event_type == self.current_data_type:
                    all_values.append(event.value)
                    pcap_values[pcap_name].add(event.value)
        
        if not all_values:
            self.pie_chart.set_data({})
            self.data_table.setRowCount(0)
            self.total_label.setText("Total Items: 0")
            self.unique_label.setText("Unique Values: 0")
            return
        
        if self.show_correlated_only and len(self.pcap_data) > 1:
            # Find values that appear in at least 2 different PCAPs
            correlated_values = set()
            all_unique_values = set(all_values)
            
            for value in all_unique_values:
                # Count how many PCAPs have this value
                pcap_count = sum(1 for pcap_set in pcap_values.values() if value in pcap_set)
                if pcap_count >= 2:
                    correlated_values.add(value)
            
            # Filter all_values to only include correlated ones
            all_values = [v for v in all_values if v in correlated_values]
            
            if not all_values:
                # No correlations found
                self.pie_chart.set_data({})
                self.data_table.setRowCount(0)
                self.total_label.setText("Total Items: 0")
                self.unique_label.setText("Unique Values: 0 (No correlations found)")
                return
        
        # Count occurrences
        value_counts = Counter(all_values)
        
        # Update chart
        chart_title = f"{self.current_data_type.capitalize()} Distribution"
        if self.show_correlated_only and len(self.pcap_data) > 1:
            chart_title += " (Correlated Only)"
        self.pie_chart.title = chart_title
        self.pie_chart.set_data(dict(value_counts))
        
        # Update table
        self._populate_table(value_counts, pcap_values if self.show_correlated_only else None)
        
        # Update statistics
        total_count = len(all_values)
        unique_count = len(value_counts)
        self.total_label.setText(f"Total Items: {total_count:,}")
        
        if self.show_correlated_only and len(self.pcap_data) > 1:
            self.unique_label.setText(f"Correlated Values: {unique_count:,}")
        else:
            self.unique_label.setText(f"Unique Values: {unique_count:,}")
    
    def _populate_table(self, value_counts, pcap_values=None):
        
        # Populate the data table
        total = sum(value_counts.values())
        sorted_items = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Adjust columns based on whether we're showing PCAP info
        if pcap_values and len(self.pcap_data) > 1:
            self.data_table.setColumnCount(4)
            self.data_table.setHorizontalHeaderLabels(['Item', 'Count', 'Percentage', 'Found in PCAPs'])
        else:
            self.data_table.setColumnCount(3)
            self.data_table.setHorizontalHeaderLabels(['Item', 'Count', 'Percentage'])
        
        self.data_table.setRowCount(0)
        self.data_table.setSortingEnabled(False)
        self.data_table.setRowCount(len(sorted_items))
        
        for row, (value, count) in enumerate(sorted_items):
            # Item name
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            self.data_table.setItem(row, 0, item)
            
            # Count
            count_item = QTableWidgetItem(str(count))
            count_item.setData(Qt.UserRole, count)
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(row, 1, count_item)
            
            # Percentage
            percentage = (count / total) * 100
            percent_item = QTableWidgetItem(f"{percentage:.2f}%")
            percent_item.setData(Qt.UserRole, percentage)
            percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.data_table.setItem(row, 2, percent_item)
            
            if pcap_values and len(self.pcap_data) > 1:
                pcaps_with_value = [pcap_name for pcap_name, values in pcap_values.items() 
                                   if value in values]
                pcap_count = len(pcaps_with_value)
                pcap_info = QTableWidgetItem(f"{pcap_count}/{len(self.pcap_data)}")
                pcap_info.setData(Qt.UserRole, pcap_count)
                pcap_info.setTextAlignment(Qt.AlignCenter)
                pcap_info.setToolTip(f"Found in: {', '.join(pcaps_with_value)}")
                self.data_table.setItem(row, 3, pcap_info)
        
        # Adjust column widths
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        if pcap_values and len(self.pcap_data) > 1:
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        self.data_table.setSortingEnabled(True)
    
    def load_data(self, timeline_data):
        
        # Load data from timeline events
    
        self.pcap_data = timeline_data
        self._update_chart()