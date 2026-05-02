# Import necessary PyQt5 modules
from ast import Load
from ast import Load
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QFileSystemModel, QTreeView, QTableWidget, QTableWidgetItem, QScrollArea, QLineEdit, QFileDialog, QTextEdit
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
import hashlib
from collections import Counter
from themes import THEME
from correlationDash import CorrelationDashboard
import copy
from sharedWidgets import DataSources, ButtonLayout, TopNavBar
from hashing import sha256_file


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
                timestamp = time.ctime(os.path.getmtime(file_path))

                # Determine source type based on file extension
                if ".pcap" in file_name or ".pcapng" in file_name:
                    source_type = "network"
                elif ".db" in file_name or ".sqlite" in file_name:
                    if "history" in file_name.lower():
                        source_type = "browser"
                    else:
                        source_type = "database"
                elif ".evtx" in file_name:
                    source_type = "windows_event"
                elif ".log" in file_name:
                    source_type = "log"
                else:
                    source_type = "unknown"

                # Compute SHA-256 hash for evidence integrity 
                file_hash = sha256_file(file_path)

                self.file_table.setItem(row, 0, QTableWidgetItem(file_name))
                self.file_table.setItem(row, 1, QTableWidgetItem(source_type))  
                self.file_table.setItem(row, 2, QTableWidgetItem(timestamp))
                self.file_table.setItem(row, 3, QTableWidgetItem(str(file_size_mb)))
                self.file_table.setItem(row, 5, QTableWidgetItem(file_hash))
                
                if ".pcap" in file_name or ".pcapng" in file_name:
                    status = "Loading..."  
                else:
                    status = "Loaded"     

                self.file_table.setItem(row, 4, QTableWidgetItem(status))

        self.setLayout(layout)

    def create_table(self):
        # Table of uploaded file paths
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(6)
        self.file_table.setHorizontalHeaderLabels(["File Path", "Source Type", "Time stamp", "File Size (MB)", "Status", "SHA-256"])
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.setColumnWidth(0, 200)  
        self.file_table.setColumnWidth(1, 100)
        self.file_table.setColumnWidth(2, 150)
        self.file_table.setColumnWidth(3, 100)  
        self.file_table.setColumnWidth(4, 80)
        self.file_table.setColumnWidth(5, 150)
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
        self.tshark_path = self._find_tshark()

    def _find_tshark(self):
        
        # Check PATH first 
        import shutil
        tshark = shutil.which("tshark")
        if tshark:
            return tshark
        
        # Common Windows install locations
        common_paths = [
            r"C:\Program Files\Wireshark\tshark.exe",
            r"C:\Program Files (x86)\Wireshark\tshark.exe",
            r"D:\Wireshark\tshark.exe",
            r"D:\Program Files\Wireshark\tshark.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        raise FileNotFoundError(
            "tshark.exe not found. Please install Wireshark or add it to your system PATH."
        )
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
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(10)

        # Store packets organized by file
        self.packets_by_file = {}
        self.current_file_path = None
        self.loading_files = set()  # Track which files are currently loading

        # Header row: title + live loading status
        header_row = QHBoxLayout()
        self.title = QLabel("Case Overview")
        self.title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        header_row.addWidget(self.title)
        header_row.addStretch()

        self.status_label = QLabel("Waiting for evidence files...")
        self.status_label.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 12px;
            font-style: italic;
        """)
        header_row.addWidget(self.status_label)
        self.main_layout.addLayout(header_row)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Stat cards rows
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)

        self.stat_total_packets  = self._build_stat_card("0",     "Total Packets",  "#5b9bd5")
        self.stat_unique_domains = self._build_stat_card("0",     "Unique Domains", "#27ae60")
        self.stat_unique_ips     = self._build_stat_card("0",     "Unique IPs",     "#e6a817")
        self.stat_capture_range  = self._build_stat_card("—",     "Capture Range",  "#8e44ad")
        self.stat_files_loaded   = self._build_stat_card("0 / 0", "Files Loaded",   "#7f8c8d")

        for card in [
            self.stat_total_packets,
            self.stat_unique_domains,
            self.stat_unique_ips,
            self.stat_capture_range,
            self.stat_files_loaded,
        ]:
            stats_row.addWidget(card)

        self.main_layout.addLayout(stats_row)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(
            f"border: none; background-color: {THEME['border']}; max-height: 1px;"
        )
        self.main_layout.addWidget(divider)

        # Top domains section title
        domains_header = QLabel("Top Contacted Domains")
        domains_header.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 13px;
            font-weight: bold;
        """)
        self.main_layout.addWidget(domains_header)

        # Domains table 
        self.domains_table = QTableWidget()
        self.domains_table.setColumnCount(4)
        self.domains_table.setHorizontalHeaderLabels(["#", "Domain", "Hits", "Protocol"])
        self.domains_table.verticalHeader().setVisible(False)
        self.domains_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.domains_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.domains_table.horizontalHeader().setStretchLastSection(True)
        self.domains_table.setColumnWidth(0, 35)
        self.domains_table.setColumnWidth(1, 350)
        self.domains_table.setColumnWidth(2, 60)
        self.domains_table.setColumnWidth(3, 80)
        self.domains_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                color: {THEME['text_primary']};
                border: none;
                gridline-color: {THEME['border']};
                font-size: 12px;
            }}
            QTableWidget::item {{
                padding: 3px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background-color: {THEME['button_checked']};
                color: {THEME['accent']};
            }}
            QHeaderView::section {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_secondary']};
                padding: 4px 8px;
                border: none;
                border-bottom: 1px solid {THEME['border']};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        self.main_layout.addWidget(self.domains_table)

        self.setLayout(self.main_layout)

        # Store the loader threads
        self.loader_threads = []

        # Store the upload threads
        self.upload_threads = []

    def _build_stat_card(self, value, label, colour):
        # Build a single stat card with a coloured left accent stripe
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border-left: 3px solid {colour};
                border-top: none;
                border-right: none;
                border-bottom: none;
                border-radius: 0px;
            }}
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(2)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {colour};
                font-size: 22px;
                font-weight: bold;
                border: none;
            }}
        """)

        desc_label = QLabel(label)
        desc_label.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_secondary']};
                font-size: 11px;
                border: none;
            }}
        """)

        card_layout.addWidget(value_label)
        card_layout.addWidget(desc_label)
        card.setLayout(card_layout)

        # Attach the value label so refresh_display can update it directly
        card._value_label = value_label
        return card

    def _update_stat_card(self, card, value):
        # Update the displayed value on a stat card
        card._value_label.setText(str(value))

    def _compute_stats(self):
        # Compute aggregate case statistics across all loaded packet files
        total_packets = 0
        unique_domains = set()
        unique_ips = set()
        timestamps = []

        for packets in self.packets_by_file.values():
            total_packets += len(packets)
            for pkt in packets:
                # Collect source and destination IPs
                if pkt.get("src_ip"):
                    unique_ips.add(pkt["src_ip"])
                if pkt.get("dst_ip"):
                    unique_ips.add(pkt["dst_ip"])
                # Collect domains from DNS, TLS SNI, and HTTP Host layers
                layers = pkt.get("layers", {})
                if "dns" in layers and layers["dns"].get("query"):
                    unique_domains.add(layers["dns"]["query"].lower().rstrip("."))
                if "tls" in layers and layers["tls"].get("server_name"):
                    unique_domains.add(layers["tls"]["server_name"].lower())
                if "http" in layers and layers["http"].get("host"):
                    unique_domains.add(layers["http"]["host"].lower())
                # Collect packet timestamps for capture range calculation
                ts = pkt.get("timestamp")
                if ts:
                    try:
                        timestamps.append(float(ts))
                    except (ValueError, TypeError):
                        pass

        # Format capture time range from earliest to latest packet
        if timestamps:
            earliest = time.strftime("%H:%M:%S", time.localtime(min(timestamps)))
            latest   = time.strftime("%H:%M:%S", time.localtime(max(timestamps)))
            capture_range = f"{earliest} – {latest}"
        else:
            capture_range = "—"

        return total_packets, len(unique_domains), len(unique_ips), capture_range

    def _get_top_domains(self, n=10):
        # Return top N domains by hit count across all loaded packet files
        domain_counts  = Counter()
        domain_protocol = {}  

        for packets in self.packets_by_file.values():
            for pkt in packets:
                layers = pkt.get("layers", {})
                if "dns" in layers and layers["dns"].get("query"):
                    domain = layers["dns"]["query"].lower().rstrip(".")
                    domain_counts[domain] += 1
                    domain_protocol.setdefault(domain, "DNS")
                if "tls" in layers and layers["tls"].get("server_name"):
                    domain = layers["tls"]["server_name"].lower()
                    domain_counts[domain] += 1
                    domain_protocol.setdefault(domain, "TLS")
                if "http" in layers and layers["http"].get("host"):
                    domain = layers["http"]["host"].lower()
                    domain_counts[domain] += 1
                    domain_protocol.setdefault(domain, "HTTP")

        return [
            (domain, count, domain_protocol.get(domain, "—"))
            for domain, count in domain_counts.most_common(n)
        ]

    def refresh_display(self):
        # Recompute and refresh all stat cards and the top domains table
        total_packets, unique_domains, unique_ips, capture_range = self._compute_stats()
        total_files  = len(self.packets_by_file) + len(self.loading_files)
        loaded_files = len(self.packets_by_file)

        self._update_stat_card(self.stat_total_packets,  f"{total_packets:,}")
        self._update_stat_card(self.stat_unique_domains, f"{unique_domains:,}")
        self._update_stat_card(self.stat_unique_ips,     f"{unique_ips:,}")
        self._update_stat_card(self.stat_capture_range,  capture_range)
        self._update_stat_card(self.stat_files_loaded,   f"{loaded_files} / {total_files}")

        # Update the inline status message
        if self.loading_files:
            self.status_label.setText(f"Loading: {', '.join(self.loading_files)}")
        elif total_files > 0:
            self.status_label.setText("All files loaded")
        else:
            self.status_label.setText("No evidence files found")

        # Refresh the top domains table
        top_domains = self._get_top_domains(10)
        self.domains_table.setRowCount(len(top_domains))

        protocol_colours = {
            "DNS":  "#5b9bd5",
            "TLS":  "#27ae60",
            "HTTP": "#e6a817",
        }

        from PyQt5.QtGui import QColor
        for row, (domain, count, protocol) in enumerate(top_domains):
            rank_item   = QTableWidgetItem(str(row + 1))
            domain_item = QTableWidgetItem(domain)
            count_item  = QTableWidgetItem(str(count))
            proto_item  = QTableWidgetItem(protocol)

            rank_item.setTextAlignment(Qt.AlignCenter)
            count_item.setTextAlignment(Qt.AlignCenter)
            proto_item.setTextAlignment(Qt.AlignCenter)

            # Colour the protocol cell text to match the stat card colours
            proto_item.setForeground(QColor(protocol_colours.get(protocol, THEME['text_secondary'])))

            self.domains_table.setItem(row, 0, rank_item)
            self.domains_table.setItem(row, 1, domain_item)
            self.domains_table.setItem(row, 2, count_item)
            self.domains_table.setItem(row, 3, proto_item)

    def display_chart_for_file(self, file_path):
        # Called when a file is selected in DataSources
        self.current_file_path = file_path
        self.refresh_display()

    def preload_all_pcap_files(self, file_list):
        
        # Start loading all PCAP files in the background
        print(f"Starting preload of {len(file_list)} files")

        pcap_count = sum(
            1 for f in file_list if f.endswith('.pcap') or f.endswith('.pcapng')
        )
        self._update_stat_card(self.stat_files_loaded, f"0 / {pcap_count}")
        if pcap_count:
            self.status_label.setText(f"Loading {pcap_count} file(s)...")
        
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
                        self.fileLoadCompleted.emit(file_name) 
                        print(f"Loaded {len(packets)} packets from cache for {file_name}")
                    except Exception as e:
                        print(f"Error loading cached packets for {file_name}: {e}")
                        # If cache fails, load normally
                        self.start_loading_file(file_path, file_name)
                else:
                    # Need to parse with tshark
                    self.start_loading_file(file_path, file_name)

        # Refresh display after any cache loads have completed synchronously
        self.refresh_display()
    
    def start_loading_file(self, file_path, file_name):
        
        # Start loading a single file in background
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
        
        # Remove from loading set
        self.loading_files.discard(file_name)
        
        # Store packets
        self.packets_by_file[file_name] = packets


        self.loader_threads = [t for t in self.loader_threads if t.isRunning()]
        
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
        
        # Refresh stats and domains table now this file's data is available
        self.refresh_display()
    
    def on_file_error(self, error_message, file_name):
        """Called when a file fails to load"""
        print(f"Error loading file {file_name}: {error_message}")
        self.loading_files.discard(file_name)
        self.fileLoadFailed.emit(file_name)
        self.status_label.setText(f"Error loading {file_name}: {error_message}")
        self.refresh_display()

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

    # Helper functions for getting stored packets
    def get_packets_for_file(self, file_name):
        
        # Get all packets from a specific file
        return self.packets_by_file.get(file_name, [])
    
