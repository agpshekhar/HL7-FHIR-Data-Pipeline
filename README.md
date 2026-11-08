# HL7-FHIR-Data-Pipeline

**An interoperability bridge from hospital lab messaging to research-ready data.**

A lab result starts life as an HL7 v2 message, is shared through FHIR APIs, and is analyzed in OMOP research databases. Each hop crosses a different standard, and each is a place where data quietly breaks: duplicate messages, corrections that arrive out of order, codes that never get mapped. This project carries synthetic lab results across all three standards, through an interface engine, and proves with automated tests that every result arrives intact.

> **Status:** Milestone 1 (walking skeleton), in progress. See the [roadmap](#roadmap).
>
> **All data is synthetic,** generated with [Synthea](https://synthetichealth.github.io/synthea/). No real patient data is used anywhere in this project.

## What it does and why

<!-- TODO: Finalize after Milestone 2 with the run report's numbers. -->

Lab results reach downstream systems as HL7 v2 messages, often with local test codes, unit variants, resends and late corrections. The pipeline receives those messages the way a hospital does, through an interface engine channel that acknowledges or rejects each one, then converts them in two independent hops: structure first (HL7 v2 to FHIR R4), meaning second (FHIR to OMOP CDM). It fixes what it can prove, flags what it can't, and never guesses. Those rules come from clinical lab practice, where a result that can't be verified is held, not released.

## Architecture

<!-- TODO: Add the diagram to docs/architecture.md and embed it here. -->

```
Seeded Synthea sample
  → Mock LIS sends ORU^R01 over MLLP
  → BridgeLink channel: validate, ACK or NAK (rejects to an error queue)
  → Staging: every raw message kept
  → Hop 1 (structure): parse to LabResult → FHIR R4 bundle per panel, deterministic IDs
  → Hop 2 (meaning): vocabulary lookup → route by concept domain → OMOP CDM
  → Tests and run report: round trip, replay determinism
```

- **Hop 1** changes only the shape of the data. It never looks up a vocabulary or touches OMOP.
- **Hop 2** reads only FHIR. Code mapping happens here, through the OHDSI vocabularies.

## Quickstart

<!-- TODO: Replace with the one-command run once the Docker stack is in (Milestone 1). -->

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

## Worked example

<!-- TODO: One lab result shown three ways, side by side:
the HL7 v2 OBX segment, its FHIR Observation, and its OMOP MEASUREMENT row. -->

_Coming in Milestone 1._

## Tech stack

| Layer | Tool |
| --- | --- |
| Language | Python |
| Synthetic patients | Synthea (seeded sample committed to the repo) |
| HL7 v2 messaging | hl7apy, MLLP |
| Interface engine | BridgeLink (open-source Mirth Connect fork) |
| FHIR models | fhir.resources (R4B, targeting FHIR R4) |
| Database | Postgres 16 |
| Target data model | OMOP CDM v5.4 with OHDSI Athena vocabularies |
| Containers | Docker Compose, one command |
| CI | GitHub Actions |
| Dashboard | Streamlit |
| FHIR server (optional) | Blaze |

## Data quality approach

<!-- TODO: Link the tests and the run report once they exist (Milestone 2). -->

- **Fix what's provable, flag what isn't.** Local codes and unit spellings are mapped through vocabularies; a missing unit or an unmapped code is flagged and counted, never guessed.
- **Ground truth.** Synthea is the source of truth, so a round-trip test checks every result end to end: same value, unit and moment of collection, nothing lost, nothing invented.
- **Messy feeds on purpose.** The mock LIS injects realistic problems (local codes, unit variants, missing units, censored values, hemolysis, duplicates, corrections, out-of-order arrivals) and logs each one as an answer key.
- **Replay determinism.** A shuffled, duplicated feed with early corrections must produce exactly the same OMOP output as a clean one.

## Design decisions and trade-offs

<!-- TODO: One ADR per decision in docs/adr/. -->

Planned decision records:

- Two independent hops, with Hop 2 reading only FHIR
- Postgres staging as a durable queue instead of a message broker
- Deterministic resource IDs from business keys
- Corrections and ordering: the newest result time wins
- OMOP destination chosen by concept domain, not by resource type
- Foreign keys kept on, made deferrable
- FHIR R4B library targeting R4, and the US Core trade-off for local codes
- Code mapping in Hop 2 rather than in the interface engine

## Roadmap

**Milestone 1: walking skeleton**

- [ ] Guardrails, repo setup and vocabulary request
- [ ] Docker stack, migrations and CI
- [ ] Seeded Synthea sample and vocabulary subset
- [ ] Mock LIS writing ORU^R01 messages
- [ ] Hop 1: HL7 v2 to FHIR R4
- [ ] Hop 2: FHIR to OMOP, with the round-trip test

**Milestone 2: interface engine and messy data**

- [ ] BridgeLink channel: MLLP, ACK and NAK, error queue (public v0.1)
- [ ] Local codes and unit variants
- [ ] Missing units, censored values, corrections and ordering
- [ ] Replay determinism test
- [ ] Run report

**Milestone 3: ship it**

- [ ] Streamlit dashboard and final docs
- [ ] Polish and fresh-clone test
- [ ] Demo video and blog post
- [ ] v1.0 release

## At production scale

<!-- TODO: Expand once Milestone 2 is done. -->

What a production version would add: highly available MLLP listeners, incremental loads instead of full rebuilds, monitoring and alerting on the error queue, PHI security controls, transformation tooling such as dbt, workflow orchestration, and cloud deployment.

## Demo

<!-- TODO: Link the 60-second demo video (Milestone 3). -->

_Coming in Milestone 3._
