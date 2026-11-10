# Sources

The standards, data and vocabularies this pipeline depends on, where each comes from, and how it is used. The MIT license in `LICENSE` covers this repository's code only. Each source below keeps its own license or terms.

## Synthea

- **What:** Open-source synthetic patient generator. Supplies the patients, encounters and basic metabolic panel (BMP) lab results that the mock LIS turns into HL7 v2 messages.
- **Where:** https://synthetichealth.github.io/synthea/ (code at https://github.com/synthetichealth/synthea)
- **License:** Apache License 2.0.
- **Use here:** `scripts/extract_bmp_sample.py` extracts the basic metabolic panels (the eight Serum/Plasma analytes Synthea reports under LOINC 24321-2, without the calculated eGFR; CMP draws are left out) into `data/sample/`: 12 patients, 1,331 panels, 10,648 results. The sample is committed so every run starts from the same input, and it is the ground truth for the round-trip test. All data is synthetic; no real patient data is used.
- **Version / seed:** Synthea commit `d9d07a6`, Java 21, run 2026-10-16:
  `java -jar synthea-with-dependencies.jar -s 42 -p 100 --exporter.csv.export=true Kansas`
  (reference date 2026-10-16, clinician seed 1792183437730, 10 years of history; 112 patients including deceased). Synthea also reads the time of day, so a rerun with the same seeds does not reproduce these files byte for byte. The committed extract, not the command, is the fixed input.

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
- **Use here:** The full bundle is kept locally in `data/vocab/` and is never committed (see `.gitignore`). `scripts/build_vocab_subset.py` cuts the minimal LOINC/UCUM subset the pipeline needs into `db/vocab_subset/`, which is committed. SNOMED CT is kept out of the subset. Attribution notices are in `NOTICE.md`.
- **Vocabulary versions:** LOINC 2.82, UCUM 1.8.2, OMOP Standardized Vocabularies v5.0 29-AUG-26 (from the bundle's `VOCABULARY.csv`). Bundle unpacked 2026-11-09.

## HL7 Version 2.5.1

- **What:** The HL7 v2 messaging standard. The pipeline uses ORU^R01 (unsolicited observation result) messages with MSH, PID, PV1, ORC, OBR, OBX, SPM and NTE segments, sent over MLLP, with ACK replies.
- **Where:** https://www.hl7.org/implement/standards/product_brief.cfm?product_id=144
- **Terms:** HL7 International standards; specifications are free to download after registering with HL7.
- **Use here:** The mock LIS builds and sends v2.5.1 messages; the BridgeLink channel validates and acknowledges them; Hop 1 parses them with hl7apy.
