# Import necessary PyQt5 modules
from ast import Load
from ast import Load
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QFileSystemModel, QTreeView, QTableWidget, QTableWidgetItem, QScrollArea, QLineEdit, QFileDialog
)
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtGui import QPainter , QPen
from PyQt5.QtCore import Qt, QDir, QPointF, pyqtSignal ,QThread
import sys
from os.path import getsize, basename
import time
import os
import pyshark
import subprocess
import json
import shutil
from collections import Counter
from themes import DARK_THEME, LIGHT_THEME


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
        

class SourceOverview(QFrame):
    
    def __init__(self, file_list=None):
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

        # Create table
        self.file_table = self.create_table()
        layout.addWidget(self.file_table)

        # Populate table with file data if provided
        if file_list:
            self.file_table.setRowCount(len(file_list))
            for row, file_path in enumerate(file_list):

                file_name = basename(file_path)
                file_size_mb = round(getsize(file_path) / (1024 * 1024), 2)
                timestamp = time.ctime(getsize(file_path))  

                if ".pcap" in file_name:
                    source_type = "network"

                self.file_table.setItem(row, 0, QTableWidgetItem(file_name))
                self.file_table.setItem(row, 1, QTableWidgetItem(source_type))  
                self.file_table.setItem(row, 2, QTableWidgetItem(timestamp))
                self.file_table.setItem(row, 3, QTableWidgetItem(str(file_size_mb)))
                self.file_table.setItem(row, 4, QTableWidgetItem("Loaded"))  

        self.setLayout(layout)

    def create_table(self):
        # Table of uploaded file paths
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["File Path", "Source Type", "Time stamp", "File Size (MB)", "Status"])
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.setColumnWidth(0, 300)  
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setColumnWidth(2, 200)
        self.file_table.setColumnWidth(3, 100)  
        self.file_table.setColumnWidth(4, 100)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setStyleSheet(f"""
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
        return self.file_table


class PacketLoaderThread(QThread):
    
    # Background thread for loading packets
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.tshark_path = "D:\\Wireshark\\tshark.exe"
    
    def run(self):
        try:
            print(f"Starting to parse packets from: {self.file_path}")
            self.progress.emit("Parsing packets with tshark...")
            
            # Use tshark to export to JSON
            cmd = [
                self.tshark_path,
                "-r", self.file_path,
                "-T", "json",  # Output as JSON
                "-e", "frame.time_epoch",  # Timestamp
                "-e", "ip.src",  # Source IP
                "-e", "ip.dst",  # Destination IP
                "-e", "tcp.srcport",  # TCP source port
                "-e", "tcp.dstport",  # TCP destination port
                "-e", "udp.srcport",  # UDP source port
                "-e", "udp.dstport",  # UDP destination port
                "-e", "frame.protocols",  # Protocol stack
                "-e", "frame.len",  # Frame length
                "-e", "dns.qry.name",  # DNS query
                "-e", "http.request.method",  # HTTP method
                "-e", "http.host",  # HTTP host
                "-e", "tls.handshake.extensions_server_name",  # TLS SNI
            ]
            
            print(f"Running tshark command: {' '.join(cmd)}")
            
            # Run tshark and capture output
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"tshark failed: {result.stderr}")
            
            print("Parsing tshark JSON output...")
            self.progress.emit("Processing packet data...")
            
            # Parse JSON output
            tshark_packets = json.loads(result.stdout)
            
            # Convert to our format
            packets = []
            for idx, pkt in enumerate(tshark_packets):
                try:
                    packet_dict = self.convert_tshark_packet(pkt)
                    packets.append(packet_dict)
                    
                    if (idx + 1) % 1000 == 0:
                        print(f"Processed {idx + 1} packets...")
                        self.progress.emit(f"Processed {idx + 1} packets...")
                        
                except Exception as e:
                    print(f"Error converting packet {idx}: {e}")
                    continue
            
            print(f"Finished parsing {len(packets)} packets")
            self.finished.emit(packets)
            
        except subprocess.TimeoutExpired:
            print("tshark timed out")
            self.error.emit("Packet parsing timed out (file too large)")
        except Exception as e:
            print(f"Error in thread: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))
    
    def convert_tshark_packet(self, tshark_pkt):
        """Convert tshark JSON packet to our format"""
        layers = tshark_pkt.get("_source", {}).get("layers", {})
        
        # Extract core fields
        packet = {
            "timestamp": layers.get("frame.time_epoch", [None])[0],
            "src_ip": layers.get("ip.src", [None])[0],
            "dst_ip": layers.get("ip.dst", [None])[0],
            "src_port": layers.get("tcp.srcport", layers.get("udp.srcport", [None]))[0],
            "dst_port": layers.get("tcp.dstport", layers.get("udp.dstport", [None]))[0],
            "protocol": layers.get("frame.protocols", [None])[0],
            "length": layers.get("frame.len", [None])[0],
            "layers": {}
        }
        
        # Add DNS info if present
        if "dns.qry.name" in layers:
            packet["layers"]["dns"] = {
                "query": layers.get("dns.qry.name", [None])[0]
            }
        
        # Add HTTP info if present
        if "http.request.method" in layers:
            packet["layers"]["http"] = {
                "method": layers.get("http.request.method", [None])[0],
                "host": layers.get("http.host", [None])[0]
            }
        
        # Add TLS info if present
        if "tls.handshake.extensions_server_name" in layers:
            packet["layers"]["tls"] = {
                "server_name": layers.get("tls.handshake.extensions_server_name", [None])[0]
            }

        return packet


class DataOverview(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(400)
        self.setFixedWidth(1525)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Add title
        self.title = QLabel("Data Overview")
        self.title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        self.layout.addWidget(self.title)
        
        # Loading label (initially hidden)
        self.loading_label = QLabel("Loading packet data...")
        self.loading_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 14px;
            font-style: italic;
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        self.layout.addWidget(self.loading_label)
        
        # Error label (initially hidden)
        self.error_label = QLabel()
        self.error_label.setStyleSheet(f"""
            color: #ff6b6b;
            font-size: 14px;
        """)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        self.layout.addWidget(self.error_label)
        
        # Placeholder label for when no file is selected
        self.placeholder_label = QLabel("Select a file to view packet data")
        self.placeholder_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 14px;
        """)
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.placeholder_label)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        self.setLayout(self.layout)
        
        # Store the loader thread
        self.loader_thread = None

    def load_packet_chart(self, file_path):
       
        # Always remove old chart before doing anything else 
        self.remove_old_chart()

        # Load packet data and display chart
        print(f"load_packet_chart called with: {file_path}")
        
        # Check if packet list already exists
        if hasattr(self, 'packets') and self.packets and file_path == self.current_file_path:
            print("Using cached packets")
            self.on_packets_loaded(self.packets)
            return
        
        else:
            # Check if it's a PCAP file
            if not (file_path.endswith('.pcap') or file_path.endswith('.pcapng')):
                print(f"Not a PCAP file: {file_path}")
                self.show_placeholder()
                return
            
            print(f"Starting to load PCAP file: {file_path}")
            
            # Store current file path
            self.current_file_path = file_path

            # Clear previous content
            self.clear_content()
            
            # Show loading state
            self.show_loading()
            
            # Start background loading
            self.loader_thread = PacketLoaderThread(file_path)
            self.loader_thread.finished.connect(self.on_packets_loaded)
            self.loader_thread.finished.connect(self.handle_packets)
            self.loader_thread.error.connect(self.on_loading_error)
            self.loader_thread.start()

    def count_protocols(self, packets):
        proto_counts = Counter()

        for pkt in packets:
            proto_stack = pkt.get("protocol", "")
            if not proto_stack:
                continue

            # Extract the top-level protocol from the stack
            top_proto = proto_stack.split(":")[-1].upper()
            proto_counts[top_proto] += 1

        return proto_counts
    
    # Store packet for later use
    def handle_packets(self, packets): 
        print("Received packets:", len(packets)) 
        self.packets = packets
        self.protocol_counts = self.count_protocols(packets)
        print("Protocol counts:", self.protocol_counts)
        
    # Remove old charts
    def remove_old_chart(self):
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and widget not in [
                self.title,
                self.loading_label,
                self.error_label,
                self.placeholder_label
            ]:
                widget.setParent(None)
                widget.deleteLater()

    def clear_content(self):
        # Clear all dynamic content except title and status labels
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and widget not in [self.title, self.loading_label, self.error_label, self.placeholder_label]:
                widget.deleteLater()
    
    def show_loading(self):
        """Show loading indicator"""
        print("Showing loading indicator")
        self.placeholder_label.hide()
        self.error_label.hide()
        self.loading_label.setText("Loading packet data...")
        self.loading_label.show()
    
    def show_placeholder(self):
        """Show placeholder when no valid file selected"""
        print("Showing placeholder")
        self.loading_label.hide()
        self.error_label.hide()
        self.placeholder_label.show()
    
    def show_error(self, error_message):
        """Show error message"""
        print(f"Showing error: {error_message}")
        self.loading_label.hide()
        self.placeholder_label.hide()
        self.error_label.setText(f"Error loading packets: {error_message}")
        self.error_label.show()
    
    def on_packets_loaded(self, packets):
        """Called when packets finish loading"""
        print(f"on_packets_loaded called with {len(packets)} packets")
        self.loading_label.hide()
        
        if not packets:
            self.show_error("No packets found in file")
            return
        
        # Add packet chart to layout
        packet_chart = self.packet_chart(packets)
        self.layout.addWidget(packet_chart)
        
        # Add packet count info
        info_label = QLabel(f"Total packets: {len(packets)}")
        info_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
        """)
        self.layout.insertWidget(1, info_label)
    
    def on_loading_error(self, error_message):
        
        # Called when loading fails
        print(f"on_loading_error called: {error_message}")
        self.show_error(error_message)

    def packet_chart(self, packets=None):
        
        # Create line chart for packet data
        series = QLineSeries()
        pen = QPen(Qt.blue)
        pen.setWidth(2)
        series.setPen(pen)
        
        # Use packet data if provided
        if packets and len(packets) > 0:
            # Parse timestamps and count packets per second
            from collections import defaultdict
            
            packets_per_second = defaultdict(int)
            min_time = None
            max_time = None
            
            for pkt in packets:
                timestamp = pkt.get("timestamp")
                if timestamp:
                    try:
                        # Convert to float and round to nearest second
                        time_float = float(timestamp)
                        time_second = int(time_float)
                        packets_per_second[time_second] += 1
                        
                        if min_time is None or time_second < min_time:
                            min_time = time_second
                        if max_time is None or time_second > max_time:
                            max_time = time_second
                            
                    except (ValueError, TypeError):
                        continue
            
            if packets_per_second and min_time is not None:
                # Normalize time to start from 0
                normalized_data = {}
                for timestamp, count in packets_per_second.items():
                    normalized_time = timestamp - min_time
                    normalized_data[normalized_time] = count
                
                # Add all data points to the series
                for time_offset in sorted(normalized_data.keys()):
                    series.append(time_offset, normalized_data[time_offset])
                
                # If no valid data, use a placeholder
                if series.count() == 0:
                    for i in range(5):
                        series.append(i, (i + 1) * 5)
            else:
                # Fallback to demo data
                for i in range(5):
                    series.append(i, (i + 1) * 5)
        else:
            # Default demo data
            series.append(0, 5)
            series.append(1, 15)
            series.append(2, 8)
            series.append(3, 20)
            series.append(4, 12)

        chart = QChart()
        chart.setBackgroundVisible(False)
        chart.setPlotAreaBackgroundVisible(False)

        chart.addSeries(series)
        chart.setTitle("Packet Traffic Over Time")
        chart.setTitleBrush(Qt.white)
        chart.createDefaultAxes()
        chart.axisX().setTitleText("Time (seconds)")
        chart.axisY().setTitleText("Packets per Second")
        chart.legend().hide()

        # Change the color of the axis labels and lines to white
        axisX = chart.axisX()
        axisY = chart.axisY()

        axisX.setLabelsColor(Qt.white)
        axisY.setLabelsColor(Qt.white)

        axisX.setLinePenColor(Qt.white)
        axisY.setLinePenColor(Qt.white)

        axisX.setTitleBrush(Qt.white)
        axisY.setTitleBrush(Qt.white)

        axisX.setGridLineColor(Qt.white)
        axisY.setGridLineColor(Qt.white)

        axisX.setGridLineVisible(False)
        axisY.setGridLineVisible(False)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)

        return chart_view


class InvestigatorNotes(QFrame):
    def __init__(self, case_path):
        super().__init__()
        self.case_path = case_path
        self.setFixedHeight(450)
        self.setFixedWidth(1075)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Title
        title = QLabel("Investigator Notes")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        main_layout.addWidget(title, alignment=Qt.AlignTop | Qt.AlignLeft)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Scrollable notes area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setFixedHeight(350)

        self.notes_container = QWidget()
        self.notes_layout = QVBoxLayout()
        self.notes_layout.setSpacing(10)

        self.notes_container.setLayout(self.notes_layout)
        self.scroll_area.setWidget(self.notes_container)
        main_layout.addWidget(self.scroll_area)
        main_layout.addStretch()

        # Button container
        button_container = QHBoxLayout()
        button_container.addStretch()

        self.add_note_button = QPushButton("Add Note")
        self.add_note_button.setStyleSheet(f"""
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
        """)

        button_container.addWidget(self.add_note_button)
        main_layout.addLayout(button_container)

        self.add_note_button.clicked.connect(self.add_note_card)

        # Load existing notes
        self.load_notes()

        self.setLayout(main_layout)

    def add_note_card(self):
        note_card = self.create_note_card("Note Title", "This is a sample investigator note. Click to edit.")
        self.notes_layout.addWidget(note_card)

    # Get notes
    def load_notes(self):
        notes_path = os.path.join(self.case_path, "notes")
        if not os.path.exists(notes_path):
            return

        for file_name in os.listdir(notes_path):
            if file_name.endswith(".txt"):
                file_path = os.path.join(notes_path, file_name)
                with open(file_path, "r", encoding="utf-8") as f:
                    note_text = f.read()

                note_title = os.path.splitext(file_name)[0]
                note_card = self.create_note_card(note_title, note_text)
                self.notes_layout.addWidget(note_card)

    # Create note cards
    def create_note_card(self, note_title, note_text):
        note_card = QFrame()
        note_card.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
            }}
        """)
        note_layout = QVBoxLayout()
        note_layout.setContentsMargins(10, 10, 10, 10)

        note_title = QLabel(note_title)
        note_title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        note_title.setFixedHeight(20)
        note_layout.addWidget(note_title)

        note_label = QLabel(note_text)
        note_label.setWordWrap(True)
        note_label.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 14px;
        """)
        note_label.setFixedHeight(60)
        edit_button = QPushButton("Edit")
        edit_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
        """)

        def edit_note():
            # Title editor
            self.title_input = QLineEdit(note_card)
            self.title_input.setText(note_title.text())
            self.title_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {THEME['surface']};
                    color: {THEME['text_primary']};
                    border: 1px solid {THEME['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 14px;
                }}
            """)

            # Body editor
            self.body_input = QLineEdit(note_card)
            self.body_input.setText(note_label.text())
            self.body_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {THEME['surface']};
                    color: {THEME['text_primary']};
                    border: 1px solid {THEME['border']};
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 14px;
                }}
            """)

            # Replace widgets
            note_layout.replaceWidget(note_title, self.title_input)
            note_layout.replaceWidget(note_label, self.body_input)

            note_title.hide()
            note_label.hide()

            # Save on Enter 
            self.body_input.returnPressed.connect(save_note)
            self.title_input.setFocus()


        def save_note():
            new_title = self.title_input.text().strip()
            new_body = self.body_input.text().strip()

            # Update UI
            note_title.setText(new_title)
            note_label.setText(new_body)

            note_layout.replaceWidget(self.title_input, note_title)
            note_layout.replaceWidget(self.body_input, note_label)

            self.title_input.deleteLater()
            self.body_input.deleteLater()

            note_title.show()
            note_label.show()

            # Save note to file
            path = self.case_path
            save_path = os.path.join(path, "notes")
            os.makedirs(save_path, exist_ok=True)

            safe_title = "".join(c for c in new_title if c.isalnum() or c in (" ", "_", "-"))
            file_path = os.path.join(save_path, f"{safe_title}.txt")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_body)


        edit_button.clicked.connect(edit_note)

        note_layout.addWidget(note_label)

        note_layout.addWidget(edit_button, alignment=Qt.AlignRight)

        note_card.setLayout(note_layout)
        return note_card



