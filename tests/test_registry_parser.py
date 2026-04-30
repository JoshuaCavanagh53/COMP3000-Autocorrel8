import json

import pytest

from autocorrel8Main.app.registryParser import RegistryParser


# Hive normalisation

@pytest.mark.parametrize("given, expected", [
    ("HKEY_LOCAL_MACHINE\\Software\\Test", "HKLM\\Software\\Test"),
    ("HKEY_CURRENT_USER\\Software", "HKCU\\Software"),
    ("HKEY_CLASSES_ROOT\\.txt", "HKCR\\.txt"),
    ("HKEY_USERS\\S-1-5", "HKU\\S-1-5"),
    ("HKEY_CURRENT_CONFIG\\System", "HKCC\\System"),
    ("HKLM\\Software\\Already\\Short", "HKLM\\Software\\Already\\Short"),
    ("hkey_local_machine\\lower\\case", "HKLM\\lower\\case"),
])
def test_normalise_hive(given, expected):
    assert RegistryParser()._normalise_hive(given) == expected


# Key categorisation

@pytest.mark.parametrize("key_path, category", [
    ("HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run", "Persistence - Run Key"),
    ("HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce", "Persistence - RunOnce"),
    ("HKLM\\SYSTEM\\CurrentControlSet\\Services\\Foo", "Persistence - Services"),
    ("HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings", "Network - Proxy Settings"),
    ("HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\TypedURLs", "Activity - Typed URLs"),
    ("HKLM\\SYSTEM\\Nothing\\Of\\Interest", "Other"),
])
def test_categorise_key(key_path, category):
    assert RegistryParser()._categorise_key(key_path) == category


def test_categorise_key_is_case_insensitive():
    p = RegistryParser()
    assert p._categorise_key("HKLM\\SOFTWARE\\MICROSOFT\\WINDOWS\\CURRENTVERSION\\RUN") == "Persistence - Run Key"


# .reg value parsing

def test_parse_reg_value_string():
    name, data = RegistryParser()._parse_reg_value('"MyApp"="C:\\\\Program Files\\\\app.exe"')
    assert name == "MyApp"
    assert data == "C:\\Program Files\\app.exe"


def test_parse_reg_value_dword_converted_to_decimal():
    name, data = RegistryParser()._parse_reg_value('"Enabled"=dword:00000001')
    assert name == "Enabled"
    assert data == "1"


def test_parse_reg_value_default_key():
    name, data = RegistryParser()._parse_reg_value('@="default value"')
    assert name == "(Default)"
    assert data == "default value"


def test_parse_reg_value_hex_passed_through():
    name, data = RegistryParser()._parse_reg_value('"Bytes"=hex:01,02,03')
    assert name == "Bytes"
    assert data.startswith("hex")


def test_parse_reg_value_malformed_returns_none():
    name, data = RegistryParser()._parse_reg_value("this is not a value line")
    assert name is None
    assert data is None


# .reg file loading

SAMPLE_REG = """Windows Registry Editor Version 5.00

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run]
"SecurityHealth"="C:\\\\Windows\\\\system32\\\\SecurityHealthSystray.exe"
"MyApp"="C:\\\\Program Files\\\\MyApp\\\\app.exe"

[HKEY_CURRENT_USER\\Software\\Test]
@="DefaultValue"
"Flag"=dword:00000001
"""


def test_load_reg_utf8(tmp_path):
    f = tmp_path / "snapshot.reg"
    f.write_text(SAMPLE_REG, encoding="utf-8")
    data = RegistryParser()._load_reg(str(f))

    run_key = "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"
    assert run_key in data
    assert data[run_key]["MyApp"] == "C:\\Program Files\\MyApp\\app.exe"
    assert data[run_key]["SecurityHealth"] == "C:\\Windows\\system32\\SecurityHealthSystray.exe"

    test_key = "HKCU\\Software\\Test"
    assert data[test_key]["(Default)"] == "DefaultValue"
    assert data[test_key]["Flag"] == "1"


