# Parcellations and extraction

A parcellation (atlas) defines how the cortex is divided into regions. Pass the names below after `--atlases` to select them.

## Available parcellations

The groups describe **how atlas boundaries were defined**, not which measures FSHarvest extracts. Counts exclude background and non-cortical labels. Cammoun requires **FSHarvest 1.0.5 or later**.

### Anatomical / structural parcellations

| Command name | Total cortex | Left / right | Parcellation basis | Source and template |
| --- | ---: | ---: | --- | --- |
| `dk68` | 68 | 34 / 34 | [Gyral anatomy](https://pubmed.ncbi.nlm.nih.gov/16530430/) | FreeSurfer built-in; default |
| `destrieux` | 148 | 74 / 74 | [Gyral and sulcal anatomy](https://pubmed.ncbi.nlm.nih.gov/20547229/) | FreeSurfer built-in |
| `dk308` | 308 | 152 / 156 | [DK subdivision by target area](https://github.com/KirstieJane/UCHANGE_ProcessingPipeline/blob/b4f8e8a3a56cee6a25187c075ed82157a3a1e67a/NSPN_Parcellation_PostEdits.sh) | NSPN500, `fsaverage` |
| `vosdewael300` | 300 | 150 / 150 | [DK anatomical subdivision](https://brainspace.readthedocs.io/en/stable/pages/matlab_doc/data_loaders/load_parcellation.html) | micapipe, `fsaverage5` |
| `cammoun33` | 68 | 34 / 34 | DK base scale | netneurotools, `fsaverage` |
| `cammoun60` | 114 | 57 / 57 | Multiscale DK subdivision | netneurotools, `fsaverage` |
| `cammoun125` | 219 | 111 / 108 | Multiscale DK subdivision | netneurotools, `fsaverage` |
| `cammoun250` | 448 | 225 / 223 | Multiscale DK subdivision | netneurotools, `fsaverage` |
| `cammoun500` | 1000 | 499 / 501 | Multiscale DK subdivision | netneurotools, `fsaverage` |
| `economo` | 86 | 43 / 43 | [Cytoarchitecture; MRI implementation](https://doi.org/10.1016/j.neuroimage.2016.12.069) | micapipe, `fsaverage5` |

Economo describes microscopic cellular organization; the other entries use macroscopic anatomy or its subdivisions.
DK308's upstream `500.aparc` name refers to a target parcel area of approximately 500 mm².
Cammoun provides anatomical regions for multiscale connectome analysis. Diffusion tractography measures connections
between these regions rather than defining their boundaries by connectivity clustering
([Cammoun et al., 2012](https://pubmed.ncbi.nlm.nih.gov/22001222/)).

### Functional-connectivity parcellations

| Command name | Total cortex | Left / right | Parcellation basis | Source and template |
| --- | ---: | ---: | --- | --- |
| `schaefer100` … `schaefer1000` | 100–1000 | Half per hemisphere | [Resting-state fMRI functional connectivity](https://pubmed.ncbi.nlm.nih.gov/28981612/) | micapipe, `fsaverage5` |

Schaefer combines local connectivity transitions with global similarity. FSHarvest bundles ten resolutions in
100-region increments, using Yeo 7-network labels. Unlike Cammoun scale identifiers, the suffix is the total cortical count.

### Multimodal parcellations: structure and function

| Command name | Total cortex | Left / right | Parcellation basis | Source and template |
| --- | ---: | ---: | --- | --- |
| `glasser360` | 360 | 180 / 180 | [Architecture, function, connectivity and topography](https://www.nature.com/articles/nature18933) | micapipe, `fsaverage5` |

Glasser HCP-MMP1.0 integrates structural MRI features, task responses and resting-state connectivity.
FSHarvest projects the bundled atlas; it does not rerun the original HCP multimodal classifier for each subject.

For every category, FSHarvest extracts **morphometric measures**, including cortical thickness, surface area and gray-matter
volume, from existing FreeSurfer reconstructions. Selecting a functional atlas does not require fMRI input or generate
functional-connectivity matrices.

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

## Cammoun2012

Cammoun2012 is a multiscale anatomical subdivision based on Desikan-Killiany. The suffixes
`33/60/125/250/500` identify upstream scales, **not cortical region counts**; actual counts
are listed above. The pinned annotations use full-resolution `fsaverage` (163842 vertices
per hemisphere), with `unknown` and `corpuscallosum` excluded from statistics.

`cammoun33` has the same cortical region-name set as DK68. It uses template-to-subject
projection, whereas `dk68` reads the subject's native `recon-all` parcellation, so boundaries
and statistics need not be identical. Only the cortical surface atlases are included;
existing aseg extraction is unchanged.

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases cammoun33 cammoun60 cammoun125 cammoun250 cammoun500
```

Assets are distributed under the [upstream terms](https://github.com/LTS5/cmp/blob/93094ce227bda9064512290dd505a7ba75cf7072/COPYRIGHT),
including research-only use. Cite [Cammoun et al. (2012)](https://doi.org/10.1016/j.jneumeth.2011.09.031).
