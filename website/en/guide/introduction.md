# Overview

FSHarvest extracts regional measures from multiple FreeSurfer subject directories and organizes them into
consistent TSV tables. It also records each subject's processing status, software versions, run parameters, and file checksums.

## Input directory requirements

Each immediate subdirectory of the input directory usually represents one subject:

```text
subjects/
├── sub-001/
│   ├── label/
│   ├── mri/
│   ├── scripts/
│   ├── stats/
│   └── surf/
└── sub-002/
    └── ...
```

Directory names do not have to start with `sub-`. FSHarvest identifies FreeSurfer results using key files such as
`stats/aseg.stats`, `surf/lh.white`, or `scripts/recon-all.log`. Use `--recursive` for nested datasets.
If different paths contain directories with the same name, the program stops to prevent them from writing to the same output location.

## Available measurements

- Subject ID, folder name, reconstruction FreeSurfer version, and presence of `recon-all.done`.
- Regional cortical vertex counts, surface area, gray matter volume, mean thickness, thickness standard deviation, and curvature measures.
- All structure records in `aseg.stats`.
- Global measures in `aseg.stats`, including estimated total intracranial volume (eTIV).
- Left and right surface-hole counts, Euler numbers, and their sums.
- Selected parcellations, run parameters, template versions, and input checksums.

## Processing workflow

```text
Discover subject directories
      │
      ├── Built-in FreeSurfer atlases ── Read existing aparc / aparc.a2009s statistics
      │
      └── External atlases ── Map annotations to subject surfaces ── Compute statistics
                                                                      │
                                                                      ▼
                                              Check region names, counts, and integrity
                                                                      │
                                                                      ▼
                                              Write long/wide tables and status (optional QC)
```

## Original results are unchanged by default

The default run only reads the input directory. Generated external-atlas `.annot` and `.stats` files and caches
are stored in `OUTPUT/per_subject/`, outside the original FreeSurfer results.

Only `--export-to-freesurfer` copies validated external-atlas files back into the input directories.
If a destination file has different contents, FSHarvest reports a conflict and refuses to overwrite it.

::: warning Use a separate output directory
The output directory must not equal the input directory or be located inside it; otherwise generated files could be mistaken for new inputs.
:::
