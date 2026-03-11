import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt
import sys

from sharedWidgets import TopNavBar
from correlationSelection import CorrelationSelectionTable
from themes import THEME
from incognitoWidget import IncognitoGapWidget
from correlationEngine import CorrelationEngine, GapDetector
from timelineCorrelation import CrossPCAPTimelineWidget
from browserLogParser import BrowserLogParser
from database import init_db, create_case, get_packets, save_packets, save_run


class CorrelationDashboard(QMainWindow):
    def __init__(self, path: str):
        super().__init__()

        self.path = path

        # Init DB and register/retrieve this case
        init_db()
        self.case_id = create_case(os.path.basename(path), path)
        self.current_run_id = None

        self.setWindowTitle("AutoCorrel8 – Incognito Analysis")
        self.setGeometry(100, 100, 1920, 1080)
        self.showMaximized()

        # Internal caches to avoid re-parsing data during iterative analysis
        self._packet_cache = {}
        self._last_timeline_data = None
        self._cached_browser_events = None
        self._cached_gaps = None

        # Main layout
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Nav bar
        nav = TopNavBar()
        nav.setFixedHeight(50)
        root.addWidget(nav)

        # Content area
        content = QWidget()
        content.setStyleSheet(f"background-color: {THEME['background']};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top section with left panel and incognito widget
        top_section = QHBoxLayout()
        top_section.setSpacing(0)
        top_section.setContentsMargins(0, 0, 0, 0)

        # Left panel: tab buttons, correlation selection, run button
        self.left_panel = QWidget()
        self.left_panel.setMaximumWidth(480)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # Correlation engine
        self.correlation_engine = CorrelationEngine()

        # Selection table
        self.correlation_selection_table = CorrelationSelectionTable(self.path)
        left_layout.addWidget(self.correlation_selection_table)

        # Attempt correlation button
        self.run_button = QPushButton("🔍  Attempt Correlation")
        self.run_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {THEME['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {THEME['button_checked']};
            }}
        """)
        self.run_button.clicked.connect(self.attempt_correlation)
        left_layout.addWidget(self.run_button)

        top_section.addWidget(self.left_panel)

        # Incognito gaps widget
        self.incognito_widget = IncognitoGapWidget()
        self.incognito_widget.setMinimumWidth(550)
        self.incognito_widget.set_case_id(self.case_id)
        self.incognito_widget.eventSelected.connect(self._on_incognito_event_selected)
        top_section.addWidget(self.incognito_widget, 1)

        content_layout.addLayout(top_section)

        # Toggle timeline button
        toggle_bar = QWidget()
        toggle_bar.setFixedHeight(36)
        toggle_bar.setStyleSheet(f"background-color: {THEME['surface']}; border-top: 1px solid {THEME['border']};")
        toggle_layout = QHBoxLayout(toggle_bar)
        toggle_layout.setContentsMargins(12, 4, 12, 4)

        tl_label = QLabel("Timeline")
        tl_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px; font-weight: bold;")
        toggle_layout.addWidget(tl_label)
        toggle_layout.addStretch()

        self._timeline_toggle_btn = QPushButton("▼  Hide")
        self._timeline_toggle_btn.setFixedSize(90, 26)
        self._timeline_toggle_btn.setCursor(Qt.PointingHandCursor)
        self._timeline_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['button_bg']};
                color: {THEME['text_primary']};
                border: 1px solid {THEME['border']};
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {THEME['surface_elevated']};
                border-color: {THEME['accent']};
            }}
        """)
        self._timeline_toggle_btn.clicked.connect(self._toggle_timeline)
        toggle_layout.addWidget(self._timeline_toggle_btn)
        content_layout.addWidget(toggle_bar)

        self.timeline_widget = CrossPCAPTimelineWidget()
        self.timeline_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border-top: 1px solid {THEME['border']};
            }}
        """)
        self.timeline_widget.setMinimumHeight(380)
        content_layout.addWidget(self.timeline_widget, 1)

        root.addWidget(content)

    def _toggle_timeline(self):
        # Hiding the timeline also collapses the selection panel so the gap
        # table expands to full width; tab buttons stay visible via left_panel header
        if self.timeline_widget.isVisible():
            self.timeline_widget.hide()
            self.left_panel.hide()
            self._timeline_toggle_btn.setText("▲  Show")
        else:
            self.timeline_widget.show()
            self.left_panel.show()
            self._timeline_toggle_btn.setText("▼  Hide")

    def _on_incognito_event_selected(self, gap: dict):
        # Focus the timeline on the selected gap's time window
        self.timeline_widget.focus_on_gap(gap)

    def attempt_correlation(self):
        # Run gap detection and populate both the table and timeline lanes

        # Clear stale caches
        self._cached_browser_events = None
        self._cached_gaps = None

        # Update checkbox states
        self.correlation_selection_table.update_selection_states()
        selected_fields = self.correlation_selection_table.get_selected_fields_by_file()
        print("Selected fields by file:", selected_fields)

        # Load packet data
        packets_by_file = self._get_packets_for_files(selected_fields.keys())

        # Build timeline events via correlation engine
        timeline_data = self.correlation_engine.prepare_timeline_data(
            packets_by_file, selected_fields
        )
        self._last_timeline_data = timeline_data

        # Load PCAP lanes into timeline
        self.timeline_widget.load_timeline_data(timeline_data)

        # Extract domain events for gap detection
        pcap_domain_events = [
            e for events in timeline_data.values()
            for e in events if e.event_type == 'domain'
        ]

        # Parse browser history
        browser_events = self._get_browser_history()

        if not browser_events:
            print("No browser history found — upload a History.db file to the evidence folder.")
            return

        # Find gaps between pcap domains and browser history
        detector = GapDetector(time_window_seconds=60)
        grouped_gaps = detector.find_gaps_grouped(pcap_domain_events, browser_events)

        if not grouped_gaps:
            print("No incognito gaps detected — all traffic matches browser history.")
            return

        self._cached_gaps = grouped_gaps

        # Save run and gaps to DB
        pcap_files = list(selected_fields.keys())
        self.current_run_id = save_run(self.case_id, pcap_files, grouped_gaps)

        # Populate incognito table — bookmarks restore automatically via case_id
        self.incognito_widget.load_gaps(grouped_gaps)

        # Add incognito gap lane underneath the PCAP lanes
        self.timeline_widget.load_incognito_gaps(
            grouped_gaps,
            gap_table_ref=self.incognito_widget
        )

        # Make timeline visible if hidden
        if not self.timeline_widget.isVisible():
            self._toggle_timeline()

    def _get_packets_for_files(self, filenames) -> dict:
        packets_by_file = {}
        for fn in filenames:
            # 1. Session memory cache
            if fn in self._packet_cache:
                packets_by_file[fn] = self._packet_cache[fn]
                continue

            # 2. Database
            data = get_packets(self.case_id, fn)

            # 3. Fallback - read old JSON file and migrate it into the DB
            if not data:
                import json
                json_path = os.path.join("packetFiles", f"{fn}_packets.json")
                if os.path.exists(json_path):
                    with open(json_path, "r") as f:
                        data = json.load(f)
                    print(f"Migrating {fn} from JSON into database...")
                    save_packets(self.case_id, fn, data)

            if data:
                self._packet_cache[fn] = data
                packets_by_file[fn] = data
            else:
                print(f"Warning: no packet data found for {fn}")

        return packets_by_file

    def _get_browser_history(self):
        if self._cached_browser_events is not None:
            return self._cached_browser_events

        evidence_dir = os.path.join(self.path, "evidence")
        browser_events = []

        for filename in os.listdir(evidence_dir):
            if filename.endswith(('.sqlite', '.db')) and 'history' in filename.lower():
                history_path = os.path.join(evidence_dir, filename)
                print(f"Parsing browser history: {filename}")
                parser = BrowserLogParser()
                events = parser.parse_browser_history('chrome', history_path)
                browser_events.extend(events)
                print(f"  → {len(events)} entries from {filename}")

        self._cached_browser_events = browser_events
        return browser_events


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CorrelationDashboard(
        path=r"C:\Users\jjc19\OneDrive\Documents\Cases\Case_13"
    )
    window.show()
    sys.exit(app.exec())