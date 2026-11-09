# HL7-FHIR-Data-Pipeline

**An interoperability bridge from hospital lab messaging to research-ready data.**

A lab result starts life as an HL7 v2 message, is shared through FHIR APIs, and is analyzed in OMOP research databases. Each hop crosses a different standard, and each is a place where data quietly breaks: duplicate messages, corrections that arrive out of order, codes that never get mapped. This pipeline carries synthetic basic metabolic panel (BMP) results across all three standards, through an interface engine, and proves with automated tests that every result arrives intact.

> **Status:** Phase 1 of 16, in progress. See the [roadmap](#roadmap).
>
> **All data is synthetic,** generated with [Synthea](https://synthetichealth.github.io/synthea/). No real patient data is used anywhere in this project.

## How it works

1. **Mock LIS.** A mock laboratory information system builds one HL7 v2.5.1 `ORU^R01` message per BMP panel from a seeded Synthea sample and sends it over MLLP, the way a real lab system does.
2. **BridgeLink channel.** An interface engine channel validates each message. Good messages get an ACK (`AA`) and are written to a Postgres staging table. Bad messages get a NAK (`AE` or `AR`) with the reason and go to an error queue.
3. **Hop 1: structure (HL7 v2 to FHIR R4).** Each staged message is parsed into a canonical `LabResult` model, then built into one FHIR transaction bundle per panel (Patient, Specimen, DiagnosticReport, Observations). Resource IDs are UUIDv5 values derived from business keys, so a resend or replay never creates a duplicate. Hop 1 changes only the shape of the data. It never looks up a vocabulary or touches OMOP.
4. **Hop 2: meaning (FHIR to OMOP CDM 5.4).** Hop 2 reads only the FHIR output. It maps codes through the OHDSI Athena vocabularies (LOINC for tests, UCUM for units), follows "Maps to" relationships, and lets each standard concept's domain decide the OMOP table. It loads PERSON and MEASUREMENT, keeps source values and source concept IDs, and records every FHIR ID in a crosswalk with a stable OMOP ID.
5. **Proof.** A round-trip test checks every result against the Synthea source (same value, unit and collection time, nothing lost, nothing invented). A replay test feeds the pipeline a shuffled, duplicated feed with early corrections and asserts the OMOP tables match a clean run exactly.

```
Seeded Synthea BMP sample
  → Mock LIS sends ORU^R01 over MLLP
  → BridgeLink channel: validate, ACK or NAK (rejects to the error queue)
  → Postgres staging: every raw message kept, unique on MSH-10
  → Hop 1 (structure): parse to LabResult → FHIR R4 bundle per panel, UUIDv5 IDs
  → Hop 2 (meaning): LOINC/UCUM lookup → route by concept domain → OMOP CDM 5.4
  → Tests and run report: round trip, replay determinism
```

<!-- TODO: Add the diagram to docs/architecture.md and embed it here (Phase 13). -->

## Quickstart

<!-- TODO: Replace with the one-command run once the Docker stack is in (Phase 2). -->

Target:

```bash
git clone https://github.com/agpshekhar/HL7-FHIR-Data-Pipeline.git
cd HL7-FHIR-Data-Pipeline
docker compose up --build
```

For now:

```bash
git clone https://github.com/agpshekhar/HL7-FHIR-Data-Pipeline.git
cd HL7-FHIR-Data-Pipeline
uv sync
```

A minimal LOINC/UCUM vocabulary subset will ship with the repo, so the default stack runs on any clone. A full OHDSI Athena bundle can be mounted into `data/vocab/` (gitignored) if you want it.

## Worked example

<!-- TODO: One lab result shown three ways, side by side:
the HL7 v2 OBX segment, its FHIR Observation, and its OMOP MEASUREMENT row. -->

_Coming in Phase 6._

## Tech stack

| Layer | Tool |
| --- | --- |
| Language | Python, with a `labpipe` command-line tool that runs every job |
| Synthetic patients | Synthea (seeded BMP sample committed to the repo) |
| HL7 v2 messaging | hl7apy, MLLP |
| Interface engine | BridgeLink (open-source Mirth Connect fork) |
| FHIR models | fhir.resources (R4B, targeting FHIR R4) |
| Database | Postgres 16 (staging, error queue, crosswalk, OMOP) |
| Target data model | OMOP CDM 5.4 with OHDSI Athena vocabularies (LOINC, UCUM) |
| Containers | Docker Compose, one command |
| CI | GitHub Actions, running the same Compose stack |
| Dashboard | Streamlit |
| FHIR server (stretch goal) | Blaze |

## Data quality approach

<!-- TODO: Link the tests and the run report once they exist (Phase 12). -->

- **Fix what's provable, flag what isn't.** Local codes and unit spellings are mapped through vocabularies. A missing unit or an unmapped code is flagged and counted, never guessed.
- **Ground truth.** Synthea is the source of truth, so the round-trip test checks every result end to end, counting in both directions.
- **Messy feeds on purpose.** The mock LIS injects realistic problems (local codes, unit variants, missing units, censored values, hemolyzed specimens, duplicates, corrections, out-of-order arrivals, malformed messages) and logs each one as an answer key.
- **Corrections and ordering.** A correction updates the same business key in place, and the newest result time wins, so a late original is ignored.
- **Consistency checks.** Every result is checked for collection before resulting, abnormal flag versus reference range, a valid UCUM unit, and a present patient and specimen.
- **Replay determinism.** A shuffled, duplicated feed with early corrections must produce exactly the same OMOP output as a clean one.

## Design decisions and trade-offs

<!-- TODO: One ADR per decision in docs/adr/. -->

Planned decision records:

- Two independent hops, with Hop 2 reading only FHIR
- BridgeLink channel in front of staging, with code mapping kept in Hop 2
- Postgres staging as a durable queue instead of a message broker
- A canonical `LabResult` model inside Hop 1
- Deterministic UUIDv5 IDs from business keys, with upsert semantics
- Corrections and ordering: the newest result time wins
- OMOP destination chosen by concept domain, not by resource type
- Foreign keys kept on, made deferrable, one transaction per load
- Hop 2 as a full rebuild every run, with stable IDs from the crosswalk
- FHIR R4B library targeting R4, and the US Core trade-off for local codes
- A committed minimal vocabulary subset, with full Athena optional
- hl7apy for strict parsing, revisited if it rejects too much messy input

## Roadmap

The work runs in 16 phases, each closed when its done-when check passes. Gate reviews follow Phases 6, 8, 12 and 16.

**Milestone 1: walking skeleton (Phases 1–6)**

- [ ] Phase 1: Athena vocabulary request, `labpipe` CLI skeleton, LICENSE and SOURCES.md, pre-commit with ruff and gitleaks
- [ ] Phase 2: app image, Postgres and migrations (staging, error queue, crosswalk, OMOP 5.4, deferrable FKs), CI runs Compose
- [ ] Phase 3: seeded Synthea BMP extract and vocabulary subset
- [ ] Phase 4: mock LIS writing ORU^R01 messages into staging
- [ ] Phase 5: Hop 1, HL7 v2 to FHIR R4 with UUIDv5 IDs
- [ ] Phase 6: Hop 2, FHIR to OMOP, with the round-trip test. **Gate: Milestone 1**

**Milestone 2: interface engine and messy data (Phases 7–12)**

- [ ] Phase 7: BridgeLink in Compose, MLLP channel with ACK
- [ ] Phase 8: validation, NAK and error queue, interface spec, tag v0.1. **Gate: v0.1**
- [ ] Phase 9: mess injection log, local codes and unit variants
- [ ] Phase 10: missing units, censored values, hemolysis, corrections and ordering
- [ ] Phase 11: replay determinism test
- [ ] Phase 12: run report (HTML and JSON) and ADRs. **Gate: Milestone 2**

**Milestone 3: ship it (Phases 13–16)**

- [ ] Phase 13: Streamlit dashboard, architecture, mapping and interface specs
- [ ] Phase 14: final README, Makefile, badges, mypy, fresh-clone test
- [ ] Phase 15: demo video and final read-through of the docs (Blaze only if ahead)
- [ ] Phase 16: tag v1.0. **Gate: v1.0**

## Out of scope

The ASTM analyzer and middleware layer, the order loop (ORM/OML), ADT and patient merges, SMART on FHIR apps, and machine learning on OMOP.

## At production scale

<!-- TODO: Expand once Milestone 2 is done. -->

What a production version would add: highly available MLLP listeners, incremental loads instead of full rebuilds, monitoring and alerting on the error queue, PHI security controls, transformation tooling such as dbt, workflow orchestration, and cloud deployment.

## Demo

<!-- TODO: Link the demo video (Phase 15). -->

_Coming in Phase 15._
