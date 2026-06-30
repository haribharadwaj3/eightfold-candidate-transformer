# Multi-Source Candidate Data Transformer

A robust, deterministic Python pipeline designed to ingest candidate information from multiple structured and unstructured sources, resolve duplicates, normalize values to canonical representations (E.164 phones, YYYY-MM dates, ISO-3166 locations, and standardized skills), trace provenance, and output schema-validated JSON with a customizable projection engine.

## Features

- **Multi-Source Support**:
  - Structured: **Recruiter CSV** export and **ATS JSON** blobs (supporting custom schema layouts).
  - Unstructured: **GitHub API** profile & repos, **Resumes** (PDF/DOCX/TXT), and **Recruiter Notes** (.txt).
- **Entity Resolution**: Clusters records belonging to the same candidate using email overlap, phone overlap, and fuzzy name similarity matching.
- **Normalization Engine**:
  - Phones to **E.164** format using `phonenumbers`.
  - Dates to **YYYY-MM** format using `dateutil`.
  - Countries to **ISO-3166-1 alpha-2** codes using `pycountry`.
  - Technology skills standardized to canonical representations using a configurable synonym dictionary.
- **Conflict Resolution**: Resolves field discrepancies across sources using field-specific priority and source reliability trust scoring.
- **Configurable Output Projection**: Includes a JSONPath-like projection layer to dynamically shape the output JSON at runtime (renaming fields, flattening arrays, and custom missing value strategies).
- **Verification & Schema Validation**: Validates candidate profiles against JSON Schemas (via `jsonschema` with a native fallback validation system).

---

## Installation

Ensure you have Python 3.8+ installed.

1. Clone or navigate to the repository directory.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## How to Run

### 1. Default Canonical Profile Output
To process sample inputs and output the unified candidate profile using the default schema:
```bash
python main.py --inputs sample_inputs/recruiter_export.csv sample_inputs/ats_blob.json sample_inputs/recruiter_notes.txt sample_inputs/resume_sample.txt --pretty --verbose
```

### 2. Runtime-Configured Schema Output
To project the unified profile into a custom layout using a configuration file:
```bash
python main.py --inputs sample_inputs/recruiter_export.csv sample_inputs/ats_blob.json sample_inputs/recruiter_notes.txt sample_inputs/resume_sample.txt --config config/sample_custom_config.json --pretty
```

### 3. Integrating GitHub Profiles
Pass the `--github-token` or export `GITHUB_TOKEN` to integrate a public GitHub profile username:
```bash
python main.py --inputs github:octocat sample_inputs/recruiter_notes.txt --pretty
```

---

## Sample Outputs

Pre-generated outputs produced by running the pipeline on the sample input files:
- **Default Canonical Output**: [sample_outputs/default_output.json](sample_outputs/default_output.json)
- **Runtime-Configured Output**: [sample_outputs/custom_config_output.json](sample_outputs/custom_config_output.json)

---

## Running Tests


All modules are fully tested with unit and integration tests. Run the test suite:
```bash
python -m pytest tests/ -v
```

---

## Project Structure

- `main.py`: Main CLI entry point.
- `pipeline/`:
  - `ingest.py`: Detects source types and dispatches to appropriate extractor.
  - `extractors/`: Specific raw parsing logic for CSV, JSON, GitHub, Resume, and Notes.
  - `normalize.py`: Conversions for phones, dates, locations, and skills.
  - `merge.py`: Groups duplicate candidate profiles and resolves data conflicts.
  - `project.py`: Applies custom runtime field projections.
  - `validate.py`: Checks structure correctness against default/custom schemas.
- `config/`:
  - `default_schema.json`: Target canonical schema specification.
  - `skills_synonyms.json`: Skill normalization mapping dict.
  - `sample_custom_config.json`: Configuration for custom layout projections.
- `sample_inputs/`: Mock files representation of a candidate across all 4 formats.
- `tests/`: Automated tests verifying normalizations, merges, configurations, and edge cases.
