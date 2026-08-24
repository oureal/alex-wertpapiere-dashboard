from pathlib import Path

from scripts.extract_legacy_data import extract


ROOT = Path(__file__).resolve().parents[1]


def test_saved_reference_is_exact_data_literal_from_index():
    expected = extract((ROOT / "index.html").read_bytes())
    assert (ROOT / "data/legacy/index-data-2026-08-21.json").read_bytes() == expected