def test_load_reg_utf16(tmp_path):
    # regedit exports in UTF-16 with BOM by default
    f = tmp_path / "snapshot.reg"
    f.write_text(SAMPLE_REG, encoding="utf-16")
    data = RegistryParser()._load_reg(str(f))
    assert "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" in data


def test_load_reg_skips_deleted_keys(tmp_path):
    content = (
        "Windows Registry Editor Version 5.00\n\n"
        "[-HKEY_LOCAL_MACHINE\\SOFTWARE\\DeletedKey]\n\n"
        "[HKEY_LOCAL_MACHINE\\SOFTWARE\\KeptKey]\n"
        '"Name"="Value"\n'
    )
    f = tmp_path / "snapshot.reg"
    f.write_text(content, encoding="utf-8")
    data = RegistryParser()._load_reg(str(f))
    assert "HKLM\\SOFTWARE\\DeletedKey" not in data
    assert "HKLM\\SOFTWARE\\KeptKey" in data


# JSON loading

def test_load_json_with_keys_wrapper(tmp_path):
    payload = {"keys": {"HKLM\\Foo": {"Bar": "Baz"}}}
    f = tmp_path / "snap.json"
    f.write_text(json.dumps(payload))
    assert RegistryParser()._load_json(str(f)) == {"HKLM\\Foo": {"Bar": "Baz"}}


def test_load_json_without_wrapper(tmp_path):
    payload = {"HKLM\\Foo": {"Bar": "Baz"}}
    f = tmp_path / "snap.json"
    f.write_text(json.dumps(payload))
    assert RegistryParser()._load_json(str(f)) == payload


# FTK CSV loading

def test_load_ftk_csv_standard_columns(tmp_path):
    content = (
        "Key Path,Value Name,Value Data\n"
        "HKLM\\Software\\Test,Setting,1\n"
        "HKLM\\Software\\Test,Other,Something\n"
    )
    f = tmp_path / "ftk.csv"
    f.write_text(content, encoding="utf-8")
    data = RegistryParser()._load_ftk_csv(str(f))
    assert data["HKLM\\Software\\Test"]["Setting"] == "1"
    assert data["HKLM\\Software\\Test"]["Other"] == "Something"


def test_load_ftk_csv_handles_alternative_column_names(tmp_path):
    # Different FTK versions use different column headers
    content = "Registry Key,Name,Data\nHKLM\\Foo,Bar,Baz\n"
    f = tmp_path / "ftk.csv"
    f.write_text(content, encoding="utf-8")
    data = RegistryParser()._load_ftk_csv(str(f))
    assert data["HKLM\\Foo"]["Bar"] == "Baz"


def test_load_ftk_csv_blank_value_name_becomes_default(tmp_path):
    content = "Key Path,Value Name,Value Data\nHKLM\\Software\\Test,,DefaultData\n"
    f = tmp_path / "ftk.csv"
    f.write_text(content, encoding="utf-8")
    data = RegistryParser()._load_ftk_csv(str(f))
    assert data["HKLM\\Software\\Test"]["(Default)"] == "DefaultData"


# load_file dispatch and hashing side effects

def test_load_file_unsupported_extension_raises(tmp_path):
    f = tmp_path / "snap.txt"
    f.write_text("whatever")
    with pytest.raises(ValueError, match="Unsupported format"):
        RegistryParser().load_file(str(f))


def test_load_file_without_case_id_sets_unchecked_status(tmp_path):
    payload = {"HKLM\\Foo": {"Bar": "Baz"}}
    f = tmp_path / "snap.json"
    f.write_text(json.dumps(payload))
    p = RegistryParser()
    p.load_file(str(f))
    assert p.last_hash_status == "unchecked"
    assert len(p.last_hash) == 64


