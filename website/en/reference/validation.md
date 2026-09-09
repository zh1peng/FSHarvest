# Validation and compatibility

## Validated environment

Real-data validation has used:

- Linux x86_64.
- A FreeSurfer 7.4.1 runtime.
- Subject directories reconstructed with FreeSurfer 7.2.0.
- Ten real subjects.
- Built-in and external atlases, cache reuse, export safeguards, and headless QC rendering.

Checks covered expected region counts, nine cortical measures, long and wide tables, four-view PNGs,
HTML reports with relative paths, and safe reuse of annotations and statistics files.

## Agreement between reading built-in statistics and recomputing them

For ten subjects, DK68 and Destrieux were evaluated through two paths: reading native `aparc.stats` / `aparc.a2009s.stats`
and rerunning `mris_anatomical_stats` using the same subjects' `.annot`, white, pial, and thickness files.
Across both hemispheres, 2,160 region rows and nine measures were compared, totaling 19,440 values.
All values were identical at the precision stored in the FreeSurfer statistics files. Maximum absolute and relative
errors were both 0, and all comparisons passed `atol=rtol=1e-12`.

The original statistics were generated with FreeSurfer 7.2.0 and recomputation used 7.4.1, so this also demonstrates
cross-version agreement for this dataset. The check uses existing subject annotations and validates statistics computation;
it is not a validation of `mri_surf2surf` atlas projection itself. The repository's
`validation/validate_builtin_recompute.py` can repeat the complete comparison.

## Version 1.0.4 checks

All 78 tests on Windows / Python 3.12 passed, along with Ruff, mypy, Bash syntax checks, and the documentation build.
Run-log tests cover merged standard output and errors, UTF-8 text, exit-code preservation, distinct logs for repeated runs,
Python entry points, shell environment-setup failures, no logs for help/version queries, and rejection of overlapping
input/output paths or uncreatable log directories before work begins.

These are pre-release automated checks; extraction integration tests use simulated FreeSurfer commands.

After release, the official v1.0.4 was installed on linux212 and the first ten subjects were rerun for the Pages examples:

- First DK68 run: 10/10 `OK`, 680 cortical rows, 450 aseg rows, and 200 global-measure rows.
- Same command repeated: 10/10 cache hits, with both run logs retained.
- Downloadable DK68 SH script: 10/10 `OK`; its three long tables and combined wide table were identical to the CLI results.
- A fresh output directory was used for DK68, DK308, Destrieux, and Schaefer100/200/300: 10/10 `OK`, all 60 subject × atlas combinations complete, 11,240 cortical rows, and a 10-row × 10,191-column combined wide table.
- Six-atlas runtime was 19 minutes 37 seconds. Both examples' name-differences reports contained only headers, and both produced zero QC PNGs.

These runs performed neither reconstruction nor QC. Commands, complete de-identified logs, and table excerpts are in the
[ten-subject worked example](../tutorials/ten-subject-example).

## Version 1.0.3 checks

All 72 tests on Windows / Python 3.12 passed, along with Ruff, mypy, Bash syntax checks, and the documentation build.
New tests cover startup attribution and version, stage order, pre-work messages, elapsed time, cache hits, optional export
and QC, partial and failed summaries, interruption, and concise help/version output.

Entry-point checks confirmed that environment-initialization failures still show one banner and preserve the original
failure exit code. Integration tests use simulated FreeSurfer commands; this version added no real-data reconstruction,
projection, statistics, or QC runs.

## Version 1.0.2 checks

All 65 tests on Windows / Python 3.12 passed, along with Ruff, mypy, and the documentation build.
New tests cover partial-result aggregation, preservation of original names, empty missing values, and isolation of duplicate keys and damaged files.

Aggregation was also validated on a temporary copy of existing outputs for 554 subjects. The wide table retained all 554
subjects and their original `PARTIAL` status. Long tables retained 452,063 cortical rows, 24,930 aseg rows, and 12,188
global-measure rows. Known missing left-hemisphere regions had empty cells while right-hemisphere values remained intact;
names containing `&` were unchanged.
Original outputs were not modified, and per-subject TSV checksums were unchanged. This validation did not rerun FreeSurfer reconstruction, projection, statistics, or QC.

## Version 1.0.1 checks

All 55 tests on Windows / Python 3.12 passed, along with Ruff, mypy, and the documentation build.
New cases cover custom atlases, unused color-table entries, automatic label exclusions, and region names with spaces.
Extraction was validated with simulated FreeSurfer commands; this version added no real-data trial run.

## Version 1.0.0 checks

All 45 local regression tests passed, together with Python 3.12, Ruff, and mypy checks. Work on `linux212` also included:

- 45 regression tests.
- Real DK68 and Schaefer100 extraction.
- QC images and HTML report generation.
- Cached reruns and recomputation after cache damage.
- Numerical comparisons against independent calculations.

A second round in a real FreeSurfer environment checked repeated export of the same complete command, conflict protection
after an exported file was changed, reducing a three-subject summary to `--limit 1`, archiving deselected atlas wide tables,
and preserving a pre-existing `OUTPUT/work` directory.

QC images shown on this site come from those earlier real linux212 runs. New 1.0.4 terminal examples explicitly identify
their version and date. Public examples replace subject names and private paths.

## Scope and limitations

These results validate the environments above, not every FreeSurfer version or cluster configuration. FreeSurfer 8.x is
not yet included. On a new environment, start with a small sample and inspect `subjects.tsv`, region counts, and QC images.

Full validation methods and records are in [`VALIDATION.md`](https://github.com/zh1peng/FSHarvest/blob/main/VALIDATION.md).
