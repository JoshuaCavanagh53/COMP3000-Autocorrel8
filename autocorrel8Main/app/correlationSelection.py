# Import necessary PyQt5 modules

from PyQt5.QtWidgets import (
  QWidget, QLabel, 
    QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QCheckBox
)
import os
from themes import THEME
from PyQt5.QtCore import Qt

class CorrelationSelectionTable(QFrame):
    def __init__(self, path):
        super().__init__()
        
        self.setMaximumHeight(400)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.path = path
        self.checkboxes = {} 

        self.srcIPSelected = False
        self.dstIPSelected = False
        self.protocolsSelected = False
        self.dnsQuerySelected = False
        self.httpHostSelected = False
        self.tlsSNISelected = False

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

        self.field_table = self.create_table()
        layout.addWidget(self.field_table)

        self.correlation_button = QPushButton("Attempt Correlation")
        self.correlation_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['accent']};
            }}
            QPushButton:pressed {{
                background-color: {THEME['button_checked']}
            }}
        """)
        self.correlation_button.clicked.connect(self.update_selection_states)
        layout.addWidget(self.correlation_button)

        self.setLayout(layout)

    def create_table(self):
        self.correlation_selection_table = QTableWidget()

        # Field names are now row labels
        self.field_names = [
            "Src IP",
            "Dst IP",
            "Protocols",
            "DNS Query",
            "HTTP Host",
            "TLS SNI"
        ]

        self.correlation_selection_table.setRowCount(len(self.field_names))

        # Set row headers to field names
        self.correlation_selection_table.setVerticalHeaderLabels(self.field_names)
        self.correlation_selection_table.verticalHeader().setVisible(True)

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

        self.populate_table()

        return self.correlation_selection_table

    def populate_table(self):
        self.uploaded_files = []
        self.evidence_directory = self.path + "/evidence"

        for filename in os.listdir(self.evidence_directory):
            full_path = os.path.join(self.evidence_directory, filename)
            if os.path.isfile(full_path):
                self.uploaded_files.append(filename)

        # Filenames are now column headers
        self.correlation_selection_table.setColumnCount(len(self.uploaded_files))
        self.correlation_selection_table.setHorizontalHeaderLabels(self.uploaded_files)
        self.correlation_selection_table.horizontalHeader().setStretchLastSection(False)

        for col in range(len(self.uploaded_files)):
            self.correlation_selection_table.setColumnWidth(col, 150)

        # Add checkboxes — rows are fields, columns are files
        for row, field_name in enumerate(self.field_names):
            for col, filename in enumerate(self.uploaded_files):
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 12px;")

                self.checkboxes[(filename, field_name)] = checkbox
                checkbox.stateChanged.connect(self.update_selection_states)

                cell_widget = QWidget()
                cell_layout = QHBoxLayout(cell_widget)
                cell_layout.addWidget(checkbox)
                cell_layout.setAlignment(Qt.AlignCenter)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                self.correlation_selection_table.setCellWidget(row, col, cell_widget)

    def update_selection_states(self):
        self.srcIPSelected = False
        self.dstIPSelected = False
        self.protocolsSelected = False
        self.dnsQuerySelected = False
        self.httpHostSelected = False
        self.tlsSNISelected = False
        
        for (filename, field_name), checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                if field_name == "Src IP":
                    self.srcIPSelected = True
                elif field_name == "Dst IP":
                    self.dstIPSelected = True
                elif field_name == "Protocols":
                    self.protocolsSelected = True
                elif field_name == "DNS Query":
                    self.dnsQuerySelected = True
                elif field_name == "HTTP Host":
                    self.httpHostSelected = True
                elif field_name == "TLS SNI":
                    self.tlsSNISelected = True
        
        print("=== Selection States ===")
        print(f"Src IP: {self.srcIPSelected}")
        print(f"Dst IP: {self.dstIPSelected}")
        print(f"Protocols: {self.protocolsSelected}")
        print(f"DNS Query: {self.dnsQuerySelected}")
        print(f"HTTP Host: {self.httpHostSelected}")
        print(f"TLS SNI: {self.tlsSNISelected}")
        print("========================")
    
    def get_selected_fields_by_file(self):
        selected_by_file = {}
        
        for (filename, field_name), checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                if filename not in selected_by_file:
                    selected_by_file[filename] = []
                selected_by_file[filename].append(field_name)
        
        return selected_by_file
    

class BrowserLogSelection(QFrame):
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # File picker for chrome history
        self.chrome_history_btn = QPushButton("Select Chrome History DB")
        self.chrome_history_path = None

        # File picker for Firefox history
        self.firefox_history_btn = QPushButton("Select Firefox history DB")
        self.firefox_history_path = None
        
        layout.addWidget(QLabel("Browser Logs"))
        layout.addWidget(self.chrome_history_btn)
        layout.addWidget(self.firefox_history_btn)

        self.setLayout(layout)