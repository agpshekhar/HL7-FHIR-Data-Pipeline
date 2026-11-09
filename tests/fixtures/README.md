# Test fixtures

- `athena_mini/`: a stand-in for a full Athena download, with the same six files and headers but about 40 concepts. The domain, vocabulary, concept class and relationship rows are copied from a real download. The LOINC concepts use made-up IDs (900001 and up) and are not real Athena IDs. It includes a retired LOINC code with a "Maps to" row, a SNOMED concept reachable only through a dead mapping, and an unused LOINC code, so tests can check that each is handled.
- `sample_mini/`: a two-row stand-in for `data/sample/bmp_results.csv`.
