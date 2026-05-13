import os
import sqlite3
from datetime import datetime
from correlationEngine import TimelineEvent
from urllib.parse import urlparse
from hashing import sha256_file
from database import store_evidence_hash, get_evidence_hash


class BrowserLogParser:

    def __init__(self):
        # Supported browsers and their schema identifiers
        self.supported_browsers = ['chrome', 'edge', 'firefox']
        self.last_hash = None
        self.last_hash_status = 'unchecked'

    def parse_browser_history(self, browser_name, history_db_path, case_id=None):
        # Hash the evidence file before parsing 
        self._verify_hash(history_db_path, case_id)

        # Auto-detect schema if browser_name not specified or unrecognised
        detected = self._detect_schema(history_db_path)
        schema = detected if detected else browser_name

        events = []
        conn = sqlite3.connect(history_db_path)
        cursor = conn.cursor()

        if schema == 'firefox':
            events = self._parse_firefox(cursor)
        else:
            # Chrome and Edge share the same Chromium schema
            events = self._parse_chrome(cursor)

        conn.close()
        return events

    def _parse_chrome(self, cursor):
        # Chrome/Edge: urls + visits tables, WebKit timestamp
        query = """
            SELECT urls.url, urls.title, visits.visit_time
            FROM urls
            INNER JOIN visits ON urls.id = visits.url
            ORDER BY visits.visit_time"""

        events = []
        cursor.execute(query)
        for url, title, chrome_time in cursor.fetchall():
            timestamp = self._chrome_time_to_datetime(chrome_time)
            domain = self._extract_domain(url)
            events.append(TimelineEvent(
                timestamp=timestamp,
                event_type='domain',
                value=domain,
                pcap_name='browser_logs'
            ))
        return events

    def _parse_firefox(self, cursor):
        # Firefox: moz_places + moz_historyvisits tables, Unix microsecond timestamp
        query = """
            SELECT moz_places.url, moz_places.title, moz_historyvisits.visit_date
            FROM moz_places
            INNER JOIN moz_historyvisits ON moz_places.id = moz_historyvisits.place_id
            ORDER BY moz_historyvisits.visit_date"""

        events = []
        cursor.execute(query)
        for url, title, firefox_time in cursor.fetchall():
            timestamp = self._firefox_time_to_datetime(firefox_time)
            domain = self._extract_domain(url)
            events.append(TimelineEvent(
                timestamp=timestamp,
                event_type='domain',
                value=domain,
                pcap_name='browser_logs'
            ))
        return events

    def _detect_schema(self, history_db_path):
        # Check which tables exist to determine browser schema
        try:
            conn = sqlite3.connect(history_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            conn.close()

            if 'moz_places' in tables and 'moz_historyvisits' in tables:
                return 'firefox'
            if 'urls' in tables and 'visits' in tables:
                return 'chrome'
        except Exception:
            pass
        return None

    def _verify_hash(self, path, case_id):
        # Hash file and store or verify against DB 
        self.last_hash = sha256_file(path)
        filename = os.path.basename(path)

        if case_id is not None:
            stored = get_evidence_hash(case_id, filename)
            if stored is None:
                store_evidence_hash(case_id, filename, self.last_hash, 'browser')
                self.last_hash_status = 'new'
            elif stored == self.last_hash:
                self.last_hash_status = 'verified'
            else:
                self.last_hash_status = 'mismatch'
        else:
            self.last_hash_status = 'unchecked'

    def _chrome_time_to_datetime(self, chrome_time):
        # WebKit epoch is 1 Jan 1601
        unix_timestamp = (chrome_time / 1_000_000) - 11_644_473_600
        return datetime.fromtimestamp(unix_timestamp)

    def _firefox_time_to_datetime(self, firefox_time):
        # Firefox uses Unix epoch microseconds 
        return datetime.fromtimestamp(firefox_time / 1_000_000)

    def _extract_domain(self, url):
        # Extract netloc (domain) from full URL
        parsed = urlparse(url)
        return parsed.netloc