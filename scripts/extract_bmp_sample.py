"""Extract the basic metabolic panel (BMP) results from a Synthea CSV export.

Reads observations.csv and patients.csv from a Synthea run and writes three small,
sorted files to data/sample/. They line up with the HL7 v2 segments the mock LIS
will build in Phase 4:

- patients.csv     (PID) the patients with at least one panel, needed columns only
- bmp_panels.csv   (OBR) one row per panel: patient, collection time, encounter
- bmp_results.csv  (OBX) one row per analyte, eight per panel

A panel is the eight Serum/Plasma analytes Synthea reports under "Basic metabolic
2000 panel - Serum or Plasma" (LOINC 24321-2), sharing one patient, encounter and
collection time. Synthea also attaches a calculated eGFR (33914-3) to that panel;
it is not one of the eight measured analytes, so it is left out. A comprehensive
metabolic panel (CMP, 24323-8) reports the same eight codes plus liver tests; those
draws are CMPs, not BMPs, so they are left out too.
Values are copied as text, exactly as Synthea wrote them, so the round-trip test
can compare them character for character.

Rerunning the script on the same export produces byte-identical files.

Usage: uv run python scripts/extract_bmp_sample.py [--synthea DIR] [--out DIR]
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# LOINC 24321-2 "Basic metabolic 2000 panel - Serum or Plasma": its eight measured analytes.
BMP_CODES = {
    "2345-7": "Glucose [Mass/volume] in Serum or Plasma",
    "3094-0": "Urea nitrogen [Mass/volume] in Serum or Plasma",
    "2160-0": "Creatinine [Mass/volume] in Serum or Plasma",
    "17861-6": "Calcium [Mass/volume] in Serum or Plasma",
    "2951-2": "Sodium [Moles/volume] in Serum or Plasma",
    "2823-3": "Potassium [Moles/volume] in Serum or Plasma",
    "2075-0": "Chloride [Moles/volume] in Serum or Plasma",
    "2028-9": "Carbon dioxide, total [Moles/volume] in Serum or Plasma",
}

# Analytes only a CMP (24323-8) adds on top of the BMP. Seeing any of them at the same
# patient, encounter and time means the draw was a CMP.
CMP_ONLY_CODES = {
    "2885-2",  # Protein
    "1751-7",  # Albumin
    "1975-2",  # Bilirubin, total
    "6768-6",  # Alkaline phosphatase
    "1742-6",  # ALT
    "1920-8",  # AST
    "10834-0",  # Globulin
}

PANEL_COLUMNS = ["patient_id", "collected_at", "encounter_id"]
RESULT_COLUMNS = ["patient_id", "collected_at", "loinc", "value", "unit"]
PATIENT_COLUMNS = ["patient_id", "birthdate", "deathdate", "gender", "given", "family"]


def read_panels(observations: Path) -> dict[tuple, dict[str, set]]:
    """Group BMP rows into panels: (patient, encounter, time) -> {loinc: {(value, unit)}}."""
    panels: dict[tuple, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    with observations.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["CODE"] in BMP_CODES or row["CODE"] in CMP_ONLY_CODES:
                key = (row["PATIENT"], row["ENCOUNTER"], row["DATE"])
                panels[key][row["CODE"]].add((row["VALUE"], row["UNITS"]))
    return panels


def keep_complete(panels: dict[tuple, dict[str, set]]) -> tuple[list, list, list, int]:
    """Return (panel rows, result rows, rejected panel keys, number of CMPs skipped).

    A draw that includes any CMP-only analyte is a CMP and is skipped.
    A panel is kept only if it has all eight codes and exactly one value for each.
    Two different values for the same code at the same moment means two draws
    were recorded on top of each other; we cannot tell them apart, so the whole
    panel is left out and reported rather than guessed at.
    """
    panel_rows, result_rows, rejected, cmps = [], [], [], 0
    for (patient, encounter, collected_at), codes in panels.items():
        if set(codes) & CMP_ONLY_CODES:
            cmps += bool(set(codes) & BMP_CODES.keys())  # liver-only draws aren't counted
            continue
        if set(codes) != set(BMP_CODES) or any(len(v) != 1 for v in codes.values()):
            rejected.append((patient, collected_at))
            continue
        panel_rows.append([patient, collected_at, encounter])
        for loinc, values in codes.items():
            (value, unit) = next(iter(values))
            result_rows.append([patient, collected_at, loinc, value, unit])
    return sorted(panel_rows), sorted(result_rows), sorted(rejected), cmps


def read_patients(patients_csv: Path, wanted: set[str]) -> list[list[str]]:
    rows = []
    with patients_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Id"] in wanted:
                rows.append(
                    [
                        row["Id"],
                        row["BIRTHDATE"],
                        row["DEATHDATE"],
                        row["GENDER"],
                        row["FIRST"],
                        row["LAST"],
                    ]
                )
    return sorted(rows)


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    # lineterminator="\n" so the file is the same on macOS, Linux and in CI.
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--synthea", type=Path, default=ROOT / "data/synthea/csv")
    parser.add_argument("--out", type=Path, default=ROOT / "data/sample")
    args = parser.parse_args(argv)

    observations = args.synthea / "observations.csv"
    panels, results, rejected, cmps = keep_complete(read_panels(observations))
    patients = read_patients(args.synthea / "patients.csv", {p[0] for p in panels})

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "patients.csv", PATIENT_COLUMNS, patients)
    write_csv(args.out / "bmp_panels.csv", PANEL_COLUMNS, panels)
    write_csv(args.out / "bmp_results.csv", RESULT_COLUMNS, results)

    print(f"{len(patients)} patients, {len(panels)} panels, {len(results)} results")
    print(f"left out {cmps} comprehensive metabolic panels (CMP), which are not BMPs")
    for patient, collected_at in rejected:
        print(f"left out (incomplete or conflicting): patient={patient} time={collected_at}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
