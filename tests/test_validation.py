import csv
import json
from pathlib import Path

from scripts.validate_data import build_report, valid_isin


ROOT = Path(__file__).resolve().parents[1]


def read_csv(name):
    with (ROOT / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_validation_has_no_hard_failures_and_records_legacy_warnings():
    report = build_report()
    assert report["overall_status"] == "pass"
    assert all(check["status"] == "pass" for check in report["checks"])
    warning_ids = {item["id"] for item in report["known_legacy_inconsistencies"]}
    assert "assets_total_differs_from_meta_total" in warning_ids
    assert "asset_direct_differs_from_meta_direct" in warning_ids
    assert all(not item["corrected"] for item in report["known_legacy_inconsistencies"])


def test_isin_check_digit_validation():
    assert valid_isin("DE000ENER6Y0")
    assert valid_isin("US0846707026")
    assert not valid_isin("DE000ENER6Y1")


def test_siemens_energy_purchase_is_cash_neutral_and_has_four_shares():
    transactions = read_csv("data/portfolio/transactions.csv")
    transaction = next(item for item in transactions if item["instrument_id"] == "siemens-energy")
    assert transaction["type"] == "BUY"
    assert float(transaction["quantity"]) == 4
    assert float(transaction["price"]) == 154.04
    assert float(transaction["gross_value_eur"]) + float(transaction["cash_effect_eur"]) == 0
    assert transaction["depot"] == "Depot 2"
    assert transaction["needs_confirmation"] == "false"
    assert "user-confirmed" in transaction["provenance"]


def test_holdings_retain_two_separate_depots():
    holdings = read_csv("data/portfolio/holdings.csv")
    assert {item["depot"] for item in holdings} == {"Depot 1", "Depot 2"}
    by_instrument = {item["instrument_id"]: item for item in holdings}
    assert by_instrument["siemens-energy"]["depot"] == by_instrument["broadcom"]["depot"]


def test_confirmed_quantities_and_identifiers_are_complete():
    confirmed = {
        "xetra-gold": ("62", "DE000A0S9GB0", "A0S9GB"),
        "boerse-de-aktienfonds": ("164", "LU2115464500", "A2PZMR"),
        "ishares-global-titans-50": ("121", "DE0006289382", "628938"),
        "boerse-de-technologiefonds": ("32", "LU2479335734", "TMG4TT"),
        "ishares-core-msci-world": ("27", "IE00B4L5Y983", "A0RPWH"),
        "ishares-msci-world-value-factor": ("17", "IE00BP3QZB59", "A12ATG"),
        "wisdomtree-physical-bitcoin": ("60", "GB00BJYDH287", "A3GKGK"),
        "marvell-technology": ("4", "US5738741041", "A3CNLD"),
        "broadcom": ("2", "US11135F1012", "A2JG9Z"),
    }
    holdings = {item["instrument_id"]: item for item in read_csv("data/portfolio/holdings.csv")}
    instruments = {
        item["id"]: item
        for item in json.loads((ROOT / "data/portfolio/instruments.yml").read_text())["instruments"]
    }
    for instrument_id, (quantity, isin, wkn) in confirmed.items():
        assert holdings[instrument_id]["quantity"] == quantity
        assert instruments[instrument_id]["isin"] == isin
        assert instruments[instrument_id]["wkn"] == wkn
        assert instruments[instrument_id]["ticker"] is None
        assert instruments[instrument_id]["exchange"] is None
        assert instruments[instrument_id]["price_source"] is None


def test_legacy_unit_price_plausibility_is_reported():
    report = build_report()
    assert report["legacy_value_plausibility"]
    assert all(item["status"] == "plausible" for item in report["legacy_value_plausibility"])
