# Citation and licensing

## Describe FSHarvest in your Methods {#methods}

Copy the English Methods paragraphs below using the button at the top right of each block, then adapt them to your study.
FSHarvest extracts measurements from existing FreeSurfer reconstructions; describe reconstruction methods and quality control separately.

### General wording

Replace bracketed placeholders with the versions, atlases, and analysis measures you actually used, and add the relevant software and atlas references:

<div class="methods-copy">

```text
Regional morphometric measures were extracted from existing FreeSurfer reconstructions using FSHarvest (version [FSHARVEST_VERSION]; https://github.com/zh1peng/FSHarvest). Cortical measures were obtained for the [ATLAS_NAMES] parcellation(s), and [MEASURES_USED_IN_ANALYSIS] were retained for analysis. FSHarvest organized the extracted measurements into participant-level tables, aligning cortical measurements by atlas, hemisphere, and region name. Software versions, processing status, and run parameters were recorded for reproducibility.
```

</div>

For `MEASURES_USED_IN_ANALYSIS`, enter the measures used in your study, such as `regional mean cortical thickness,
surface area, and gray matter volume`. If analyzing only subcortical measures, revise the cortical-parcellation sentence.
The reconstruction version is recorded in `subjects.tsv` as `fs_version`; the FreeSurfer version used during extraction
is recorded in `run_metadata.json`. These may differ and should be distinguished in your Methods.

### Wording for the six-atlas example

This paragraph matches the site's [ten-subject six-atlas example](../tutorials/ten-subject-example#six-atlas):
FSHarvest 1.0.4, FreeSurfer 7.2.0 input reconstructions, and a FreeSurfer 7.4.1 extraction runtime.
Replace these details with your actual versions, atlases, and workflow before using it in a manuscript.

<div class="methods-copy">

```text
Regional morphometric measures were extracted using FSHarvest (version 1.0.4; https://github.com/zh1peng/FSHarvest) from reconstructions previously generated with FreeSurfer 7.2.0. Six cortical parcellations were included: Desikan-Killiany (68 regions), DK308, Destrieux (148 regions), and Schaefer parcellations with 100, 200, and 300 regions. Desikan-Killiany and Destrieux measurements were read from the existing FreeSurfer statistics files. DK308 and Schaefer annotations were mapped from their source template surfaces to each participant's cortical surfaces using mri_surf2surf, and regional statistics were computed using mris_anatomical_stats in FreeSurfer 7.4.1. Outputs included regional cortical thickness, surface area, gray matter volume, aseg structure volumes, and global measures. Measurements were aggregated across participants by atlas, hemisphere, and region name, with processing status and run parameters retained alongside the results.
```

</div>

This example enabled neither FSHarvest QC rendering nor reconstruction. `OK` status does not mean every subject passed
manual QC. Describe quality control, exclusion criteria, and downstream analysis according to the procedures actually performed.

### Describing missing-value handling

This paragraph describes FSHarvest's aggregation behavior. Report any subsequent imputation, name normalization, or subject exclusions separately:

<div class="methods-copy">

```text
FSHarvest retained successfully parsed measurements with unambiguous identifiers even when other measurements were unavailable. Original region names were preserved, and missing measurements were left empty in the exported tables without imputation. Differences from expected region names and processing errors were recorded for review.
```

</div>

## Cite FSHarvest

Software citation metadata are in [`CITATION.cff`](https://github.com/zh1peng/FSHarvest/blob/main/CITATION.cff).
Click **Cite this repository** on the GitHub repository page to copy a BibTeX or APA citation.
Cite the version you used; these examples use [v1.0.4](https://github.com/zh1peng/FSHarvest/releases/tag/v1.0.4).

Current software information:

| Item | Value |
| --- | --- |
| Name | FSHarvest |
| Version | 1.0.4 |
| Release date | 2026-09-09 |
| Code license | MIT |

## Cite the parcellations

In addition to FSHarvest, cite FreeSurfer and the original papers for each atlas used, including built-in DK68 and Destrieux.
Sources, pinned commits, DOIs, templates, and redistribution licenses for bundled external atlases are recorded in:

- [`atlases/README.md`](https://github.com/zh1peng/FSHarvest/blob/main/atlases/README.md)
- [`THIRD_PARTY_NOTICES.md`](https://github.com/zh1peng/FSHarvest/blob/main/THIRD_PARTY_NOTICES.md)

## License scope

FSHarvest source code is MIT-licensed. Bundled `.annot` files retain their original licenses; the MIT license does not
replace atlas authors' citation requirements or data-use terms. Check the terms for every atlas you used before distributing or publishing results.
