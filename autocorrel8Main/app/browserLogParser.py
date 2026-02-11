import sqlite3
import json
from datetime import datetime
from correlationEngine import TimelineEvent
from urllib.parse import urlparse

class BrowserLogParser:

    def __init__(self):

        # Parse browser histrory from sqlite database
        self.supported_browsers = ['chrome', 'edge', 'firefox']

    def parse_browser_history(self, browser_name, history_db_path):

        # Extract the visited URLs from the history
        events = []

        conn = sqlite3.connect(history_db_path)
        cursor = conn.cursor()


        # Chrome stores visits in urls and visits tables
        query = """
            SELECT urls.url, urls.title, visits.visit_time
            FROM urls
            INNER JOIN visits ON urls.id = visits.url
            ORDER BY visits.visit_time"""
        
        cursor.execute(query)
        for row in cursor.fetchall():
            url, title, chrome_time = row

            # Chrome uses WebKit timestamp
            timestamp = self._chrome_time_to_datetime(chrome_time)

            # Extract domain from URL
            domain = self._extract_domain(url)

            event = TimelineEvent(
                timestamp=timestamp,
                event_type='domain',
                value=domain,
                pcap_name='browser_logs'
            )
            events.append(event)


        conn.close()
        return events
    
    def _chrome_time_to_datetime(self, chrome_time):

        # Convert chrome timestamp to datetime
        # Account for time difference between Crhome epoch and Unix epoch
        unix_timestamp = (chrome_time / 1000000) - 11644473600
        return datetime.fromtimestamp(unix_timestamp)
    
    def _extract_domain(self, url):

        # Extract the domain from URL
        parsed = urlparse(url)
        return parsed.netloc
    
            