"""Build the minimal OMOP vocabulary subset that ships with the repo.

Reads the full OHDSI Athena download in data/vocab/ (gitignored) and writes only
the rows the pipeline needs to db/vocab_subset/, in the same tab-separated
Athena format, so one loader handles both the subset and a full bundle.

What goes in:

1. Seeds: every LOINC code and UCUM unit in data/sample/bmp_results.csv, plus a
   few fixed concepts the OMOP load needs (concept 0, the gender concepts and the
   type concepts).
2. Their "Maps to" targets, and the matching "Maps to" / "Mapped from" rows.
3. The closure: every domain, vocabulary, concept class and relationship those
   rows name, and the concept behind each of those, repeated until nothing new
   turns up. Without this, the foreign keys in cdm.* would reject the load.

SNOMED is never allowed in. Every seed must exist and map to a standard concept,
or the script stops: it never guesses.

Rerunning the script on the same inputs produces byte-identical files.

Usage: uv run python scripts/build_vocab_subset.py [--athena DIR] [--sample DIR] [--out DIR]
"""

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Concepts the OMOP load uses that do not come from the sample's codes.
FIXED_CONCEPT_IDS = {
    0,  # No matching concept: OMOP's value for "unmapped" (race, ethnicity, ...)
    8507,  # MALE (Gender)
    8532,  # FEMALE (Gender)
    32817,  # EHR (Type Concept): observation_period.period_type_concept_id
    32856,  # Lab (Type Concept): measurement.measurement_type_concept_id
}
RELATIONSHIPS = ("Maps to", "Mapped from")
BANNED_VOCABULARIES = {"SNOMED"}

TABLES = [
    "CONCEPT",
    "CONCEPT_RELATIONSHIP",
    "DOMAIN",
    "VOCABULARY",
    "CONCEPT_CLASS",
    "RELATIONSHIP",
]


class SubsetError(Exception):
    """Something in the inputs cannot be proven, so the subset is not written."""


def read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return f.readline().rstrip("\r\n").split("\t")


def read_rows(path: Path):
    """Yield each row of an Athena file as a dict: tab-separated, no quoting.

    Fields are kept as the exact text in the file, so the output matches it byte for byte.
    """
    with path.open(encoding="utf-8", newline="") as f:
        header = f.readline().rstrip("\r\n").split("\t")
        for line in f:
            line = line.rstrip("\r\n")
            if line:
                yield dict(zip(header, line.split("\t"), strict=True))


def read_table(path: Path, key: str) -> dict[str, dict]:
    """Read a small Athena table into memory, keyed by its id column."""
    return {row[key]: row for row in read_rows(path)}


