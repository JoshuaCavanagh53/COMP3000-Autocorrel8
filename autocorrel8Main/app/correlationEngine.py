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
                    # Attach protocol for info panel
                    event.protocol = packet.get('protocol')
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
            'Protocols': ('protocol', lambda p: p.get('protocol')),
            'DNS Query': ('domain', lambda p: p.get('layers', {}).get('dns', {}).get('query')),
            'HTTP Host': ('domain', lambda p: p.get('layers', {}).get('http', {}).get('host')),
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
    
# Gap detection 
class GapDetector:

    def __init__(self, time_window_seconds=10):
        self.time_window = time_window_seconds

        # Noise patterns used for scoring, these are common domains/subdomains that are likely to be background noise
        self.noise_patterns = [
            # LOCAL NETWORK SERVICES 
            '.local', '_tcp.local', '_udp.local', 'wpad',
            
            # GOOGLE INFRASTRUCTURE
            'google.com', 'googleapis.com', 'googleusercontent.com',
            'googlevideo.com', 'googlezip.net', 'gstatic.com',
            'ytimg.com', 'ggpht.com', 'youtube.com',
            'google-analytics.com', 'googletagmanager.com', 
            'googleadservices.com', 'googlesyndication.com',
            'doubleclick.net', 'admob.com',
            
            # MICROSOFT SERVICES 
            'microsoft.com', 'microsoftonline.com', 'microsoftazuread',
            'windows.com', 'office.com', 'office365.com', 'live.com',
            'msn.com', 'bing.com', 'azure.com', 'azurewebsites.net',
            
            # SPOTIFY 
            'spotify.com', 'spclient.', 'spotilocal.com',
            
            # CDN & STATIC
            'cloudflare.', 'akamai.', 'fastly.', 'cdn.', 'static.',
            'cloudfront.net',
            
            # ANALYTICS & TRACKING 
            'analytics.', 'telemetry.', 'metrics.', 'tracking.',
            'clarity.ms', 'hotjar.', 'segment.', 'mixpanel.',
            
            # ADS 
            'ads.', 'ad.', 'adservice', 'adserver', 'advertising',
            'admedo.com', 'criteo.', 'taboola.', 'outbrain.', 'ttl.ai',
            
            # COOKIES & CONSENT 
            'cookiebot.com', 'consent.', 'privacy.',
            
            # SAFETY & SECURITY 
            'safebrowsing', 'passwordsleakcheck', 'passwordreset',
            
            # API & INFRASTRUCTURE
            'api.', 'api-', 'clients.', 'clients1.', 'clients2.',
            'clients3.', 'clients4.', 'clients5.', 'clients6.',
            
            # CONTENT DELIVERY 
            'avatars.', 'user-images.', 'githubassets.com',
            'githubusercontent.com',
            
            # SOCIAL INFRASTRUCTURE 
            'facebook.net', 'fbcdn.net', 'connect.facebook.', 
            'platform.twitter.com',
            
            # OTHER
            'apple.com', 'icloud.com', 'amazonaws.com',
        ]

    def find_gaps(self, pcap_events, browser_events):
        
        # Find gaps 
        
        gaps = []
        browser_domains = self._group_by_domain_and_time(browser_events)
        
        for pcap_event in pcap_events:
            
            # Only check domain-based events
            if pcap_event.event_type not in ['domain']:
                continue
            
            # Skip if matches browser entry
            if self._has_matching_browser_entry(pcap_event, browser_domains):
                continue
            
            # Keep all gaps 
            gaps.append(pcap_event)
        
        return gaps
    
    def find_gaps_grouped(self, pcap_events, browser_events):
        
        # Find gaps, group by domain, and score suspiciousness
        
        # Get raw gaps 
        raw_gaps = self.find_gaps(pcap_events, browser_events)
        
        # Count domain frequencies
        domain_counts = {}
        for gap in raw_gaps:
            domain = gap.value
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Group by main domain
        grouped = {}
        for gap in raw_gaps:
            domain = gap.value
            
            # Extract main domain for grouping
            main_domain = self._extract_main_domain(domain) or domain
            
            if main_domain not in grouped:
                grouped[main_domain] = {
                    'domain': main_domain,
                    'subdomains': set(),
                    'first_seen': gap.timestamp,
                    'last_seen': gap.timestamp,
                    'count': 0,
                    'sources': set(),
                    'suspiciousness': 0,
                    'category': 'Unknown'
                }
            
            grouped[main_domain]['count'] += 1
            grouped[main_domain]['subdomains'].add(domain)
            grouped[main_domain]['sources'].add(gap.pcap_name)
            
            # Track time range
            if gap.timestamp < grouped[main_domain]['first_seen']:
                grouped[main_domain]['first_seen'] = gap.timestamp
            if gap.timestamp > grouped[main_domain]['last_seen']:
                grouped[main_domain]['last_seen'] = gap.timestamp
        
        # Score each domain
        for domain_data in grouped.values():
            domain_data['suspiciousness'], domain_data['category'] = self._score_domain(
                domain_data['domain'],
                domain_data['count'],
                len(domain_data['subdomains'])
            )
        
        # Sort by suspiciousness (high to low), then by count (low to high)
        grouped_list = list(grouped.values())
        grouped_list.sort(key=lambda x: (-x['suspiciousness'], x['count']))
        
        return grouped_list
    
    def _score_domain(self, domain, count, subdomain_count):
        
        # Score suspiciousness from 0-100
        # 100 = Very suspicious (likely incognito browsing)
        # 0 = Not suspicious (infrastructure/background)
        
        score = 50  # Start neutral
        category = "Unknown"
        

        if not domain:
            return 0, "Invalid"
        
        domain_lower = domain.lower()
        
        # Check for specific high-value browsing sites
        # These should score high even if they have many requests
        
        # Social Media 
        social_sites = ['reddit.com', 'twitter.com', 'facebook.com', 'instagram.com', 
                    'tiktok.com', 'snapchat.com', 'linkedin.com', 'pinterest.com',
                    'tumblr.com', 'whatsapp.com', 'discord.com']
        if any(site in domain_lower for site in social_sites):
            score = 85
            category = "Social Media"
            if 1 <= count <= 20:
                score += 15  # Boost for low frequency
            return min(100, score), category
        
        # Streaming/Entertainment 
        streaming_sites = ['youtube.com', 'netflix.com', 'hulu.com', 'disneyplus.com', 
                        'primevideo.', 'twitch.tv', 'spotify.com', 'soundcloud.com']
        if any(site in domain_lower for site in streaming_sites):
            score = 70
            category = "Streaming/Entertainment"
            if 1 <= count <= 20:
                score += 15
            return min(100, score), category
        
        # News/Content 
        content_sites = ['bbc.co', 'cnn.com', 'nytimes.com', 'theguardian.com', 'guardian.co.uk',
                        'techcrunch.com', 'medium.com', 'substack.com', 'news.']
        if any(site in domain_lower for site in content_sites):
            score = 75
            category = "News/Content"
            if 1 <= count <= 20:
                score += 10
            return min(100, score), category
        
        # Shopping/Services 
        shopping_sites = ['amazon.', 'ebay.', 'etsy.', 'uber', 'deliveroo', 
                        'justeat.', 'grubhub.', 'doordash.']
        if any(site in domain_lower for site in shopping_sites):
            score = 75
            category = "Shopping/Services"
            if 1 <= count <= 20:
                score += 15
            return min(100, score), category
        
        # Adult Content 
        adult_sites = ['porn', 'xxx', 'sex', 'adult', 'cam', 'onlyfans']
        if any(site in domain_lower for site in adult_sites):
            score = 95
            category = "Adult Content"
            return min(100, score), category
        
        # Development/Work 
        dev_sites = ['github.com', 'gitlab.com', 'stackoverflow.com', 'npmjs.com']
        if any(site in domain_lower for site in dev_sites):
            score = 65
            category = "Development"
            if 1 <= count <= 10:
                score += 10
            return min(100, score), category
        
        # Apply penalties for infrastructure/noise
        
        # Local network 
        if '.local' in domain_lower or domain_lower == 'wpad' or 'wpad.' in domain_lower:
            return 10, "Local Network"
        
        # Ads & Tracking
        ad_patterns = [
            'ad-', 'ads-', 'ads.', '.ad.', 'adservice', 'adserver', 'adsystem',
            'advertising', 'googleads', 'doubleclick', 'admob', 'adsrvr',
            'adtech', 'adform', 'adriver', 'admedo', 'adnxs', 'adroll',
            'bidswitch', 'casalemedia', 'crwdcntrl', 'quantserve', 'rubiconproject',
            'openx', 'pubmatic', 'taboola', 'outbrain', 'criteo',
            'fastclick', 'lijit', 'omnitag', 'onetag', 'kueez', 'minutemedia-prebid',
            'quantcount', 'pbxai', 'cootlogix', 'indexww', 'id5-sync',
            '3lift', 'btloader', 'snigelweb', '4dex', 'clarium',
            'anonymised.io', 'anonm.io', 'ad-delivery', 'adtrafficquality'
        ]
        if any(pattern in domain_lower for pattern in ad_patterns):
            return 15, "Ads/Tracking"
        
        # Analytics
        analytics_patterns = [
            'analytics', 'telemetry', 'metrics', 'tracking', 'clarity.ms',
            'hotjar', 'segment', 'mixpanel', 'siteimprove', 'quantcast'
        ]
        if any(pattern in domain_lower for pattern in analytics_patterns):
            return 20, "Analytics"
        
        # CDN & Static Content 
        cdn_patterns = [
            'cdn.', 'cdn-', 'cloudflare', 'cloudfront', 'akamai', 'fastly',
            'static.', 'media.', 'images.', 'assets.', 'jsdelivr',
            'maxcdn', 'tiqcdn', 'roocdn', 'rlcdn', 'creativecdn',
            'px-cdn', 'openxcdn', 'vscode-cdn', 'spotifycdn', 'scdn.co'
        ]
        if any(pattern in domain_lower for pattern in cdn_patterns):
            return 25, "CDN/Infrastructure"
        
        # Cookie/Consent 
        if 'cookie' in domain_lower or 'consent' in domain_lower or 'privacy' in domain_lower:
            return 25, "Cookie/Consent"
        
        # Security/Safety
        if 'safebrowsing' in domain_lower or 'passwordleak' in domain_lower or 'passwordreset' in domain_lower:
            return 20, "Security"
        
        # Google Infrastructure
        google_infra = [
            'gstatic.com', 'gvt1.com', 'gvt2.com', 'gvt3.com', '1e100.net',
            'googlezip', 'googleapis.com', 'googleusercontent.com',
            'googlevideo.com', 'googletagmanager', 'googletagservices',
            'googlesyndication', 'googleadservices', 'clients.google', 
            'clients1.', 'clients2.', 'clients3.', 'clients4.',
            'clients5.', 'clients6.', 'ogs.google', 'android.clients'
        ]
        if any(pattern in domain_lower for pattern in google_infra):
            return 25, "Google Infrastructure"
        
        # Microsoft Infrastructure 
        ms_infra = [
            'microsoft.com', 'microsoftonline.com', 'microsoftazuread',
            'windows.com', 'office.com', 'office365.com', 'office.net',
            'live.com', 'msn.com', 'bing.com', 'azure.com', 
            'azurewebsites.net', 'msftauth', 'msauth'
        ]
        if any(pattern in domain_lower for pattern in ms_infra):
            return 25, "Microsoft Infrastructure"
        
        # Other Infrastructure
        other_infra = [
            'amazonaws.com', 'apple.com', 'icloud.com', 'facebook.net',
            'fbcdn.net', 'githubassets.com', 'githubusercontent.com',
            'grammarly.io', 'grammarly.com', 'sentry.io', 'stripe.network',
            'stripe.com', 'onetrust.com', 'cookielaw.org', 'polyfill',
            'mapbox.com', 'teuteuf.fr'
        ]
        if any(pattern in domain_lower for pattern in other_infra):
            return 30, "Infrastructure"
        
        # Frequency based scoring for unknown domains
        
        score = 50  # Reset to neutral for unknowns
        
        # High frequency = background service
        if count > 100:
            score -= 30
            category = "High-Frequency Service"
        elif count > 50:
            score -= 20
            category = "Background Service"
        elif count > 30:
            score -= 10
        
        # Low frequency = manual browsing
        if 1 <= count <= 10:
            score += 25
            if category == "Unknown":
                category = "Low-Frequency Domain"
        elif 11 <= count <= 20:
            score += 15
            if category == "Unknown":
                category = "Low-Frequency Domain"
        
        # Many subdomains = infrastructure
        if subdomain_count > 10:
            score -= 20
        elif subdomain_count > 5:
            score -= 10
        
        # Simple domain structure 
        parts = domain_lower.split('.')
        if len(parts) == 2:
            score += 10
            if category == "Unknown":
                category = "Main Domain"
        
        # Complex subdomain patterns 
        for part in parts:
            if part.count('-') >= 3:  # Many hyphens
                score -= 15
                category = "Generated Domain"
                break
            if part and part[0].isdigit():  # Starts with number
                score -= 10
                break
        
        # Keep score in range
        score = max(0, min(100, score))
        
        return score, category

    def _group_by_domain_and_time(self, browser_events):
        
        # Create lookup dict: {domain: [timestamps]}
        lookup = {}
        for event in browser_events:
            domain = event.value
            if domain not in lookup:
                lookup[domain] = []
            lookup[domain].append(event.timestamp)
        return lookup
    
    def _extract_main_domain(self, domain):
        
        # Extract main domain from subdomain
        if not domain:
            return None
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Skip local domains
        if domain.endswith('.local'):
            return None
        
        # Split by dots
        parts = domain.split('.')
        
        # Handle special TLDs
        if len(parts) >= 2:
            # Common multi-part TLDs
            multi_tlds = ['.co.uk', '.co.jp', '.com.au', '.gov.uk', 
                         '.co.za', '.com.br', '.co.in']
            domain_suffix = '.' + '.'.join(parts[-2:])
            
            if domain_suffix in multi_tlds and len(parts) >= 3:
                return '.'.join(parts[-3:])  # domain.co.uk
            else:
                return '.'.join(parts[-2:])  # domain.com
        
        return domain

    def _has_matching_browser_entry(self, pcap_event, browser_lookup):
        
        # Check if PCAP event has corresponding browser log entry
        domain = pcap_event.value
        timestamp = pcap_event.timestamp
        
        if not domain:
            return False
        
        # Check main domain (handles subdomains)
        main_domain = self._extract_main_domain(domain)
        
        # Check both exact domain and main domain
        domains_to_check = [domain]
        if main_domain and main_domain != domain:
            domains_to_check.append(main_domain)
        
        for check_domain in domains_to_check:
            if check_domain in browser_lookup:
                # Check if timestamp matches within time window
                for browser_time in browser_lookup[check_domain]:
                    time_diff = abs((timestamp - browser_time).total_seconds())
                    if time_diff <= self.time_window:
                        return True
        
        return False