# Main correlation window
class OverviewDashBoard(QMainWindow):
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
        
        # Load chart when file selected
        data_sources.fileSelected.connect(data_overview.load_packet_chart)

        # Add stretch to push everything to the left
        top_boxes_layout.addStretch()
        
        # Add the horizontal layout to the main content layout
        content_layout.addLayout(top_boxes_layout)
        
        # Create horizontal layout for SourceOverview and InvestigatorNotes
        bottom_boxes_layout = QHBoxLayout()
        bottom_boxes_layout.setSpacing(15)
        
        # Get list of evidence files in the case directory
        file_list = []
        for root, dirs, files in os.walk(f"{self.path}/evidence"):
            for file in files:
                file_list.append(os.path.join(root, file))

        # Data source overview (left)
        source_overview = SourceOverview(file_list)
        bottom_boxes_layout.addWidget(source_overview, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Investigator notes (right)
        investigator_notes = InvestigatorNotes(self.path)
        bottom_boxes_layout.addWidget(investigator_notes, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        
        # Add sources button functionality to add new source to evidence folder
        def add_source():
            
            options = QFileDialog.Options()
            options |= QFileDialog.ReadOnly
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Data Source File",
                "",
                "All Files (*);;PCAP Files (*.pcap *.pcapng);;Log Files (*.log *.txt)",
                options=options
            )

            if file_path:

                evidence_dir = os.path.join(self.path, "evidence")

                dest_file = os.path.join(evidence_dir, os.path.basename(file_path))

                try:
                    shutil.copy(file_path, dest_file)
                    print(f"Copied {file_path} to {dest_file}")

                    # Refresh the source overview table
                    source_overview.file_table.insertRow(source_overview.file_table.rowCount())
                    row = source_overview.file_table.rowCount() - 1

                    file_name = os.path.basename(dest_file)
                    file_size_mb = round(getsize(dest_file) / (1024 * 1024), 2)
                    timestamp = time.ctime(getsize(dest_file))  

                    if ".pcap" in file_name:
                        source_type = "network"

                    source_overview.file_table.setItem(row, 0, QTableWidgetItem(file_name))
                    source_overview.file_table.setItem(row, 1, QTableWidgetItem(source_type))  
                    source_overview.file_table.setItem(row, 2, QTableWidgetItem(timestamp))
                    source_overview.file_table.setItem(row, 3, QTableWidgetItem(str(file_size_mb)))
                    source_overview.file_table.setItem(row, 4, QTableWidgetItem("Loaded"))  
                except Exception as e:
                    print(f"Error copying file: {e}")
        
        # When add source button clicked
        button_layout.add_source_clicked(add_source)

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
    window = OverviewDashBoard(path=r"path_to_case_folder")
    window.show()
    sys.exit(app.exec())