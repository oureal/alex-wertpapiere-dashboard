from pathlib import Path

from scripts.extract_legacy_data import extract


ROOT = Path(__file__).resolve().parents[1]


def test_saved_reference_is_exact_data_literal_from_archived_2026_08_21_dashboard():
    source = ROOT / "dashboard/history/2026-08-21-full-market-update.html"
    expected = extract(source.read_bytes())
    assert (ROOT / "data/legacy/index-data-2026-08-21.json").read_bytes() == expected
