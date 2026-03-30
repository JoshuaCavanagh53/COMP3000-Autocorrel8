import json
import os
import csv
import re


KEY_CATEGORIES = {
    # Persistence, autorun locations
    r'CurrentVersion\Run': 'Persistence - Run Key',
    r'CurrentVersion\RunOnce': 'Persistence - RunOnce',
    r'CurrentVersion\RunOnceEx': 'Persistence - RunOnceEx',
    r'BootExecute': 'Persistence - Boot Execute',
    r'Image File Execution Options': 'Persistence - IFEO Hijack',
    r'AppInit_DLLs': 'Persistence - AppInit DLL',
    r'Winlogon': 'Persistence - Winlogon',
    r'Shell Folders': 'Persistence - Shell Folder',
    r'Browser Helper Objects': 'Persistence - Browser Helper',
    r'CurrentControlSet\Services': 'Persistence - Services',
    r'Policies\Explorer\Run': 'Persistence - Policy Run',
    r'Group Policy\Scripts': 'Persistence - Group Policy',

    # COM hijacking
    r'HKCU\SOFTWARE\Classes\CLSID': 'COM Hijack',
    r'InprocServer32': 'COM Hijack - InprocServer',

    # Network and proxy
    r'Internet Settings': 'Network - Proxy Settings',
    r'FirewallPolicy': 'Network - Firewall Policy',
    r'Winsock': 'Network - Winsock',
    r'Tcpip\Parameters': 'Network - TCP/IP',
    r'NameServer': 'Network - DNS Server',

    # Security and authentication
    r'CurrentControlSet\Control\Lsa': 'Security - LSA',
    r'SAM\SAM': 'Security - User Accounts',
    r'SecurityProviders': 'Security - Auth Providers',
    r'DisableAntiSpyware': 'Security - Defender Disabled',
    r'DisableRealtimeMonitoring': 'Security - Defender Disabled',

    # User activity
    r'RecentDocs': 'Activity - Recent Docs',
    r'RunMRU': 'Activity - Run History',
    r'TypedURLs': 'Activity - Typed URLs',
    r'ComDlg32\OpenSavePidlMRU': 'Activity - File Open/Save',
    r'UserAssist':'Activity - Program Execution',

    # System configuration
    r'CurrentVersion\Windows': 'System - Windows Config',
    r'Session Manager': 'System - Session Manager',
    r'Environment': 'System - Environment Vars',
    r'FileRenameOperations': 'System - Pending File Ops',
}


