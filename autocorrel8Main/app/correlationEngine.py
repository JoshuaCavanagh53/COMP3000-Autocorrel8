from datetime import datetime

# Timeline event data structure
class TimelineEvent:
    def __init__(self, timestamp, event_type, value, pcap_name):
        self.timestamp = timestamp
        self.event_type = event_type
        self.value = value
        self.pcap_name = pcap_name

class CorrelationEngine:

    def __init__(self):
        self.selected_fields = {}

    # Extract timeline events from packet data based on the selected fields
    def extract_event_from_packets(self, packets, pcap_name, selected_fields):
        
        events = []
        for packet in packets:
            # Get the timestamp
            timestamp = self._parse_timestamp(packet.get('timestamp'))
            if not timestamp:
                continue
            # Extract events based on selected fields
            for field in selected_fields:
                event_type, value = self._extract_field_value(packet, field)
                if value:
                    event = TimelineEvent(
                        timestamp=timestamp,
                        event_type = event_type,
                        value = value,
                        pcap_name = pcap_name
                    )
                    events.append(event)
        return events
        
    def _parse_timestamp(self, timestamp):

        # Convert timestamp to datetime object

        if isinstance(timestamp, datetime):
            return timestamp
        
        elif isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(float(timestamp))
        
        elif isinstance(timestamp, str):
            try:
                return datetime.fromtimestamp(float(timestamp))
            except:
                return None
        return None
    
    def _extract_field_value(self, packet, field_name):

        # Extract value from packet based on field name

        field_mapping = {
            'Src IP': ('ip', lambda p: p.get('src_ip')),
            'Dst IP': ('ip', lambda p: p.get('dst_ip')),
            'TCP Src Port': ('port', lambda p: p.get('src_port')),
            'TCP Dst Port': ('port', lambda p: p.get('dst_port')),
            'UDP Src Port': ('port', lambda p: p.get('src_port')),
            'UDP Dst Port': ('port', lambda p: p.get('dst_port')),
            'Protocols': ('protocol', lambda p: p.get('protocol')),
            'DNS Query': ('domain', lambda p: p.get('layers', {}).get('dns', {}).get('query')),
            'HTTP Host': ('domain', lambda p: p.get('layers', {}).get('http', {}).get('host')),
            'TLS SNI': ('domain', lambda p: p.get('layers', {}).get('tls', {}).get('server_name')),
        }

        if field_name in field_mapping:
            event_type, extractor = field_mapping[field_name]
            value = extractor(packet)
            return (event_type, value)
        
        return (None, None)
    
    def prepare_timeline_data(self, packets_by_file, selected_fields_by_file):
        
        # Prepare all timeline data for visualization

        timeline_data = {}

        for filename, packets in packets_by_file.items():
            selected_fields = selected_fields_by_file.get(filename, [])

            if selected_fields:
                events = self.extract_event_from_packets(
                    packets,
                    filename,
                    selected_fields
                )
                timeline_data[filename] = events

        return timeline_data