def sample_seeds(sample_dir: Path) -> set[tuple[str, str]]:
    """The (vocabulary_id, concept_code) pairs the sample uses."""
    seeds = set()
    with (sample_dir / "bmp_results.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seeds.add(("LOINC", row["loinc"]))
            seeds.add(("UCUM", row["unit"]))
    return seeds


def scan_concepts(path: Path, ids: set[int], codes: set[tuple[str, str]] = frozenset()):
    """One pass over CONCEPT.csv: return {concept_id: row} for rows matching an id or a code."""
    found = {}
    for row in read_rows(path):
        if int(row["concept_id"]) in ids or (row["vocabulary_id"], row["concept_code"]) in codes:
            found[int(row["concept_id"])] = row
    return found


def build(athena: Path, sample: Path) -> dict[str, list[dict]]:
    seeds = sample_seeds(sample)

    # 1. Seeds and fixed concepts.
    concepts = scan_concepts(athena / "CONCEPT.csv", FIXED_CONCEPT_IDS, seeds)
    found = {(r["vocabulary_id"], r["concept_code"]) for r in concepts.values()}
    missing = sorted(seeds - found) + sorted(FIXED_CONCEPT_IDS - concepts.keys())
    if missing:
        raise SubsetError(f"not in CONCEPT.csv: {missing}")
    seed_ids = {
        cid for cid, r in concepts.items() if (r["vocabulary_id"], r["concept_code"]) in seeds
    }

    # 2. "Maps to" for each seed (a standard concept maps to itself), and the reverse rows.
    candidates = []
    for row in read_rows(athena / "CONCEPT_RELATIONSHIP.csv"):
        if row["relationship_id"] in RELATIONSHIPS and not row["invalid_reason"]:
            if int(row["concept_id_1"]) in seed_ids or int(row["concept_id_2"]) in seed_ids:
                candidates.append(row)
    maps_to = {}
    for row in candidates:
        if row["relationship_id"] == "Maps to" and int(row["concept_id_1"]) in seed_ids:
            maps_to.setdefault(int(row["concept_id_1"]), set()).add(int(row["concept_id_2"]))
    unmapped = sorted(concepts[c]["concept_code"] for c in seed_ids if c not in maps_to)
    if unmapped:
        raise SubsetError(f"no 'Maps to' row for: {unmapped}")

    # 3. The closure over the metadata tables.
    domains = read_table(athena / "DOMAIN.csv", "domain_id")
    vocabs = read_table(athena / "VOCABULARY.csv", "vocabulary_id")
    classes = read_table(athena / "CONCEPT_CLASS.csv", "concept_class_id")
    rels = read_table(athena / "RELATIONSHIP.csv", "relationship_id")

    wanted = set(concepts) | {t for targets in maps_to.values() for t in targets}
    while True:
        new = wanted - concepts.keys()
        if new:
            more = scan_concepts(athena / "CONCEPT.csv", new)
            if new - more.keys():
                raise SubsetError(f"concept ids not in CONCEPT.csv: {sorted(new - more.keys())}")
            concepts.update(more)
        refs = set()
        for r in concepts.values():
            refs.add(int(domains[r["domain_id"]]["domain_concept_id"]))
            refs.add(int(vocabs[r["vocabulary_id"]]["vocabulary_concept_id"]))
            refs.add(int(classes[r["concept_class_id"]]["concept_class_concept_id"]))
        refs |= {int(rels[name]["relationship_concept_id"]) for name in RELATIONSHIPS}
        if refs <= concepts.keys():
            break
        wanted |= refs

    for cid in seed_ids:
        for target in maps_to[cid]:
            if concepts[target]["standard_concept"] != "S":
                raise SubsetError(f"concept {cid} maps to non-standard concept {target}")
    banned = sorted({r["vocabulary_id"] for r in concepts.values()} & BANNED_VOCABULARIES)
    if banned:
        raise SubsetError(f"banned vocabularies pulled in: {banned}")

    kept_rels = [
        r
        for r in candidates
        if int(r["concept_id_1"]) in concepts and int(r["concept_id_2"]) in concepts
    ]

    def used(field: str) -> set[str]:
        return {r[field] for r in concepts.values()}

    return {
        "CONCEPT": sorted(concepts.values(), key=lambda r: int(r["concept_id"])),
        "CONCEPT_RELATIONSHIP": sorted(
            kept_rels,
            key=lambda r: (int(r["concept_id_1"]), int(r["concept_id_2"]), r["relationship_id"]),
        ),
        "DOMAIN": [domains[k] for k in sorted(used("domain_id"))],
        "VOCABULARY": [vocabs[k] for k in sorted(used("vocabulary_id"))],
        "CONCEPT_CLASS": [classes[k] for k in sorted(used("concept_class_id"))],
        "RELATIONSHIP": [rels[k] for k in sorted(RELATIONSHIPS)],
    }


def write(athena: Path, out: Path, tables: dict[str, list[dict]]) -> None:
    """Write each table with the same header (column order) as the Athena file it came from."""
    out.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        header = read_header(athena / f"{name}.csv")
        lines = ["\t".join(header)] + ["\t".join(row[h] for h in header) for row in tables[name]]
        (out / f"{name}.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--athena", type=Path, default=ROOT / "data/vocab")
    parser.add_argument("--sample", type=Path, default=ROOT / "data/sample")
    parser.add_argument("--out", type=Path, default=ROOT / "db/vocab_subset")
    args = parser.parse_args(argv)

    try:
        tables = build(args.athena, args.sample)
    except SubsetError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    write(args.athena, args.out, tables)
    for name in TABLES:
        print(f"{name}: {len(tables[name])} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
