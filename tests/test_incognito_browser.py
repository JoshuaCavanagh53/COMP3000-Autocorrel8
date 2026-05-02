import sqlite3
from datetime import datetime

import pytest

from autocorrel8Main.app.browserLogParser import BrowserLogParser
from autocorrel8Main.app.correlationEngine import CorrelationEngine, GapDetector, TimelineEvent


# Domain Extraction 

@pytest.mark.parametrize("url, expected", [
    ("https://www.example.com/path?q=1", "www.example.com"),
    ("http://sub.domain.co.uk/page", "sub.domain.co.uk"),
    ("https://192.168.1.1/login", "192.168.1.1"),
    ("ftp://files.example.com/file.txt", "files.example.com"),
    ("https://example.com", "example.com"),
])
def test_extract_domain(url, expected):
    assert BrowserLogParser()._extract_domain(url) == expected


@pytest.mark.parametrize("domain, expected", [
    ("www.example.com", "example.com"),          
    ("sub.example.com", "example.com"),          
    ("example.com", "example.com"),              
    ("shop.example.co.uk", "example.co.uk"),     
    ("host.local", None),                        
    ("", None),                                  
])
def test_extract_main_domain(domain, expected):
    assert GapDetector()._extract_main_domain(domain) == expected


def test_extract_main_domain_www_only():
    # www. is stripped before TLD resolution
    assert GapDetector()._extract_main_domain("www.bbc.co.uk") == "bbc.co.uk"


# Timestamp Normalisation 

def test_chrome_time_to_datetime_unix_epoch():
    # Chrome timestamp for 1970-01-01 00:00:00 UTC
    chrome_unix_epoch = 11644473600 * 1_000_000
    result = BrowserLogParser()._chrome_time_to_datetime(chrome_unix_epoch)
    assert result.year == 1970
    assert result.month == 1
    assert result.day == 1


def test_chrome_time_returns_datetime_object():
    result = BrowserLogParser()._chrome_time_to_datetime(13_350_000_000_000_000)
    assert isinstance(result, datetime)


def test_parse_timestamp_handles_int():
    ts = CorrelationEngine()._parse_timestamp(1_700_000_000)
    assert isinstance(ts, datetime)


def test_parse_timestamp_handles_float_string():
    ts = CorrelationEngine()._parse_timestamp("1700000000.5")
    assert isinstance(ts, datetime)


def test_parse_timestamp_passthrough_datetime():
    dt = datetime(2025, 1, 1, 12, 0, 0)
    assert CorrelationEngine()._parse_timestamp(dt) is dt


def test_parse_timestamp_invalid_string_returns_none():
    assert CorrelationEngine()._parse_timestamp("not-a-timestamp") is None


def test_parse_timestamp_none_returns_none():
    assert CorrelationEngine()._parse_timestamp(None) is None


# Incognito Gap Detection

def _make_event(domain, timestamp, event_type="domain", pcap="capture.pcap"):
    return TimelineEvent(
        timestamp=timestamp,
        event_type=event_type,
        value=domain,
        pcap_name=pcap,
    )


def test_find_gaps_returns_all_unmatched_pcap_events():
    t = datetime(2025, 1, 1, 12, 0, 0)
    pcap_events = [_make_event("example.com", t)]
    browser_events = []  # nothing in history
    gaps = GapDetector().find_gaps(pcap_events, browser_events)
    assert len(gaps) == 1
    assert gaps[0].value == "example.com"


def test_find_gaps_suppresses_matched_domain():
    t = datetime(2025, 1, 1, 12, 0, 0)
    pcap_events = [_make_event("example.com", t)]
    browser_events = [_make_event("example.com", t)]
    gaps = GapDetector().find_gaps(pcap_events, browser_events)
    assert gaps == []


def test_find_gaps_respects_time_window():
    t_pcap = datetime(2025, 1, 1, 12, 0, 0)
    # Browser entry 5s later 
    t_browser = datetime(2025, 1, 1, 12, 0, 5)
    pcap_events = [_make_event("example.com", t_pcap)]
    browser_events = [_make_event("example.com", t_browser)]
    gaps = GapDetector(time_window_seconds=10).find_gaps(pcap_events, browser_events)
    assert gaps == []


