from ctypes import alignment
from PyQt5.QtWidgets import ( QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
   QScrollArea,  QComboBox, QStackedWidget, QLabel, QSlider, QButtonGroup, QTableWidget, QHeaderView, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QRect, QPoint, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont
from datetime import datetime, timedelta

from distributionChart import *

from themes import THEME

from timelineCorrelation import *

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
        self.distribution_chart_widget = DistributionChartWidget()
        self.cross_pcap_widget = QLabel("Cross-PCAP Communication View - Coming Soon")
        self.cross_pcap_widget.setStyleSheet(f"color: {THEME['text_secondary']}; padding: 20px;")

        
        
        # Add widgets to stack 
        self.stacked_widget.addWidget(self.timeline_widget)
        self.stacked_widget.addWidget(self.distribution_chart_widget)
        self.stacked_widget.addWidget(self.cross_pcap_widget)

        layout.addWidget(self.stacked_widget)

        # Connect buttons to switch views
        button_layout.timeline_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        button_layout.host_interaction_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        button_layout.cross_pcap_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))

        # Push everything to top
        layout.addStretch()

        self.setLayout(layout)

    def load_timeline_data(self, timeline_data):
        
        # Forward timeline data to all sub-widgets
        self.timeline_widget.load_timeline_data(timeline_data)
        self.distribution_chart_widget.load_data(timeline_data)


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
        self.timeline_button = QPushButton("Timeline")
        self.host_interaction_button = QPushButton("Distribution Chart")
        self.cross_pcap_button = QPushButton("Cross PCAP Interaction")
    
        
        for btn in (self.timeline_button, self.host_interaction_button, self.cross_pcap_button):
            btn.setCheckable(True) 
            btn.setFixedSize(120, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            group.addButton(btn)

        # Set Default button selection
        self.timeline_button.setChecked(True)

        self.setLayout(layout)
