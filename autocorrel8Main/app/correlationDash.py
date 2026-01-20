from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QFileSystemModel, QTreeView, QTableWidget, QTableWidgetItem, QScrollArea, QLineEdit, QFileDialog
)
from PyQt5.QtCore import Qt , QDir, pyqtSignal
from overviewDash import DataOverview

from themes import DARK_THEME, LIGHT_THEME
from ast import Load
import sys

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

# Button layout for navigation
class ButtonLayout(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(75)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(15)

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
        self.case_overview_button = QPushButton("Case Overview")
        self.case_overview_button.setStyleSheet(button_style)
        self.case_overview_button.setFixedHeight(40)
        self.case_overview_button.setFixedWidth(120)
        self.case_overview_button.setCheckable(True)
        
        # Case overview checked by default
        self.case_overview_button.setChecked(True)

        self.case_overview_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.case_overview_button)

        self.add_source_button = QPushButton("Add Source")
        self.add_source_button.setStyleSheet(button_style)
        self.add_source_button.setFixedHeight(40)
        self.add_source_button.setFixedWidth(120)
        self.add_source_button.setCheckable(True)
        self.add_source_button.setCursor(Qt.PointingHandCursor)
        
        
        layout.addWidget(self.add_source_button)

        self.correlation_button = QPushButton("Correlation")
        self.correlation_button.setStyleSheet(button_style)
        self.correlation_button.setFixedHeight(40)
        self.correlation_button.setFixedWidth(120)
        self.correlation_button.setCheckable(True)
        self.correlation_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.correlation_button)

        self.setLayout(layout)

    def add_source_clicked(self, function):
        self.add_source_button.clicked.connect(function)

class DataSources(QFrame):

    fileSelected = pyqtSignal(str)

    def __init__(self, start_path=r"path"):
        super().__init__()
        self.setFixedHeight(400)
        self.setFixedWidth(350)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("Data Sources")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        # File explorer (QTreeView)
        self.model = QFileSystemModel()
        self.model.setReadOnly(True)

        # If no path provided, use home directory
        if start_path is None:
            start_path = QDir.homePath()

        self.model.setRootPath(start_path)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(start_path))

        self.tree.selectionModel().selectionChanged.connect(self._on_selection_changed)

        self.tree.setStyleSheet(f"""
            QTreeView {{
                background-color: {THEME['surface']};
                color: {THEME['text_primary']};
                border: none;
                outline: 0;
            }}

            QTreeView::item {{
                color: {THEME['text_primary']};
                padding: 2px 4px;
            }}

            QTreeView::item:selected {{
                background-color: {THEME['accent']};
                color: {THEME['text_primary']};
            }}

            /* Restore expand/collapse arrows */
            QTreeView::branch:has-children:closed,
            QTreeView::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url(icons/arrow-right.png);
            }}

            QTreeView::branch:has-children:open,
            QTreeView::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url(icons/arrow-down.png);
            }}
        """)


        # Hide columns except the name 
        self.tree.setHeaderHidden(True)
        self.tree.setColumnHidden(1, True)  
        self.tree.setColumnHidden(2, True)  
        self.tree.setColumnHidden(3, True) 

        layout.addWidget(self.tree)

        # Frame styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        self.setLayout(layout)

    def _on_selection_changed(self, selected, deselected):
        index = self.tree.currentIndex()
        if not index.isValid():
            return

        path = self.model.filePath(index)
        self.fileSelected.emit(path)

# Create a selection table to select fields for correlation
class CorrelationSelectionTable(QFrame):
    def __init__(self, number_of_fields):
        super().__init__()
        self.setFixedHeight(450)
        self.setFixedWidth(800)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Set number of fields
        self.number_of_fields = number_of_fields

        # Add title
        title = QLabel("Correlation Selection")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Create table
        self.field_table = self.create_table()
        layout.addWidget(self.field_table)

        self.setLayout(layout)

    def create_table(self):
        # Table to select fields for correlation
        self.correlation_selection_table = QTableWidget()
        self.correlation_selection_table.setColumnCount(self.number_of_fields)
        self.correlation_selection_table.horizontalHeader().setStretchLastSection(False)
        self.correlation_selection_table.setColumnWidth(100, 800 // self.number_of_fields)  
        self.correlation_selection_table.verticalHeader().setVisible(False)
        self.correlation_selection_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {THEME['surface_elevated']};
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
        return self.correlation_selection_table



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

        # Main content + description container
        content_container = QWidget()
        content_container.setStyleSheet(f"background-color: {THEME['background']};") 
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(20, 15, 20, 20)  
        content_layout.setSpacing(15)  
           
        # Navigation Buttons
        button_layout = ButtonLayout()
        content_layout.addWidget(button_layout, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Create horizontal layout for DataSources and DataOverview
        top_boxes_layout = QHBoxLayout()
        top_boxes_layout.setSpacing(15)
        
        # Add DataSources box
        data_sources = DataSources(start_path=self.path)
        top_boxes_layout.addWidget(data_sources, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Add the horizontal layout to the main content layout
        content_layout.addLayout(top_boxes_layout)
        
        # Create horizontal layout 
        bottom_boxes_layout = QHBoxLayout()
        bottom_boxes_layout.setSpacing(15)

        # Data source overview (left)
        correlation_selection_table = CorrelationSelectionTable(5)
        bottom_boxes_layout.addWidget(correlation_selection_table, alignment=Qt.AlignTop | Qt.AlignLeft)
        content_layout.addLayout(bottom_boxes_layout)

        # Add stretch to push everything to the left
        top_boxes_layout.addStretch()

        main_layout.addWidget(content_container)

        # Instantiate DataOverview for packet handeling and display 
        self.data_overview = DataOverview()

        self.data_overview.get_packets_for_file("cw1.pcap")

        # Build from the top down
        content_layout.addStretch()

# Start the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CorrelationDashboard(path="C:\\Users\\jjc19\\OneDrive\\Documents\\Cases\\Case_1")
    window.show()
    sys.exit(app.exec())
        
