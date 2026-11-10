"""Tests for scripts/build_vocab_subset.py, run against a tiny stand-in Athena download."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
ATHENA = FIXTURES / "athena_mini"
SAMPLE = FIXTURES / "sample_mini"

_spec = importlib.util.spec_from_file_location(
    "build_vocab_subset", ROOT / "scripts" / "build_vocab_subset.py"
)
subset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(subset)


def build_into(out: Path) -> dict[str, str]:
    assert subset.main(["--athena", str(ATHENA), "--sample", str(SAMPLE), "--out", str(out)]) == 0
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(out.iterdir())}


def concept_ids(out: Path) -> set[int]:
    lines = (out / "CONCEPT.csv").read_text(encoding="utf-8").splitlines()[1:]
    return {int(line.split("\t")[0]) for line in lines}


def test_rerun_is_byte_identical(tmp_path):
    assert build_into(tmp_path / "a") == build_into(tmp_path / "b")


def test_writes_all_six_tables(tmp_path):
    files = build_into(tmp_path)
    assert set(files) == {f"{name}.csv" for name in subset.TABLES}


def test_includes_seeds_fixed_concepts_and_maps_to_targets(tmp_path):
    build_into(tmp_path)
    ids = concept_ids(tmp_path)
    assert {900001, 900003, 8840, 8753} <= ids  # sample codes and units
    assert 900002 in ids  # what the retired code 9999-9 maps to
    assert subset.FIXED_CONCEPT_IDS <= ids


def test_leaves_out_unused_and_snomed_concepts(tmp_path):
    build_into(tmp_path)
    ids = concept_ids(tmp_path)
    assert 900004 not in ids  # a LOINC code the sample never uses
    assert 900005 not in ids  # SNOMED, reachable only through a dead "Maps to" row


def test_every_metadata_reference_resolves(tmp_path):
    build_into(tmp_path)
    ids = concept_ids(tmp_path)
    for name, column in [
        ("DOMAIN", "domain_concept_id"),
        ("VOCABULARY", "vocabulary_concept_id"),
        ("CONCEPT_CLASS", "concept_class_concept_id"),
        ("RELATIONSHIP", "relationship_concept_id"),
    ]:
        header, *rows = (tmp_path / f"{name}.csv").read_text(encoding="utf-8").splitlines()
        col = header.split("\t").index(column)
        assert {int(r.split("\t")[col]) for r in rows} <= ids, name


def test_unknown_code_stops_the_build(tmp_path):
    sample = tmp_path / "sample"
    sample.mkdir()
    (sample / "bmp_results.csv").write_text(
        "patient_id,collected_at,loinc,value,unit\np1,2024-01-01T08:00:00Z,0000-0,1,mg/dL\n"
    )
    with pytest.raises(subset.SubsetError, match="0000-0"):
        subset.build(ATHENA, sample)
