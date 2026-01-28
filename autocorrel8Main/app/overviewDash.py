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
from mongoDBConnection import DatabaseHelper, DatabaseUploadThread
from correlationDash import CorrelationDashboard
import copy
from sharedWidgets import DataSources, ButtonLayout, TopNavBar

# Dark mode by default
CURRENT_THEME = 'dark'
THEME = DARK_THEME if CURRENT_THEME == 'dark' else LIGHT_THEME


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
                self.file_table.setItem(row, 4, QTableWidgetItem("Loading..."))  

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
    
    def update_file_status(self, file_name, status):
        
        # Update the status column for a specific file
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 0)
            if item and item.text() == file_name:
                self.file_table.setItem(row, 4, QTableWidgetItem(status))
                break


class PacketLoaderThread(QThread):
    
    # Background thread for loading packets
    finished = pyqtSignal(list, str)  # packets, file_name
    error = pyqtSignal(str, str)  # error_message, file_name
    progress = pyqtSignal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.tshark_path = "D:\\Wireshark\\tshark.exe"
    
    def run(self):
        try:
            file_name = os.path.basename(self.file_path)
            print(f"Starting to parse packets from: {self.file_path}")
            self.progress.emit(f"Parsing {file_name}...")
            
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
                "-Y", "dns.qry.name || http.host || tls.handshake.extensions_server_name"
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
            self.progress.emit(f"Processing {file_name}...")
            
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
                        self.progress.emit(f"Processed {idx + 1} packets from {file_name}...")
                        
                except Exception as e:
                    print(f"Error converting packet {idx}: {e}")
                    continue
            
            # Tag packets with metadata before sending to UI thread
            for pkt in packets:
                pkt["source_file"] = file_name


            print(f"Finished parsing {len(packets)} packets from {file_name}")
            self.finished.emit(packets, file_name)
            
        except subprocess.TimeoutExpired:
            print("tshark timed out")
            self.error.emit("Packet parsing timed out (file too large)", file_name)
        except Exception as e:
            print(f"Error in thread: {e}")
            import traceback
            traceback.print_exc()
            self.error.emit(str(e), file_name)
    
    def convert_tshark_packet(self, tshark_pkt):
        # Convert tshark JSON packet to our format
        layers = tshark_pkt.get("_source", {}).get("layers", {})

        # Get frame number for unique ID
        frame_number = layers.get("frame.number", [None])[0]

        # Extract core fields
        src_ip = layers.get("ip.src", [None])[0]
        dst_ip = layers.get("ip.dst", [None])[0]
        src_port = layers.get("tcp.srcport", layers.get("udp.srcport", [None]))[0]
        dst_port = layers.get("tcp.dstport", layers.get("udp.dstport", [None]))[0]
        protocol_stack = layers.get("frame.protocols", [None])[0]

        # Generate descriptive packet name
        packet_name = self.generate_packet_name(
            frame_number, src_ip, dst_ip, src_port, dst_port, protocol_stack, layers
        )

        packet = {
            "packet_id": f"pkt_{frame_number}",  # Unique identifier
            "packet_name": packet_name,  # Descriptive name
            "frame_number": frame_number,
            "timestamp": layers.get("frame.time_epoch", [None])[0],
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": protocol_stack,
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

    def generate_packet_name(self, frame_num, src_ip, dst_ip, src_port, dst_port, protocol_stack, layers):
        
        # Generate a human-readable packet name

        # Extract the highest-level protocol
        if protocol_stack:
            protocols = protocol_stack.split(":")
            top_protocol = protocols[-1].upper()
        else:
            top_protocol = "UNKNOWN"

        # Create contextual names based on protocol
        if "dns.qry.name" in layers:
            query = layers.get("dns.qry.name", [None])[0]
            return f"DNS_{frame_num}_{query}"

        elif "http.request.method" in layers:
            method = layers.get("http.request.method", [None])[0]
            host = layers.get("http.host", [None])[0] or "unknown"
            return f"HTTP_{frame_num}_{method}_{host}"

        elif "tls.handshake.extensions_server_name" in layers:
            server_name = layers.get("tls.handshake.extensions_server_name", [None])[0]
            return f"TLS_{frame_num}_{server_name}"

        elif src_ip and dst_ip:
            # For other protocols, use IPs and ports
            port_info = f":{src_port}" if src_port else ""
            return f"{top_protocol}_{frame_num}_{src_ip}{port_info}_to_{dst_ip}"

        else:
            # Fallback
            return f"Packet_{frame_num}_{top_protocol}"


class DataOverview(QFrame):
    
    # Signals for file loading status
    fileLoadStarted = pyqtSignal(str)  
    fileLoadCompleted = pyqtSignal(str)  
    fileLoadFailed = pyqtSignal(str) 
    
    def __init__(self):
        super().__init__()
        self.setFixedHeight(400)
        self.setFixedWidth(1525)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Store packets organized by file
        self.packets_by_file = {}
        self.current_file_path = None
        self.loading_files = set()  # Track which files are currently loading

        # Add title
        self.title = QLabel("Data Overview")
        self.title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        self.layout.addWidget(self.title)
        
        # Loading label 
        self.loading_label = QLabel("Loading packet data...")
        self.loading_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 14px;
            font-style: italic;
        """)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.hide()
        self.layout.addWidget(self.loading_label)
        
        # Error label 
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
        
        
        # Store the loader threads
        self.loader_threads = []

        # Store the upload threads
        self.upload_threads = []

    def display_chart_for_file(self, file_path):
        
        # Display chart for a selected file 
        print(f"display_chart_for_file called with: {file_path}")
        
        # Always remove old chart first
        self.remove_old_chart()
        
        # Check if it's a PCAP file
        if not (file_path.endswith('.pcap') or file_path.endswith('.pcapng')):
            print(f"Not a PCAP file: {file_path}")
            self.show_placeholder()
            return
        
        file_name = os.path.basename(file_path)
        
        # Check if file is currently loading
        if file_name in self.loading_files:
            print(f"File is still loading: {file_name}")
            self.show_loading(f"Loading {file_name}...")
            return
        
        # Check if packets already loaded
        if file_name in self.packets_by_file:
            print(f"Using cached packets for file: {file_name}")
            self.current_file_path = file_path
            self.display_packets(self.packets_by_file[file_name])
        else:
            # Packets haven't loaded yet, show loading
            print(f"Packets not yet loaded for: {file_name}")
            self.show_loading(f"Processing {file_name}...")

    def preload_all_pcap_files(self, file_list):
        
        # Start loading all PCAP files in the background
        print(f"Starting preload of {len(file_list)} files")
        
        for file_path in file_list:
            if file_path.endswith('.pcap') or file_path.endswith('.pcapng'):
                file_name = os.path.basename(file_path)
                
                # Check if already cached in JSON
                packets_file_path = os.path.join("packetFiles", f"{file_name}_packets.json")
                
                if os.path.exists(packets_file_path):
                    # Load from cache
                    print(f"Loading cached packets for: {file_name}")
                    try:
                        with open(packets_file_path, "r", encoding="utf-8") as f:
                            packets = json.load(f)
                        self.packets_by_file[file_name] = packets
                        print(f"Loaded {len(packets)} packets from cache for {file_name}")
                    except Exception as e:
                        print(f"Error loading cached packets for {file_name}: {e}")
                        # If cache fails, load normally
                        self.start_loading_file(file_path, file_name)
                else:
                    # Need to parse with tshark
                    self.start_loading_file(file_path, file_name)
    
    def start_loading_file(self, file_path, file_name):
        
        # Start loading a single file in background"
        print(f"Starting background load for: {file_name}")
        self.loading_files.add(file_name)
        self.fileLoadStarted.emit(file_name)
        
        loader_thread = PacketLoaderThread(file_path)
        loader_thread.finished.connect(self.on_file_loaded)
        loader_thread.error.connect(self.on_file_error)
        
        loader_thread.start()
        
        self.loader_threads.append(loader_thread)

    def on_file_loaded(self, packets, file_name):
        
        # Called when a file finishes loading
        print(f"File loaded: {file_name} with {len(packets)} packets")
        
        # Start background DB upload
        upload_thread = DatabaseUploadThread(packets, file_name) 
        upload_thread.finished.connect(lambda fn: print(f"DB upload complete for {fn}"))
        upload_thread.error.connect(lambda err: print(f"DB upload error: {err}"))
        upload_thread.start() 
        
        self.upload_threads.append(upload_thread) # Prevents garbage collection
        # Remove from loading set
        self.loading_files.discard(file_name)
        
        # Store packets
        self.packets_by_file[file_name] = packets
        
        # Emit completion signal
        self.fileLoadCompleted.emit(file_name)
        
        # Save to cache
        packets_file_path = os.path.join("packetFiles", f"{file_name}_packets.json")
        os.makedirs("packetFiles", exist_ok=True)
        
        # Copy packets for caching
        packets_to_cache = copy.deepcopy(packets)

        # Store packets locally
        try:
            with open(packets_file_path, "w", encoding="utf-8") as f:
                json.dump(packets_to_cache, f, indent=4)
            print(f"Cached packets to: {packets_file_path}")
        except Exception as e:
            print(f"Error caching packets: {e}")
        
        # If this is the currently selected file, update display
        if self.current_file_path and os.path.basename(self.current_file_path) == file_name:
            self.display_packets(packets_to_cache)
    
    def on_file_error(self, error_message, file_name):
        """Called when a file fails to load"""
        print(f"Error loading file {file_name}: {error_message}")
        self.loading_files.discard(file_name)
        self.fileLoadFailed.emit(file_name)
        
        # If this was the currently selected file, show error
        if self.current_file_path and os.path.basename(self.current_file_path) == file_name:
            self.show_error(error_message)

    def display_packets(self, packets):
        """Display the packet chart for loaded packets"""
        print(f"Displaying chart for {len(packets)} packets")
        
        self.loading_label.hide()
        self.placeholder_label.hide()
        self.error_label.hide()
        
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
    
    def show_loading(self, message="Loading packet data..."):
        """Show loading indicator"""
        print(f"Showing loading indicator: {message}")
        self.placeholder_label.hide()
        self.error_label.hide()
        self.loading_label.setText(message)
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

    # Helper functions for getting stored packets
    def get_packets_for_file(self, file_name):
        
        # Get all packets from a specific file
        return self.packets_by_file.get(file_name, [])
    
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
        button_layout = ButtonLayout("Overview", "Correlation", "Add Source")
        content_layout.addWidget(button_layout, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Set button states
        button_layout.case_overview_button.setChecked(True)

        # Switch screens
        def show_correlation_dashboard():
            self.correlation_dashboard = CorrelationDashboard(self.path)
            self.correlation_dashboard.show()

        # If correlation button is pressed switch to the correlation screen
        button_layout.correlation_button.clicked.connect(
            lambda: show_correlation_dashboard()
        )


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
        data_sources.fileSelected.connect(data_overview.display_chart_for_file)

        # Add stretch to push everything to the left
        top_boxes_layout.addStretch()
        
        # Add the horizontal layout to the main content layout
        content_layout.addLayout(top_boxes_layout)
        
        # Create horizontal layout for SourceOverview and InvestigatorNotes
        bottom_boxes_layout = QHBoxLayout()
        bottom_boxes_layout.setSpacing(15)
     
        helperDB = DatabaseHelper()

        helperDB.fetch_from_database()

        # Get list of evidence files in the case directory
        file_list = []
        for root, dirs, files in os.walk(f"{self.path}/evidence"):
            for file in files:
                file_list.append(os.path.join(root, file))

        # Preload Pcap files
        data_overview.preload_all_pcap_files(file_list)

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