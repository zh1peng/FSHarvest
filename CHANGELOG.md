# Changelog

All notable changes to FSHarvest are recorded here. The project follows semantic versioning once a release is tagged.

## Unreleased

- Preserve pre-existing output files by cleaning only uniquely named, run-owned work directories, and reject input/output nesting in either direction.
- Track FSHarvest-created exports by relative path and SHA-256 so identical full reruns reuse cache while changed destinations remain conflict-protected.
- Record checksums for current wide tables and archive a preceding run's no-longer-selected atlas tables instead of leaving them in `wide/`.
- Clarify that cohort tables represent the current command scope and document subject-aware regional join keys.

## 1.0.0rc1

- Release candidate; not a stable public release.
- Add Schaefer 100–1000, Glasser360, Economo, and Vos de Wael 300 support using pinned atlas assets.
- Add resumable private annotation/statistics caches and opt-in conflict-safe export to FreeSurfer subjects.
- Add streamed cohort aggregation, provenance metadata, and four-view QC rendering/reporting.
- Validate cached TSV checksums, schemas, atlas/hemisphere row counts, and serialized values before reuse.
- Parse and validate external annotation structure and pinned region names before reuse or export.
- Record and verify per-hemisphere annotation/statistics checksums in artifact metadata.
- Exclude non-OK or integrity-failed subjects from trusted cohort feature tables.
- Download and verify atlas updates in a staged directory before replacing the installed bundle.
- Pin expected cortical region-name sets for every supported atlas and hemisphere.
- Strengthen `aseg.stats` validation with key structures, minimum completeness, duplicate detection, and integer-domain checks.
- Add per-run identifiers, cache-hit provenance, fatal-status persistence, and current-run-only aggregation.
- Preflight optional QC dependencies before extraction.
- Make `--overwrite` force fresh external atlas projection and anatomical-statistics generation.
- Add Linux CI across Python 3.9–3.12, CLI integration coverage, citation metadata, and third-party notices.
