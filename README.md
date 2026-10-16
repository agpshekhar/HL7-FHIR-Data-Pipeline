# HL7-FHIR-Data-Pipeline

Public, end-to-end pipeline that turns synthetic HL7 v2 lab results into FHIR resources and OMOP research tables, with automated quality checks, orchestration, Docker, and cloud deployment.

> **Status:** Phase 0 (setup). Work in progress. See the [roadmap](#roadmap).
>
> **All data is synthetic,** generated with [Synthea](https://synthetichealth.github.io/synthea/). No real patient data is used anywhere in this project.

## What it does and why

<!-- TODO: One paragraph. The problem (lab results arrive as HL7 v2 with local codes),
what the pipeline does about it, and why the quality checks come from lab auto-validation. -->

_To be written._

## Architecture

<!-- TODO: Add the diagram to docs/ and embed it here. -->

_Diagram coming soon._

## Quickstart

<!-- TODO: Replace with the one-command run once Docker is set up (Phase 4). -->

```bash
git clone https://github.com/agpshekhar/HL7-FHIR-Data-Pipeline.git
cd HL7-FHIR-Data-Pipeline
uv sync
```

## Worked example

<!-- TODO: One lab result shown three ways, side by side:
the HL7 v2 OBX segment, its FHIR Observation, and its OMOP MEASUREMENT row. -->

_Coming in Phase 3._

## Tech stack

| Layer | Tool |
| --- | --- |
| Language | Python |
| Synthetic patients | Synthea |
| HL7 v2 parsing | hl7apy |
| FHIR models | fhir.resources |
| Warehouse | DuckDB (local), Postgres on RDS (cloud) |
| Transformations and tests | dbt Core |
| Target data model | OMOP CDM v5.4 |
| Orchestration | Dagster |
| Containers | Docker, docker compose |
| CI | GitHub Actions |
| Cloud | AWS |
| Dashboard | Streamlit |

## Data quality approach

<!-- TODO: How the checks mirror clinical lab auto-validation (delta checks, AMR,
critical values) and the warn-versus-error design. Link the dbt tests. -->

_Coming in Phase 3._

## Design decisions and trade-offs

<!-- TODO: e.g. Dagster vs Airflow, DuckDB vs Postgres, how unmapped local codes are handled. -->

_To be written as decisions are made._

## Roadmap

- [ ] Phase 0: Setup and data exploration
- [ ] Phase 1: Generate and parse HL7 v2 messages
- [ ] Phase 2: Map HL7 v2 to FHIR
- [ ] Phase 3: FHIR to OMOP with dbt and quality tests
- [ ] Phase 4: Orchestration, Docker, and CI
- [ ] Phase 5: Cloud deployment and dashboard

## At production scale

<!-- TODO: Real-time MLLP ingestion, incremental loads, monitoring. -->

_To be written._

## Demo

<!-- TODO: Link the 3-minute demo video (Phase 5). -->

_Coming in Phase 5._