class RegistryParser:

    # File loading 
    def load_file(self, path: str) -> dict:
        # Auto-detects format from extension
        ext = os.path.splitext(path)[1].lower()
        if ext == '.json':
            return self._load_json(path)
        if ext == '.csv':
            return self._load_ftk_csv(path)
        if ext == '.reg':
            return self._load_reg(path)
        raise ValueError(f"Unsupported format: {ext} — use .reg, .csv, or .json")

    def _load_json(self, path: str) -> dict:
        with open(path, 'r') as f:
            data = json.load(f)
        # Support both raw dict
        if 'keys' in data:
            return data['keys']
        return data

    def _load_reg(self, path: str) -> dict:
        # Parses standard .reg file format exported from regedit or FTK
        snapshot = {}
        current_key = None

        try:
            with open(path, 'r', encoding='utf-16', errors='replace') as f:
                lines = f.readlines()
            if lines and 'Windows Registry Editor' not in lines[0]:
                raise UnicodeError
        except (UnicodeError, UnicodeDecodeError):
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

        for line in lines:
            line = line.strip()

            if not line or line.startswith(';'):
                continue

            # Key path line 
            if line.startswith('['):
                deleted = line.startswith('[-')
                key_path = line.lstrip('[-').rstrip(']')
                key_path = self._normalise_hive(key_path)
                if not deleted:
                    current_key = key_path
                    if current_key not in snapshot:
                        snapshot[current_key] = {}
                else:
                    current_key = None
                continue

            # Value line
            if current_key is not None and '=' in line:
                name, data = self._parse_reg_value(line)
                if name is not None:
                    snapshot[current_key][name] = data

        return snapshot

    def _parse_reg_value(self, line: str):
        try:
            if line.startswith('@='):
                name = '(Default)'
                raw = line[2:]
            else:
                match = re.match(r'^"((?:[^"\\]|\\.)*)"\s*=\s*(.*)', line)
                if not match:
                    return None, None
                name = match.group(1).replace('\\"', '"')
                raw = match.group(2)

            if raw.startswith('"'):
                data = raw.strip('"').replace('\\\\', '\\').replace('\\"', '"')
            elif raw.startswith('dword:'):
                data = str(int(raw[6:], 16))
            elif raw.startswith('hex'):
                data = raw
            else:
                data = raw

            return name, data
        except Exception:
            return None, None

    def _load_ftk_csv(self, path: str) -> dict:
        # Parses FTK Registry Viewer CSV export
        # Handles column name variations between different FTK versions
        snapshot = {}

        with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key_path = (
                    row.get('Key Path') or row.get('Key') or
                    row.get('Registry Key') or row.get('Full Path') or ''
                ).strip()
                value_name = (
                    row.get('Value Name') or row.get('Name') or
                    row.get('Value') or ''
                ).strip()
                value_data = (
                    row.get('Value Data') or row.get('Data') or
                    row.get('Value Data (Hex)') or ''
                ).strip()

                if not key_path:
                    continue

                key_path = self._normalise_hive(key_path)

                if key_path not in snapshot:
                    snapshot[key_path] = {}

                snapshot[key_path][value_name or '(Default)'] = value_data

        return snapshot

    # Comparison

    def compare(self, baseline_path: str, snapshot_path: str) -> list[dict]:
        baseline = self.load_file(baseline_path)
        snapshot = self.load_file(snapshot_path)
        changes = []

        all_keys = set(baseline) | set(snapshot)
        for key_path in all_keys:
            base_vals = baseline.get(key_path, {})
            snap_vals = snapshot.get(key_path, {})
            all_names = set(base_vals) | set(snap_vals)

            category = self._categorise_key(key_path)

            for name in all_names:
                in_base = name in base_vals
                in_snap = name in snap_vals

                if in_snap and not in_base:
                    changes.append({
                        'change_type': 'added',
                        'key_path': key_path,
                        'value_name': name,
                        'old_data': '',
                        'new_data': snap_vals[name],
                        'category': category,
                    })
                elif in_base and not in_snap:
                    changes.append({
                        'change_type': 'deleted',
                        'key_path': key_path,
                        'value_name': name,
                        'old_data': base_vals[name],
                        'new_data': '',
                        'category': category,
                    })
                elif base_vals[name] != snap_vals[name]:
                    changes.append({
                        'change_type': 'modified',
                        'key_path': key_path,
                        'value_name': name,
                        'old_data': base_vals[name],
                        'new_data': snap_vals[name],
                        'category': category,
                    })

        return changes

    # Helpers

    def _categorise_key(self, key_path: str) -> str:
        # Match key path against known categories, return first match
        for pattern, label in KEY_CATEGORIES.items():
            if pattern.lower() in key_path.lower():
                return label
        return 'Other'

    def _normalise_hive(self, key_path: str) -> str:
        # Convert full hive names to short form
        replacements = [
            ('HKEY_LOCAL_MACHINE', 'HKLM'),
            ('HKEY_CURRENT_USER', 'HKCU'),
            ('HKEY_CLASSES_ROOT', 'HKCR'),
            ('HKEY_USERS', 'HKU'),
            ('HKEY_CURRENT_CONFIG', 'HKCC'),
        ]
        for full, short in replacements:
            if key_path.upper().startswith(full):
                return short + key_path[len(full):]
        return key_path