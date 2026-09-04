# Bundled atlas provenance

The binary `.annot` files in this directory are redistributed with the extraction code so a run does not depend on a mutable network download. `manifest.json` pins and verifies every file by SHA-256. `region_schema.json` pins a SHA-256 of each sorted post-exclusion region-name set, so a same-sized but semantically different atlas cannot pass extraction validation. Run `../download_atlases.sh` to reproduce the downloads and verify them; downloads are staged and fully verified before the installed atlas directory is replaced.

## Schaefer 2018: 100–1000 parcels

- Scientific atlas: ThomasYeoLab/CBIG, `Schaefer2018_LocalGlobal`.
- Redistributed annotation source: `MICA-MNI/micapipe`, pinned commit `4227ee660f216387df4310088dde026d1278dd8e`.
- Source directory and template: micapipe `parcellations/`, FreeSurfer `fsaverage5`.
- Files: left/right `schaefer-{100,200,...,1000}_mics.annot`, using Yeo 7-network labels.
- Projection reference: <https://github.com/ThomasYeoLab/CBIG/blob/master/stable_projects/brain_parcellation/Schaefer2018_LocalGlobal/Parcellations/project_to_individual/README.md>
- Annotation source: <https://github.com/MICA-MNI/micapipe/tree/4227ee660f216387df4310088dde026d1278dd8e/parcellations>
- Schaefer et al. (2018): <https://doi.org/10.1093/cercor/bhx179>.
- Redistribution license: micapipe GNU GPL v3; see `LICENSE_MICAPIPE_GPL3.txt`. The original atlas authors' citation and terms still apply.

The **files** and their `fsaverage5` geometry come from micapipe; the **subject projection procedure** follows CBIG. For each hemisphere FSHarvest runs `mri_surf2surf --srcsubject fsaverage5 --trgsubject SUBJECT --sval-annot ... --tval ...`, then runs `mris_anatomical_stats` on the subject's native surfaces. It excludes `Background+FreeSurfer_Defined_Medial_Wall` and requires exactly half of the requested parcels per hemisphere.

## DK308 / NSPN500 (`500.aparc`)

- Pipeline name: `dk308`.
- Canonical upstream names: NSPN500 and `500.aparc`.
- Upstream: `KirstieJane/UCHANGE_ProcessingPipeline` (Kirstie Whitaker).
- Pinned commit: `b4f8e8a3a56cee6a25187c075ed82157a3a1e67a`.
- Source directory: `FS_SUBJECTS/fsaverageSubP/label/`.
- Files: `lh.500.aparc.annot`, `rh.500.aparc.annot`.
- Source: <https://github.com/KirstieJane/UCHANGE_ProcessingPipeline/tree/b4f8e8a3a56cee6a25187c075ed82157a3a1e67a/FS_SUBJECTS/fsaverageSubP/label>
- Original projection script: <https://github.com/KirstieJane/UCHANGE_ProcessingPipeline/blob/b4f8e8a3a56cee6a25187c075ed82157a3a1e67a/NSPN_Parcellation_PostEdits.sh>
- License: MIT; see `LICENSE_DK308_MIT.md`.

The upstream script defines `500.aparc` as the NSPN500 parcellation: 308 regions constrained within Desikan-Killiany atlas boundaries and no more than approximately 500 mm² in surface area. `fsaverageSubP` is an upstream copy of FreeSurfer's full-resolution `fsaverage`; this package uses the installed FreeSurfer `fsaverage` as the source registration subject and supplies the pinned annotations by absolute path. Compatibility is checked by expected native-space parcel counts during every run.

## Other micapipe fsaverage5 parcellations

- Pipeline names: `economo`, `glasser360`, and `vosdewael300`.
- Upstream: `MICA-MNI/micapipe`.
- Pinned commit: `4227ee660f216387df4310088dde026d1278dd8e`.
- Source directory: `parcellations/`.
- Source template: FreeSurfer `fsaverage5`.
- Files: left/right `economo_mics.annot`, `glasser-360_mics.annot`, and `vosdewael-300_mics.annot`.
- Source: <https://github.com/MICA-MNI/micapipe/tree/4227ee660f216387df4310088dde026d1278dd8e/parcellations>
- micapipe methods: Cruces et al. (2022), <https://doi.org/10.1016/j.neuroimage.2022.119612>.
- micapipe repository license: GNU GPL v3; see `LICENSE_MICAPIPE_GPL3.txt`. The original atlas authors' terms and required scientific citations may additionally apply to derived atlas data.

`economo` is the MRI implementation of the von Economo-Koskinas cytoarchitectonic atlas described by Scholtens et al. (2018), <https://doi.org/10.1016/j.neuroimage.2016.12.069>. FSHarvest expects 43 cortical regions per hemisphere after excluding non-cortical labels.

`glasser360` is micapipe's fsaverage5 representation of the 360-area HCP-MMP1.0 multimodal parcellation described by Glasser et al. (2016), <https://doi.org/10.1038/nature18933>. FSHarvest excludes `medialwall` and expects 180 cortical regions per hemisphere.

`vosdewael300` is the 300-region anatomical subparcellation of Desikan-Killiany/aparc distributed with micapipe and BrainSpace. It is distinct from both the functional `schaefer300` atlas and the 308-region `dk308`/NSPN500 atlas. See Vos de Wael et al. (2020), <https://doi.org/10.1038/s42003-020-0794-7>. FSHarvest excludes label `1` (the medial wall) and expects 150 cortical regions per hemisphere.

micapipe projects these annotations from `fsaverage5` to the native subject surface with `mri_surf2surf --sval-annot`; FSHarvest follows the same source-template convention and validates the resulting region counts separately for each hemisphere.

## Built-in FreeSurfer atlases are not bundled or rebuilt

`dk68` (`aparc`) and `destrieux` (`aparc.a2009s`) are outputs of the subject's existing `recon-all`. FSHarvest reads their existing `stats/{lh,rh}.*.stats` files directly. Their `label/{lh,rh}.*.annot` files are read only when rendering QC. Neither path calls `mri_surf2surf` or `mris_anatomical_stats`, and neither creates an annotation under `OUTPUT/per_subject/`.
