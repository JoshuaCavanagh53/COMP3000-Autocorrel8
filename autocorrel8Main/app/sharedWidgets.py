from themes import THEME

from PyQt5.QtWidgets import (
     QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QFileSystemModel, QTreeView, QButtonGroup
)

from PyQt5.QtCore import Qt, QDir, pyqtSignal




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

class ButtonLayout(QFrame):
    
    def __init__(self, button1, button2, button3):
        super().__init__()
        self.setFixedHeight(75)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(15)
        self.button1 = button1
        self.button2 = button2
        self.button3 = button3

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

        group = QButtonGroup(self)
        group.setExclusive(True)

        # Add buttons
        self.case_overview_button = QPushButton(button1)
        self.correlation_button = QPushButton(button2)
        self.add_source_button = QPushButton(button3)

        # Add buttons to layout
        for btn in (self.case_overview_button, self.correlation_button, self.add_source_button):
            btn.setCheckable(True)
            btn.setFixedSize(120, 40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(button_style)
            layout.addWidget(btn)
            group.addButton(btn)
      
        self.setLayout(layout)

    def add_source_clicked(self, function):
        self.add_source_button.clicked.connect(function)

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