# Parcellations and extraction

A parcellation (atlas) defines how the cortex is divided into regions. Pass the names below after `--atlases` to select them.

## Available parcellations

| Command name | Total regions | Left / right regions | Source and template space |
| --- | ---: | ---: | --- |
| `dk68` | 68 | 34 / 34 | FreeSurfer built-in; default |
| `destrieux` | 148 | 74 / 74 | FreeSurfer built-in |
| `dk308` | 308 | 152 / 156 | NSPN500, `fsaverage` |
| `schaefer100` … `schaefer1000` | 100–1000 | Half the total per hemisphere | micapipe, `fsaverage5` |
| `glasser360` | 360 | 180 / 180 | micapipe, `fsaverage5` |
| `economo` | 86 | 43 / 43 | micapipe, `fsaverage5` |
| `vosdewael300` | 300 | 150 / 150 | micapipe, `fsaverage5` |

Only `dk68` is selected by default. All other atlases require explicit selection with `--atlases`.

`--atlases` also accepts custom atlas JSON files, mixed with the names above. Given left/right annotations and a source
template, custom atlases use the same projection, statistics, aggregation, and optional QC workflow.
See [Using your own annot files](../tutorials/multi-atlas#custom-annot).

## How each atlas is extracted

### Built-in FreeSurfer parcellations

DK68 reads `stats/{lh,rh}.aparc.stats` directly; Destrieux reads `stats/{lh,rh}.aparc.a2009s.stats`.
FSHarvest does not project, copy, or create a second set of subject annotation files for these atlases.

### External parcellations

FSHarvest uses `mri_surf2surf --sval-annot` to map pinned atlas annotation files (`.annot`) onto each subject's own surfaces.
It then runs `mris_anatomical_stats` using the white, pial, and thickness files.

Generated files are stored under:

```text
OUTPUT/per_subject/SUBJECT/label/
OUTPUT/per_subject/SUBJECT/stats/
```

## Select atlases to extract

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux dk308 \
            schaefer100 schaefer400 schaefer1000 \
            glasser360 economo vosdewael300
```

## Name and integrity checks

FSHarvest checks more than row counts: it compares region names against the fixed list after excluding medial-wall and
background regions, and verifies that annotation vertex counts match the subject surfaces. Inconsistent `.annot` files
fail validation. Bundled atlas files and region-name lists have SHA-256 checksums.

::: warning Three similarly sized atlases are not interchangeable
`schaefer300`, `vosdewael300`, and `dk308` are different parcellations. The `500` in DK308's upstream name refers to target parcel area, not the number of regions.
:::
