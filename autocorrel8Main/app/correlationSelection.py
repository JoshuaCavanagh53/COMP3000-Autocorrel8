# Import necessary PyQt5 modules

from PyQt5.QtWidgets import (
  QWidget, QLabel, 
    QHBoxLayout, QFrame, QTableWidget, QTableWidgetItem, QVBoxLayout, QPushButton, QCheckBox
)
import os
from themes import THEME
from PyQt5.QtCore import Qt

# Create a selection table to select fields for correlation
class CorrelationSelectionTable(QFrame):
    def __init__(self, path):
        super().__init__()
        
        # Set max height to keep top section compact
        self.setMaximumHeight(400)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.path = path

        # Store checkboxes
        self.checkboxes = {} 

        # Define checkboxes
        self.srcIPSelected = False
        self.dstIPSelected = False
        self.tcpSrcPortSelected = False
        self.tcpDstPortSelected = False
        self.udpSrcPortSelected = False
        self.udpDstPortSelected = False
        self.protocolsSelected = False
        self.dnsQuerySelected = False
        self.httpMethodSelected = False
        self.httpHostSelected = False
        self.tlsSNISelected = False

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

        # Attempt correlation button
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

        # Connect button to update selection states
        self.correlation_button.clicked.connect(self.update_selection_states)

        layout.addWidget(self.correlation_button)

        self.setLayout(layout)

    def create_table(self):
        # Table to select fields for correlation
        self.correlation_selection_table = QTableWidget()
        
        # Set the column names
        self.column_names = [  
            "Source",
            "Src IP",
            "Dst IP",
            "TCP Src Port",
            "TCP Dst Port",
            "UDP Src Port",
            "UDP Dst Port",
            "Protocols",
            "DNS Query",
            "HTTP Method",
            "HTTP Host",
            "TLS SNI"
        ]

        # Set number of fields
        self.number_of_fields = len(self.column_names)

        self.correlation_selection_table.setColumnCount(self.number_of_fields)
        self.correlation_selection_table.horizontalHeader().setStretchLastSection(False)
        self.correlation_selection_table.setHorizontalHeaderLabels(self.column_names)


        # Set width for each column
        for i in range(self.number_of_fields):
            self.correlation_selection_table.setColumnWidth(i, 1200 // self.number_of_fields)
        
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

        self.populate_table() 

        return self.correlation_selection_table

    def populate_table(self): 

        self.uploaded_files = []

        self.evidence_directory = self.path + "/evidence"

        for filename in os.listdir(self.evidence_directory):
            full_path = os.path.join(self.evidence_directory, filename)
            if os.path.isfile(full_path):
                self.uploaded_files.append(filename)

        self.correlation_selection_table.setRowCount(len(self.uploaded_files))

        # Add the sources
        for row, filename in enumerate(self.uploaded_files):
            item = QTableWidgetItem(filename)
            item.setFlags(Qt.ItemIsEnabled) # Cannot edit item
            self.correlation_selection_table.setItem(row, 0, item)

        # Add the checkboxes
        for row in range(len(self.uploaded_files)):
            filename = self.uploaded_files[row]
            
            for col in range(1, self.number_of_fields):
                field_name = self.column_names[col]  # Use self.column_names
                
                checkbox = QCheckBox()
                checkbox.setStyleSheet("margin-left: 12px;")
                
                # Store with key
                self.checkboxes[(filename, field_name)] = checkbox
                
                # Connect to real-time updates
                checkbox.stateChanged.connect(self.update_selection_states)
                
                cell_widget = QWidget()
                layout = QHBoxLayout(cell_widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.correlation_selection_table.setCellWidget(row, col, cell_widget)

    def update_selection_states(self):  
        
        # Update boolean variables based on checkbox states

        # Reset all to False
        self.srcIPSelected = False
        self.dstIPSelected = False
        self.tcpSrcPortSelected = False
        self.tcpDstPortSelected = False
        self.udpSrcPortSelected = False
        self.udpDstPortSelected = False
        self.protocolsSelected = False
        self.dnsQuerySelected = False
        self.httpMethodSelected = False
        self.httpHostSelected = False
        self.tlsSNISelected = False
        
        # Check all checkboxes and update booleans
        for (filename, field_name), checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                if field_name == "Src IP":
                    self.srcIPSelected = True
                elif field_name == "Dst IP":
                    self.dstIPSelected = True
                elif field_name == "TCP Src Port":
                    self.tcpSrcPortSelected = True
                elif field_name == "TCP Dst Port":
                    self.tcpDstPortSelected = True
                elif field_name == "UDP Src Port":
                    self.udpSrcPortSelected = True
                elif field_name == "UDP Dst Port":
                    self.udpDstPortSelected = True
                elif field_name == "Protocols":
                    self.protocolsSelected = True
                elif field_name == "DNS Query":
                    self.dnsQuerySelected = True
                elif field_name == "HTTP Method":
                    self.httpMethodSelected = True
                elif field_name == "HTTP Host":
                    self.httpHostSelected = True
                elif field_name == "TLS SNI":
                    self.tlsSNISelected = True
        
        # Print current state 
        print("=== Selection States ===")
        print(f"Src IP: {self.srcIPSelected}")
        print(f"Dst IP: {self.dstIPSelected}")
        print(f"TCP Src Port: {self.tcpSrcPortSelected}")
        print(f"TCP Dst Port: {self.tcpDstPortSelected}")
        print(f"UDP Src Port: {self.udpSrcPortSelected}")
        print(f"UDP Dst Port: {self.udpDstPortSelected}")
        print(f"Protocols: {self.protocolsSelected}")
        print(f"DNS Query: {self.dnsQuerySelected}")
        print(f"HTTP Method: {self.httpMethodSelected}")
        print(f"HTTP Host: {self.httpHostSelected}")
        print(f"TLS SNI: {self.tlsSNISelected}")
        print("========================")
    
    def get_selected_fields_by_file(self):
        # Get selected fields organized by filename
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