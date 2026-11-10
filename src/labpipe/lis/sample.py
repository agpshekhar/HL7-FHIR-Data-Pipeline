"""Read the committed BMP sample and turn it into panels the mock LIS can send.

The three files in data/sample/ line up with the HL7 v2 segments of one ORU^R01:

- patients.csv    -> PID  (one row per patient)
- bmp_panels.csv  -> PV1, ORC, OBR and SPM  (one row per panel)
- bmp_results.csv -> OBX  (eight rows per panel)

This module joins them into Panel objects and assigns the identifiers a real lab
system would own: a medical record number (MRN) per patient and an accession number
per panel. Synthea has neither, so they are assigned here, deterministically:

- MRN: patients sorted by Synthea patient_id, numbered from 100001.
- Accession: panels sorted by collection time (then patient), numbered BMP000001 up.

Because the sample is committed and sorted, every run assigns the same numbers.
"""

import csv
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

DEFAULT_DIR = Path("data/sample")

# LOINC for "Basic metabolic 2000 panel - Serum or Plasma", the ordered test (OBR-4).
PANEL_LOINC = "24321-2"
PANEL_NAME = "Basic metabolic 2000 panel - Serum or Plasma"

# The eight analytes in the order a BMP report usually lists them (OBX-1 follows this).
ANALYTES = {
    "2951-2": "Sodium [Moles/volume] in Serum or Plasma",
    "2823-3": "Potassium [Moles/volume] in Serum or Plasma",
    "2075-0": "Chloride [Moles/volume] in Serum or Plasma",
    "2028-9": "Carbon dioxide, total [Moles/volume] in Serum or Plasma",
    "3094-0": "Urea nitrogen [Mass/volume] in Serum or Plasma",
    "2160-0": "Creatinine [Mass/volume] in Serum or Plasma",
    "2345-7": "Glucose [Mass/volume] in Serum or Plasma",
    "17861-6": "Calcium [Mass/volume] in Serum or Plasma",
}

# Synthea records only the collection time. A real analyzer reports a little later,
# so the mock LIS stamps every result a fixed 45 minutes after collection.
# Fixed, not random, so every run builds byte-identical messages.
RESULT_DELAY = timedelta(minutes=45)

FIRST_MRN = 100001


@dataclass(frozen=True)
class Patient:
    patient_id: str  # Synthea UUID; never sent in a message, kept to trace back to the source
    mrn: str
    family: str
    given: str
    birthdate: date
    gender: str  # "M" or "F", as Synthea writes it
    deathdate: date | None


@dataclass(frozen=True)
class Result:
    loinc: str
    name: str
    value: str  # text, exactly as Synthea wrote it ("136.9", never 136.9)
    unit: str  # UCUM, as Synthea wrote it


@dataclass(frozen=True)
class Panel:
    accession: str
    patient: Patient
    encounter_id: str
    collected_at: datetime  # timezone-aware, UTC
    results: tuple[Result, ...]  # in ANALYTES order

    @property
    def resulted_at(self) -> datetime:
        return self.collected_at + RESULT_DELAY


def sample_dir() -> Path:
    """Where the sample lives: LABPIPE_SAMPLE_DIR, or data/sample."""
    return Path(os.environ.get("LABPIPE_SAMPLE_DIR", DEFAULT_DIR))


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _utc(text: str) -> datetime:
    """Parse Synthea's '2016-10-23T00:26:54Z' into an aware UTC datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def load_patients(directory: Path) -> dict[str, Patient]:
    """patient_id -> Patient, with MRNs assigned in patient_id order."""
    rows = sorted(_read(directory / "patients.csv"), key=lambda r: r["patient_id"])
    patients = {}
    for number, row in enumerate(rows, start=FIRST_MRN):
        patients[row["patient_id"]] = Patient(
            patient_id=row["patient_id"],
            mrn=str(number),
            family=row["family"],
            given=row["given"],
            birthdate=date.fromisoformat(row["birthdate"]),
            gender=row["gender"],
            deathdate=date.fromisoformat(row["deathdate"]) if row["deathdate"] else None,
        )
    return patients


def load_panels(directory: Path | None = None) -> list[Panel]:
    """Every panel in the sample, in accession order, each with its eight results."""
    directory = directory or sample_dir()
    patients = load_patients(directory)

    results: dict[tuple[str, str], dict[str, Result]] = {}
    for row in _read(directory / "bmp_results.csv"):
        key = (row["patient_id"], row["collected_at"])
        results.setdefault(key, {})[row["loinc"]] = Result(
            loinc=row["loinc"], name=ANALYTES[row["loinc"]], value=row["value"], unit=row["unit"]
        )

    rows = sorted(
        _read(directory / "bmp_panels.csv"), key=lambda r: (r["collected_at"], r["patient_id"])
    )
    panels = []
    for number, row in enumerate(rows, start=1):
        by_code = results[(row["patient_id"], row["collected_at"])]
        if set(by_code) != set(ANALYTES):
            raise ValueError(f"panel {row['patient_id']} {row['collected_at']} is incomplete")
        panels.append(
            Panel(
                accession=f"BMP{number:06d}",
                patient=patients[row["patient_id"]],
                encounter_id=row["encounter_id"],
                collected_at=_utc(row["collected_at"]),
                results=tuple(by_code[code] for code in ANALYTES),
            )
        )
    return panels
