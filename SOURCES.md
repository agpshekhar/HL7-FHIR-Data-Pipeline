# Sources

The standards, data and vocabularies this pipeline depends on, where each comes from, and how it is used. The MIT license in `LICENSE` covers this repository's code only. Each source below keeps its own license or terms.

## Synthea

- **What:** Open-source synthetic patient generator. Supplies the patients, encounters and basic metabolic panel (BMP) lab results that the mock LIS turns into HL7 v2 messages.
- **Where:** https://synthetichealth.github.io/synthea/ (code at https://github.com/synthetichealth/synthea)
- **License:** Apache License 2.0.
- **Use here:** A small seeded sample is committed under `data/sample/` so every run starts from the same input. It is also the ground truth for the round-trip test. All data is synthetic; no real patient data is used.
- **Version / seed:** _To be recorded when the sample is generated._

## OMOP Common Data Model 5.4

- **What:** The OHDSI Observational Medical Outcomes Partnership data model, the target schema for Hop 2 (`person`, `visit_occurrence`, `measurement`, `observation`, vocabulary tables and so on).
- **Where:** https://ohdsi.github.io/CommonDataModel/cdm54.html (DDL at https://github.com/OHDSI/CommonDataModel)
- **License:** Apache License 2.0.
- **Use here:** The Postgres DDL for CDM 5.4 defines the tables Hop 2 loads. `scripts/fetch_omop_ddl.py` downloads it and writes it to `db/migrations/01*.sql` in the `cdm` schema, with every foreign key made deferrable and the missing primary key on `vocabulary` added.
- **Version:** CommonDataModel tag `v5.4.3`.

## OHDSI Athena vocabularies (LOINC, UCUM, SNOMED CT)

- **What:** The OHDSI Standardized Vocabularies, downloaded from Athena. Hop 2 uses them to map lab test codes to standard concepts (LOINC), units to UCUM concepts, and specimen and qualitative values to SNOMED CT concepts.
- **Where:** https://athena.ohdsi.org/
- **Terms:**
  - **LOINC:** Regenstrief Institute LOINC license (https://loinc.org/license/).
  - **UCUM:** Regenstrief Institute UCUM terms of use (https://ucum.org/license).
  - **SNOMED CT:** SNOMED International terms (https://www.snomed.org/get-snomed). Athena shows the license status of each vocabulary at download time; record any terms accepted there.
- **Use here:** The full bundle is kept locally in `data/vocab/` and is never committed (see `.gitignore`). Only a small subset needed by the tests may be committed, where the terms allow it.
- **Download date / vocabulary version:** _To be recorded when the bundle is downloaded._

## HL7 Version 2.5.1

- **What:** The HL7 v2 messaging standard. The pipeline uses ORU^R01 (unsolicited observation result) messages with MSH, PID, PV1, ORC, OBR, OBX, SPM and NTE segments, sent over MLLP, with ACK replies.
- **Where:** https://www.hl7.org/implement/standards/product_brief.cfm?product_id=144
- **Terms:** HL7 International standards; specifications are free to download after registering with HL7.
- **Use here:** The mock LIS builds and sends v2.5.1 messages; the BridgeLink channel validates and acknowledges them; Hop 1 parses them with hl7apy.