def test_find_gaps_outside_time_window_is_flagged():
    t_pcap = datetime(2025, 1, 1, 12, 0, 0)
    # Browser entry 60s later
    t_browser = datetime(2025, 1, 1, 12, 1, 0)
    pcap_events = [_make_event("example.com", t_pcap)]
    browser_events = [_make_event("example.com", t_browser)]
    gaps = GapDetector(time_window_seconds=10).find_gaps(pcap_events, browser_events)
    assert len(gaps) == 1


def test_find_gaps_ignores_non_domain_events():
    t = datetime(2025, 1, 1, 12, 0, 0)
    pcap_events = [_make_event("1.2.3.4", t, event_type="ip")]
    browser_events = []
    gaps = GapDetector().find_gaps(pcap_events, browser_events)
    assert gaps == []


def test_find_gaps_subdomain_matched_by_main_domain():
    t = datetime(2025, 1, 1, 12, 0, 0)
    # PCAP sees sub.example.com; browser only recorded example.com
    pcap_events = [_make_event("sub.example.com", t)]
    browser_events = [_make_event("example.com", t)]
    gaps = GapDetector(time_window_seconds=10).find_gaps(pcap_events, browser_events)
    assert gaps == []


def test_find_gaps_grouped_deduplicates_by_main_domain():
    t = datetime(2025, 1, 1, 12, 0, 0)
    pcap_events = [
        _make_event("a.reddit.com", t),
        _make_event("b.reddit.com", t),
    ]
    grouped = GapDetector().find_gaps_grouped(pcap_events, [])
    domains = [g["domain"] for g in grouped]
    assert domains.count("reddit.com") == 1


def test_find_gaps_grouped_count_is_correct():
    t = datetime(2025, 1, 1, 12, 0, 0)
    pcap_events = [_make_event("reddit.com", t)] * 3
    grouped = GapDetector().find_gaps_grouped(pcap_events, [])
    assert grouped[0]["count"] == 3


# Browser SQLite Parsing 

def _make_chrome_db(tmp_path, rows):
    db = tmp_path / "History"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE urls (id INTEGER PRIMARY KEY, url TEXT, title TEXT)")
    conn.execute("CREATE TABLE visits (id INTEGER PRIMARY KEY, url INTEGER, visit_time INTEGER)")
    for i, (url, title, ts) in enumerate(rows, start=1):
        conn.execute("INSERT INTO urls VALUES (?, ?, ?)", (i, url, title))
        conn.execute("INSERT INTO visits VALUES (?, ?, ?)", (i, i, ts))
    conn.commit()
    conn.close()
    return str(db)


def test_parse_chrome_history_returns_events(tmp_path):
    chrome_ts = (1_700_000_000 + 11644473600) * 1_000_000
    db = _make_chrome_db(tmp_path, [("https://example.com", "Example", chrome_ts)])
    events = BrowserLogParser().parse_browser_history("chrome", db)
    assert len(events) == 1
    assert events[0].value == "example.com"


def test_parse_chrome_history_empty_db_returns_no_events(tmp_path):
    db = _make_chrome_db(tmp_path, [])
    events = BrowserLogParser().parse_browser_history("chrome", db)
    assert events == []


def test_parse_chrome_history_event_type_is_domain(tmp_path):
    chrome_ts = (1_700_000_000 + 11644473600) * 1_000_000
    db = _make_chrome_db(tmp_path, [("https://example.com", "Example", chrome_ts)])
    events = BrowserLogParser().parse_browser_history("chrome", db)
    assert events[0].event_type == "domain"


def test_parse_chrome_history_multiple_rows(tmp_path):
    base_ts = (1_700_000_000 + 11644473600) * 1_000_000
    rows = [
        ("https://example.com", "Example", base_ts),
        ("https://reddit.com/r/test", "Reddit", base_ts + 1_000_000),
    ]
    db = _make_chrome_db(tmp_path, rows)
    events = BrowserLogParser().parse_browser_history("chrome", db)
    assert len(events) == 2
    domains = {e.value for e in events}
    assert "example.com" in domains
    assert "reddit.com" in domains