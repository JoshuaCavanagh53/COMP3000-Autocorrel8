import winreg
import json
import os
from datetime import datetime

HIVES = {
    'HKCU': winreg.HKEY_CURRENT_USER,
    'HKLM': winreg.HKEY_LOCAL_MACHINE,
}

# Scan for persistence keys which are commonly used for malware
PERSISTENCE_KEYS = [
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_CURRENT_USER,  r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Windows"),
    (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services"),
]


class RegistryParser:

    def take_snapshot(self) -> dict:
        snapshot = {}
        for hive, key_path in PERSISTENCE_KEYS:
            try:
                key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
                values = {}
                i = 0
                while True:
                    try:
                        name, data, _ = winreg.EnumValue(key, i)
                        values[name] = str(data)
                        i += 1
                    except OSError:
                        break
                winreg.CloseKey(key)
                hive_name = 'HKCU' if hive == winreg.HKEY_CURRENT_USER else 'HKLM'
                snapshot[f"{hive_name}\\{key_path}"] = values
            except OSError:
                pass
        return snapshot

    def save_snapshot(self, path: str):
        snapshot = self.take_snapshot()
        with open(path, 'w') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'keys': snapshot}, f, indent=2)

    def compare(self, baseline_path: str, snapshot_path: str) -> list[dict]:
        with open(baseline_path) as f:
            baseline = json.load(f)['keys']
        with open(snapshot_path) as f:
            snapshot = json.load(f)['keys']

        changes = []

        all_keys = set(baseline) | set(snapshot)
        for key_path in all_keys:
            base_vals = baseline.get(key_path, {})
            snap_vals = snapshot.get(key_path, {})
            all_names = set(base_vals) | set(snap_vals)

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
                    })
                elif in_base and not in_snap:
                    changes.append({
                        'change_type': 'deleted',
                        'key_path': key_path,
                        'value_name': name,
                        'old_data': base_vals[name],
                        'new_data': '',
                    })
                elif base_vals[name] != snap_vals[name]:
                    changes.append({
                        'change_type': 'modified',
                        'key_path': key_path,
                        'value_name': name,
                        'old_data': base_vals[name],
                        'new_data': snap_vals[name],
                    })

        return changes
    