def test_load_file_records_new_hash_then_verifies(tmp_path, sample_case):
    f = tmp_path / "snap.json"
    f.write_text(json.dumps({"HKLM\\Foo": {"Bar": "Baz"}}))

    p = RegistryParser()
    p.load_file(str(f), case_id=sample_case)
    assert p.last_hash_status == "new"

    # Loading the same file again should verify against the stored hash
    p.load_file(str(f), case_id=sample_case)
    assert p.last_hash_status == "verified"


def test_load_file_detects_hash_mismatch(tmp_path, sample_case):
    # ACPO Principle 2: evidence tampering must be flagged
    f = tmp_path / "snap.json"
    f.write_text(json.dumps({"HKLM\\Foo": {"A": "1"}}))

    p = RegistryParser()
    p.load_file(str(f), case_id=sample_case)
    assert p.last_hash_status == "new"

    # Tamper with the file contents while keeping the same filename
    f.write_text(json.dumps({"HKLM\\Foo": {"A": "2"}}))
    p.load_file(str(f), case_id=sample_case)
    assert p.last_hash_status == "mismatch"


# compare - the diff engine

def _write_snapshots(baseline, snapshot, tmp_path):
    b = tmp_path / "baseline.json"
    s = tmp_path / "snapshot.json"
    b.write_text(json.dumps(baseline))
    s.write_text(json.dumps(snapshot))
    return str(b), str(s)


def test_compare_detects_added_value(tmp_path):
    b, s = _write_snapshots(
        {"HKLM\\Software\\Test": {"Existing": "1"}},
        {"HKLM\\Software\\Test": {"Existing": "1", "NewValue": "2"}},
        tmp_path,
    )
    changes = RegistryParser().compare(b, s)
    added = [c for c in changes if c["change_type"] == "added"]
    assert len(added) == 1
    assert added[0]["value_name"] == "NewValue"
    assert added[0]["new_data"] == "2"
    assert added[0]["old_data"] == ""


def test_compare_detects_deleted_value(tmp_path):
    b, s = _write_snapshots(
        {"HKLM\\Software\\Test": {"Goner": "1"}},
        {"HKLM\\Software\\Test": {}},
        tmp_path,
    )
    changes = RegistryParser().compare(b, s)
    deleted = [c for c in changes if c["change_type"] == "deleted"]
    assert len(deleted) == 1
    assert deleted[0]["value_name"] == "Goner"
    assert deleted[0]["old_data"] == "1"
    assert deleted[0]["new_data"] == ""


def test_compare_detects_modified_value(tmp_path):
    b, s = _write_snapshots(
        {"HKLM\\Software\\Test": {"Setting": "old"}},
        {"HKLM\\Software\\Test": {"Setting": "new"}},
        tmp_path,
    )
    changes = RegistryParser().compare(b, s)
    modified = [c for c in changes if c["change_type"] == "modified"]
    assert len(modified) == 1
    assert modified[0]["old_data"] == "old"
    assert modified[0]["new_data"] == "new"


def test_compare_returns_empty_when_snapshots_identical(tmp_path):
    b, s = _write_snapshots(
        {"HKLM\\Software\\Test": {"Stable": "1"}},
        {"HKLM\\Software\\Test": {"Stable": "1"}},
        tmp_path,
    )
    assert RegistryParser().compare(b, s) == []


def test_compare_attaches_category_to_changes(tmp_path):
    run_key = "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    b, s = _write_snapshots(
        {run_key: {}},
        {run_key: {"malware": "C:\\evil.exe"}},
        tmp_path,
    )
    changes = RegistryParser().compare(b, s)
    assert len(changes) == 1
    assert changes[0]["category"] == "Persistence - Run Key"


def test_compare_detects_brand_new_key(tmp_path):
    b, s = _write_snapshots(
        {},
        {"HKLM\\Software\\BrandNew": {"Value": "1"}},
        tmp_path,
    )
    changes = RegistryParser().compare(b, s)
    assert len(changes) == 1
    assert changes[0]["change_type"] == "added"
    assert changes[0]["key_path"] == "HKLM\\Software\\BrandNew"