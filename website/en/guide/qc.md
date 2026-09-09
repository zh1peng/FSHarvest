# Surface QC images

FSHarvest can generate four-view PNGs for selected parcellations and display all subjects in `all_qc.html`.
The HTML uses relative image paths, so it remains usable after copying or moving the entire output directory.

## Install plotting dependencies

```bash
python3 -m pip install -r requirements-qc.txt
```

## Generate four-view images

```bash
fsharvest INPUT OUTPUT \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

Each image shows left lateral, left medial, right lateral, and right medial views, in that order.
The default surface is inflated. Other settings include:

```bash
--qc-surface pial
--qc-surface white
--qc-dpi 150
```

The minimum `--qc-dpi` is 72. This real DK68 output was generated on `linux212` with FreeSurfer 7.4.1 and contains no subject text identifier:

![Real four-view DK68 inflated-surface output](/examples/dk68-inflated-example.png)

The same run generated this Schaefer100 image:

![Real four-view Schaefer100 inflated-surface output](/examples/schaefer100-inflated-example.png)

## View all subjects in a browser

```bash
xdg-open OUTPUT/all_qc.html
```

Switch between atlases, search by subject ID, and click thumbnails to view the full images.
This screenshot is from an actual generated report; the subject name was replaced with `example-01`:

![Generated all_qc.html report](/examples/qc-report-example.png)

Each PNG has a companion `.json` recording the run ID, surface type, DPI, and SHA-256 checksums for input surfaces and annotations.
The HTML shows only images matching the current run and inputs. If QC was not enabled or rendering failed, old images do not appear as current results.

## What to inspect

- Whether the parcellation covers the expected cortical regions.
- Missing or visibly misaligned hemispheres.
- Unexpected appearance of the medial wall.
- Subjects that differ markedly from most other images in the dataset.

::: danger These images do not replace Freeview inspection
Four-view images help reveal obvious projection or reconstruction problems, but cannot establish whether subtle white/pial boundary errors are present.
Complete the final quality review in Freeview.
:::
