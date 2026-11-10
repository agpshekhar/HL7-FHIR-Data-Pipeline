"""Tests for reading the committed BMP sample into panels."""

from datetime import UTC, datetime, timedelta

from labpipe.lis.sample import ANALYTES, load_panels


def test_every_panel_in_the_sample_is_loaded():
    panels = load_panels()
    assert len(panels) == 1331
    assert all(len(p.results) == 8 for p in panels)
    assert len({p.patient.mrn for p in panels}) == 12


def test_accessions_follow_collection_time():
    panels = load_panels()
    assert [p.accession for p in panels[:2]] == ["BMP000001", "BMP000002"]
    assert panels[-1].accession == "BMP001331"
    times = [p.collected_at for p in panels]
    assert times == sorted(times)
    assert len({p.accession for p in panels}) == len(panels)


def test_identifiers_are_the_same_on_every_load():
    first = [(p.accession, p.patient.mrn) for p in load_panels()]
    second = [(p.accession, p.patient.mrn) for p in load_panels()]
    assert first == second


def test_first_panel_details():
    panel = load_panels()[0]
    assert panel.patient.mrn == "100007"
    assert panel.patient.family == "Ruecker817"
    assert panel.collected_at == datetime(1984, 10, 30, 8, 42, 48, tzinfo=UTC)
    assert panel.resulted_at - panel.collected_at == timedelta(minutes=45)
    assert [r.loinc for r in panel.results] == list(ANALYTES)
    assert panel.results[0].value == "139.9"  # text, exactly as Synthea wrote it
