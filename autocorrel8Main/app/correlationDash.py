import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel,
    QPushButton, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget, QButtonGroup
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
from registryWidget import RegistryWidget
from registryTimeline import RegistryTimelineWidget


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

        # Top section with left panel and right panel
        top_section = QHBoxLayout()
        top_section.setSpacing(0)
        top_section.setContentsMargins(0, 0, 0, 0)

        # Left panel
        self.left_panel = QWidget()
        self.left_panel.setMaximumWidth(480)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        # Correlation engine
        self.correlation_engine = CorrelationEngine()

        top_section.addWidget(self.left_panel)

        # Right panel
        right_panel = QWidget()
        right_panel.setMinimumWidth(550)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Panel tab bar
        panel_tab_bar = QWidget()
        panel_tab_bar.setFixedHeight(38)
        panel_tab_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {THEME['surface']};
                border-bottom: 1px solid {THEME['border']};
            }}
        """)
        panel_tab_layout = QHBoxLayout(panel_tab_bar)
        panel_tab_layout.setContentsMargins(8, 4, 8, 0)
        panel_tab_layout.setSpacing(2)

        tab_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {THEME['text_secondary']};
                border: none;
                border-bottom: 2px solid transparent;
                padding: 4px 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:checked {{
                color: {THEME['accent']};
                border-bottom: 2px solid {THEME['accent']};
            }}
            QPushButton:hover:!checked {{
                color: {THEME['text_primary']};
            }}
        """

        self._panel_group = QButtonGroup(self)
        self._panel_group.setExclusive(True)

        browser_tab_btn = QPushButton("Browser Activity")
        registry_tab_btn = QPushButton("Registry")

        for i, btn in enumerate((browser_tab_btn, registry_tab_btn)):
            btn.setCheckable(True)
            btn.setStyleSheet(tab_style)
            btn.setCursor(Qt.PointingHandCursor)
            panel_tab_layout.addWidget(btn)
            self._panel_group.addButton(btn, i)

        browser_tab_btn.setChecked(True)
        panel_tab_layout.addStretch()

        # Attempt correlation button, lives in the tab bar, right side
        self.run_button = QPushButton("🔍  Attempt Correlation")
        self.run_button.setFixedHeight(26)
        self.run_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 14px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {THEME['accent_hover']}; }}
            QPushButton:pressed {{ background-color: {THEME['button_checked']}; }}
        """)
        self.run_button.clicked.connect(self.attempt_correlation)

        right_layout.addWidget(panel_tab_bar)

        # Right stacked widget, browser activity and registry
        self._right_stack = QStackedWidget()

        self.incognito_widget = IncognitoGapWidget()
        self.incognito_widget.set_case_id(self.case_id)
        self.incognito_widget.eventSelected.connect(self._on_incognito_event_selected)
        self.incognito_widget.set_action_button(self.run_button)
        self._right_stack.addWidget(self.incognito_widget)  

        self.registry_widget = RegistryWidget()
        self.registry_widget.set_case_id(self.case_id)
        self._right_stack.addWidget(self.registry_widget)    

        right_layout.addWidget(self._right_stack, 1)
        top_section.addWidget(right_panel, 1)

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

        # Bottom timeline stack, network timeline index 0, registry timeline index 1
        self._timeline_stack = QStackedWidget()

        self.timeline_widget = CrossPCAPTimelineWidget()
        self.timeline_widget.setStyleSheet(f"""
            QFrame {{
                background-color: {THEME['surface']};
                border-top: 1px solid {THEME['border']};
            }}
        """)
        self.timeline_widget.setMinimumHeight(380)
        self._timeline_stack.addWidget(self.timeline_widget)   # index 0

        self.registry_timeline = RegistryTimelineWidget()
        self.registry_timeline.setMinimumHeight(380)
        self.registry_timeline.set_registry_table(self.registry_widget)
        self._timeline_stack.addWidget(self.registry_timeline) # index 1

        # Wire registry widget to also update the timeline when compare runs
        self.registry_widget.load_entries = self._registry_load_entries_hooked

        # Highlight timeline dot when a registry table row is selected
        self.registry_widget.entrySelected.connect(self.registry_timeline.highlight_entry)

        content_layout.addWidget(self._timeline_stack, 1)

        # Swap both stacks together when the tab changes
        def on_tab_changed(index):
            self._right_stack.setCurrentIndex(index)
            self._timeline_stack.setCurrentIndex(index)
            self.run_button.setVisible(index == 0)

        self._panel_group.idClicked.connect(on_tab_changed)

        root.addWidget(content)

    def _toggle_timeline(self):
        if self._timeline_stack.isVisible():
            self._timeline_stack.hide()
            self.left_panel.hide()
            self._timeline_toggle_btn.setText("▲  Show")
        else:
            self._timeline_stack.show()
            self.left_panel.show()
            self._timeline_toggle_btn.setText("▼  Hide")

    def _registry_load_entries_hooked(self, entries):
        # Call the real load_entries on the registry widget then feed the timeline
        RegistryWidget.load_entries(self.registry_widget, entries)
        self.registry_timeline.load_entries(entries)

    def _on_incognito_event_selected(self, gap: dict):
        # Focus the network timeline on the selected gap's time window
        self.timeline_widget.focus_on_gap(gap)

    def attempt_correlation(self):
        self._cached_browser_events = None
        self._cached_gaps = None

        # Auto-discover PCAP files from evidence folder
        evidence_dir = os.path.join(self.path, "evidence")
        PCAP_EXTENSIONS = ('.pcap', '.pcapng', '.cap')
        pcap_files = [
            f for f in os.listdir(evidence_dir)
            if os.path.isfile(os.path.join(evidence_dir, f))
            and f.lower().endswith(PCAP_EXTENSIONS)
        ]

        if not pcap_files:
            print("No PCAP files found in evidence folder.")
            return

        # Build selected fields dict, all files with DNS Query selected
        selected_fields = {fn: ['DNS Query'] for fn in pcap_files}

        # Load packet data
        packets_by_file = self._get_packets_for_files(selected_fields.keys())

        # Build timeline events
        timeline_data = self.correlation_engine.prepare_timeline_data(
            packets_by_file, selected_fields
        )
        self._last_timeline_data = timeline_data

        # Load PCAP lanes into network timeline
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

        self._cached_gaps = grouped_gaps

        # Group normal browser events by domain for the unified table
        normal_entries = self._group_browser_events(browser_events)

        # Save run and gaps to DB
        self.current_run_id = save_run(self.case_id, pcap_files, grouped_gaps)

        # Populate unified browser activity table
        self.incognito_widget.load_all_entries(grouped_gaps, normal_entries)

        # Add browser activity lane underneath the PCAP lanes
        self.timeline_widget.load_browser_activity(
            grouped_gaps,
            browser_events,
            gap_table_ref=self.incognito_widget
        )

        if not self._timeline_stack.isVisible():
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

            # 3. Fallback, read JSON file and migrate into the DB
            if not data:
                import json
                json_path = os.path.join(os.path.dirname(__file__), "packetFiles", f"{fn}_packets.json")
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

    def _group_browser_events(self, browser_events) -> list:
        # Group raw browser history events by domain into the same dict shape as gaps
        grouped = {}
        for ev in browser_events:
            domain = ev.value
            if not domain:
                continue
            if domain not in grouped:
                grouped[domain] = {
                    'domain': domain,
                    'count': 0,
                    'category': 'Browser History',
                    'first_seen': ev.timestamp,
                    'last_seen': ev.timestamp,
                    'entry_type': 'normal',
                }
            g = grouped[domain]
            g['count'] += 1
            if ev.timestamp < g['first_seen']:
                g['first_seen'] = ev.timestamp
            if ev.timestamp > g['last_seen']:
                g['last_seen'] = ev.timestamp

        return sorted(grouped.values(), key=lambda x: x['first_seen'])

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