class InvestigatorNotes(QFrame):
 
    TAGS = {
        "Observation":        ("#5b9bd5", "#1a2535"),
        "Suspicious":         ("#e6a817", "#2a2010"),
        "Confirmed Finding":  ("#c0392b", "#2a1010"),
        "Note":               ("#7f8c8d", "#1e2022"),
    }

    def __init__(self, case_path):
        super().__init__()
        self.case_path = case_path
        self.setFixedHeight(450)
        self.setFixedWidth(1075)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header row: title + add button
        header_row = QHBoxLayout()
        title = QLabel("Key Findings")
        title.setStyleSheet(f"""
            color: {THEME['text_primary']};
            font-size: 16px;
            font-weight: bold;
        """)
        header_row.addWidget(title)
        header_row.addStretch()

        self.add_note_button = QPushButton("+ Add Finding")
        self.add_note_button.setCursor(Qt.PointingHandCursor)
        self.add_note_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                border: 1px solid {THEME['accent']};
                color: {THEME['accent']};
            }}
        """)
        header_row.addWidget(self.add_note_button)
        main_layout.addLayout(header_row)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface_elevated']};
                border: 1px solid {THEME['border']};
                border-radius: 6px;
            }}
        """)

        # Scrollable findings area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none; background: transparent;")

        self.notes_container = QWidget()
        self.notes_container.setStyleSheet("background: transparent;")
        self.notes_layout = QVBoxLayout()
        self.notes_layout.setSpacing(8)
        self.notes_layout.addStretch()

        self.notes_container.setLayout(self.notes_layout)
        self.scroll_area.setWidget(self.notes_container)
        main_layout.addWidget(self.scroll_area)

        self.add_note_button.clicked.connect(self.add_note_card)

        # Load existing findings from JSON files
        self.load_notes()

        self.setLayout(main_layout)

    def add_note_card(self):
        card = self.create_note_card(
            title_text="New Finding",
            note_text="Describe the finding here.",
            tag="Observation",
            timestamp=time.strftime("%Y-%m-%d %H:%M"),
            start_editing=True
        )
        # Insert before the trailing stretch
        self.notes_layout.insertWidget(self.notes_layout.count() - 1, card)

    # Load existing findings from JSON files in the notes directory
    def load_notes(self):
        notes_path = os.path.join(self.case_path, "notes")
        if not os.path.exists(notes_path):
            return

        for file_name in sorted(os.listdir(notes_path)):
            if file_name.endswith(".json"):
                file_path = os.path.join(notes_path, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    card = self.create_note_card(
                        title_text=data.get("title", "Finding"),
                        note_text=data.get("body", ""),
                        tag=data.get("tag", "Note"),
                        timestamp=data.get("timestamp", ""),
                        start_editing=False
                    )
                    self.notes_layout.insertWidget(self.notes_layout.count() - 1, card)
                except Exception as e:
                    print(f"Error loading finding {file_name}: {e}")

    # Save a finding to a JSON file in the notes directory
    def save_finding(self, title_text, note_text, tag, timestamp):
        notes_path = os.path.join(self.case_path, "notes")
        os.makedirs(notes_path, exist_ok=True)
        safe_title = "".join(c for c in title_text if c.isalnum() or c in (" ", "_", "-"))
        file_path = os.path.join(notes_path, f"{safe_title}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": title_text,
                "body": note_text,
                "tag": tag,
                "timestamp": timestamp
            }, f, indent=4)

    # Delete a finding's JSON file from disk
    def delete_finding(self, title_text):
        notes_path = os.path.join(self.case_path, "notes")
        safe_title = "".join(c for c in title_text if c.isalnum() or c in (" ", "_", "-"))
        file_path = os.path.join(notes_path, f"{safe_title}.json")
        if os.path.exists(file_path):
            os.remove(file_path)

    # Create finding cards
    def create_note_card(self, title_text, note_text, tag="Note", timestamp="", start_editing=False):
        tag_colour, tag_bg = self.TAGS.get(tag, ("#7f8c8d", "#1e2022"))

        # Outer card
        note_card = QFrame()
        note_card.setStyleSheet(f"""
            QFrame#findingCard {{
                background-color: {tag_bg};
                border-left: 3px solid {tag_colour};
                border-top: none;
                border-right: none;
                border-bottom: none;
                border-radius: 0px;
                padding-left: 4px;
            }}
        """)
        note_card.setObjectName("findingCard")

        note_layout = QVBoxLayout()
        note_layout.setContentsMargins(12, 10, 12, 10)
        note_layout.setSpacing(4)

        # Top row: tag badge + timestamp
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        tag_badge = QLabel(tag)
        tag_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {tag_colour};
                color: #ffffff;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: bold;
                border: none;
            }}
        """)
        tag_badge.setFixedHeight(18)

        timestamp_label = QLabel(timestamp)
        timestamp_label.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_secondary']};
                font-size: 11px;
                border: none;
            }}
        """)

        top_row.addWidget(tag_badge)
        top_row.addWidget(timestamp_label)
        top_row.addStretch()
        note_layout.addLayout(top_row)

        # Title label
        note_title = QLabel(title_text)
        note_title.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_primary']};
                font-size: 13px;
                font-weight: bold;
                border: none;
                padding: 0px;
            }}
        """)
        note_layout.addWidget(note_title)

        # Body label 
        note_label = QLabel(note_text)
        note_label.setWordWrap(True)
        note_label.setStyleSheet(f"""
            QLabel {{
                color: {THEME['text_secondary']};
                font-size: 12px;
                border: none;
                padding: 0px;
            }}
        """)
        note_layout.addWidget(note_label)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(6)

        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: none;
                padding: 2px 6px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                color: {THEME['text_primary']};
            }}
        """

        edit_button = QPushButton("Edit")
        edit_button.setCursor(Qt.PointingHandCursor)
        edit_button.setStyleSheet(btn_style)

        delete_button = QPushButton("Delete")
        delete_button.setCursor(Qt.PointingHandCursor)
        delete_button.setStyleSheet(btn_style + f"""
            QPushButton:hover {{ color: #ff6b6b; }}
        """)

        button_row.addStretch()
        button_row.addWidget(edit_button)
        button_row.addWidget(delete_button)
        note_layout.addLayout(button_row)

        note_card.setLayout(note_layout)

        def delete_note():
            # Remove the saved finding file if it exists
            self.delete_finding(note_title.text())
            note_card.deleteLater()

        delete_button.clicked.connect(delete_note)

        def edit_note():
            title_input = QLineEdit()
            title_input.setText(note_title.text())
            title_input.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {THEME['surface']};
                    color: {THEME['text_primary']};
                    border: 1px solid {THEME['border']};
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 13px;
                    font-weight: bold;
                }}
            """)

            body_input = QTextEdit()
            body_input.setPlainText(note_label.text())
            body_input.setFixedHeight(70)
            body_input.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {THEME['surface']};
                    color: {THEME['text_secondary']};
                    border: 1px solid {THEME['border']};
                    border-radius: 3px;
                    padding: 4px 8px;
                    font-size: 12px;
                }}
            """)

            note_layout.replaceWidget(note_title, title_input)
            note_layout.replaceWidget(note_label, body_input)
            note_title.hide()
            note_label.hide()

            # Swap Edit for Save button while editing
            edit_button.hide()
            save_button = QPushButton("Save")
            save_button.setCursor(Qt.PointingHandCursor)
            save_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {THEME['accent']};
                    border: none;
                    padding: 2px 6px;
                    font-size: 11px;
                    font-weight: bold;
                }}
            """)
            button_row.insertWidget(1, save_button)

            def save_note():
                new_title = title_input.text().strip()
                new_body = body_input.toPlainText().strip()
                current_tag = tag_badge.text()
                current_ts = timestamp_label.text()

                # Remove old file if title changed
                if new_title != note_title.text():
                    self.delete_finding(note_title.text())

                # Update display labels
                note_title.setText(new_title)
                note_label.setText(new_body)

                note_layout.replaceWidget(title_input, note_title)
                note_layout.replaceWidget(body_input, note_label)
                title_input.deleteLater()
                body_input.deleteLater()
                note_title.show()
                note_label.show()

                # Restore Edit button, remove Save button
                save_button.deleteLater()
                edit_button.show()

                # Persist finding to disk
                self.save_finding(new_title, new_body, current_tag, current_ts)

            save_button.clicked.connect(save_note)
            title_input.returnPressed.connect(save_note)
            title_input.setFocus()

        edit_button.clicked.connect(edit_note)

        # If this is a brand-new card, drop straight into edit mode
        if start_editing:
            edit_note()

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
        self.showMaximized()

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

        self.correlation_dashboard = None

        def show_correlation_dashboard():
            if self.correlation_dashboard is None or not self.correlation_dashboard.isVisible():
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
        
        # Create horizontal layout for SourceOverview and InvestigatorNotes
        bottom_boxes_layout = QHBoxLayout()
        bottom_boxes_layout.setSpacing(15)

        # Data overview box 
        data_overview = DataOverview()
        top_boxes_layout.addWidget(data_overview, alignment=Qt.AlignTop | Qt.AlignLeft)
        
        # Load chart when file selected
        data_sources.fileSelected.connect(data_overview.display_chart_for_file)

        # Get list of evidence files in the case directory
        file_list = []
        for root, dirs, files in os.walk(f"{self.path}/evidence"):
            for file in files:
                file_list.append(os.path.join(root, file))

        # Data source overview (left)
        source_overview = SourceOverview(file_list)
        bottom_boxes_layout.addWidget(source_overview, alignment=Qt.AlignTop | Qt.AlignLeft)

        # Update file status in DataSources when loading completes
        data_overview.fileLoadCompleted.connect(
            lambda file_name: source_overview.update_file_status(file_name, "Loaded")
        )

        data_overview.fileLoadStarted.connect(
            lambda file_name: source_overview.update_file_status(file_name, "Loading...")
        )
        data_overview.fileLoadFailed.connect(
            lambda file_name: source_overview.update_file_status(file_name, "Failed")
        )

        # Add stretch to push everything to the left
        top_boxes_layout.addStretch()
        
        # Add the horizontal layout to the main content layout
        content_layout.addLayout(top_boxes_layout)
    
        # Preload Pcap files
        data_overview.preload_all_pcap_files(file_list)


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
                    timestamp = time.ctime(os.path.getmtime(dest_file))

                    if ".pcap" in file_name or ".pcapng" in file_name:
                        source_type = "network"
                    elif ".db" in file_name or ".sqlite" in file_name:
                        if "history" in file_name.lower():
                            source_type = "browser"
                        else:
                            source_type = "database"
                    elif ".evtx" in file_name:
                        source_type = "windows_event"
                    elif ".log" in file_name:
                        source_type = "log"
                    else:
                        source_type = "unknown"

                    # Compute SHA-256 hash for evidence integrity 
                    file_hash = sha256_file(dest_file)

                    source_overview.file_table.setItem(row, 0, QTableWidgetItem(file_name))
                    source_overview.file_table.setItem(row, 1, QTableWidgetItem(source_type))  
                    source_overview.file_table.setItem(row, 2, QTableWidgetItem(timestamp))
                    source_overview.file_table.setItem(row, 3, QTableWidgetItem(str(file_size_mb)))
                    source_overview.file_table.setItem(row, 4, QTableWidgetItem("Loaded"))
                    source_overview.file_table.setItem(row, 5, QTableWidgetItem(file_hash))
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