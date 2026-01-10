# Import necessary PyQt5 modules
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QFileSystemModel, QTreeView,
)
from PyQt5.QtCore import Qt, QDir
import sys




# Color schemes
DARK_THEME = {
    'background': '#1E1E1E',
    'surface': '#252526',
    'surface_elevated': '#2D2D30',
    'border': '#3E3E42',
    'text_primary': '#CCCCCC',
    'text_secondary': '#858585',
    'accent': '#007ACC',
    'accent_hover': '#1C97EA',
    'nav_bg': '#2D2D30',
    'button_bg': '#3E3E42',
    'button_checked': '#094771',
}

LIGHT_THEME = {
    'background': '#FFFFFF',
    'surface': '#F5F5F5',
    'surface_elevated': '#FFFFFF',
    'border': '#E0E0E0',
    'text_primary': '#1E1E1E',
    'text_secondary': '#616161',
    'accent': '#0078D4',
    'accent_hover': '#106EBE',
    'nav_bg': '#F3F3F3',
    'button_bg': '#E8E8E8',
    'button_checked': '#CCE4F7',
}

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


class DataSources(QFrame):
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

        

class SourceOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(450)
        self.setFixedWidth(800)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add title
        title = QLabel("Source Overview")
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
        self.setLayout(layout)


class DataOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(400)
        self.setFixedWidth(1525)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add title
        title = QLabel("Data Overview")
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
        self.setLayout(layout)


class InvestigatorNotes(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(450)
        self.setFixedWidth(1075)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Add title
        title = QLabel("Investigator Notes")
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
        self.setLayout(layout)


# Main correlation window
class CorrelationDashBoard(QMainWindow):
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
        
        # Data sources box 
        data_sources = DataSources(self.path)
        top_boxes_layout.addWidget(data_sources, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        # Data overview box 
        data_overview = DataOverview()
        top_boxes_layout.addWidget(data_overview, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        # Add stretch to push everything to the left
        top_boxes_layout.addStretch()
        
        # Add the horizontal layout to the main content layout
        content_layout.addLayout(top_boxes_layout)
        
        # Create horizontal layout for SourceOverview and InvestigatorNotes
        bottom_boxes_layout = QHBoxLayout()
        bottom_boxes_layout.setSpacing(15)
        
        # Data source overview (left)
        source_overview = SourceOverview()
        bottom_boxes_layout.addWidget(source_overview, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Investigator notes (right)
        investigator_notes = InvestigatorNotes()
        bottom_boxes_layout.addWidget(investigator_notes, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        # Add stretch to push everything to the left
        bottom_boxes_layout.addStretch()
        
        # Add the bottom horizontal layout to the main content layout
        content_layout.addLayout(bottom_boxes_layout)

        # Add space at the bottom
        content_layout.addSpacing(20)
        
        # Build from the top down
        content_layout.addStretch()

        # Add the container to the main layout
        main_layout.addWidget(content_container)


# Start the application 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CorrelationDashBoard(path=r"path_to_case_folder")
    window.show()
    sys.exit(app.exec())