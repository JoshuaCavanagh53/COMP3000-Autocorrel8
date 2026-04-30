import pytest

from autocorrel8Main.app.hashing import sha256_file


def test_sha256_is_deterministic(tmp_path):
    f = tmp_path / "evidence.bin"
    f.write_bytes(b"hello world")
    assert sha256_file(f) == sha256_file(f)


def test_identical_files_produce_identical_hashes(tmp_path):
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"registry snapshot content")
    f2.write_bytes(b"registry snapshot content")
    assert sha256_file(f1) == sha256_file(f2)


def test_single_byte_change_alters_hash(tmp_path):
    # ACPO Principle 2: any alteration of evidence must be detectable
    f1 = tmp_path / "a.bin"
    f2 = tmp_path / "b.bin"
    f1.write_bytes(b"hello world")
    f2.write_bytes(b"hello worlD")
    assert sha256_file(f1) != sha256_file(f2)


def test_empty_file_matches_known_value(tmp_path):
    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256_file(f) == expected


def test_hello_world_matches_known_value(tmp_path):
    f = tmp_path / "hw.bin"
    f.write_bytes(b"hello world")
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert sha256_file(f) == expected


def test_hash_is_64_lowercase_hex_chars(tmp_path):
    f = tmp_path / "some.bin"
    f.write_bytes(b"anything")
    digest = sha256_file(f)
    assert len(digest) == 64
    int(digest, 16)  # parseable as hex
    assert digest == digest.lower()


def test_file_larger_than_chunk_size_hashed_correctly(tmp_path):
    # Verifies the iter(lambda: f.read(8192)) loop covers all bytes
    f = tmp_path / "big.bin"
    f.write_bytes(b"A" * 100_000)
    expected = "e6631225e83d23bf67657e85109ad5deb3570e1405d7aaa23a2485ae8582c143"
    assert sha256_file(f) == expected


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        sha256_file(tmp_path / "does_not_exist.bin")