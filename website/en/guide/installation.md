# Installation

## Requirements

- Linux
- Python 3.9 or later
- FreeSurfer installed with a configured license
- `curl` if you need to download the atlas files again

Core table extraction requires no third-party Python packages. NumPy, Nibabel, Matplotlib, and Pillow are needed only for surface QC images.

## Install the fsharvest command

```bash
git clone https://github.com/zh1peng/FSHarvest.git
cd FSHarvest
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
```

The default installation directory is `~/.local/lib/fsharvest/VERSION/`. After installation and checks succeed,
the `current` link points to the new version and the launcher is created at `~/.local/bin/fsharvest`.
Versions are stored separately. The installed command does not depend on the downloaded source directory.

To install elsewhere, pass the installation directory to `install.sh`:

```bash
bash install.sh /opt/fsharvest
```

Check the installation or remove its launcher links:

```bash
bash install.sh --check /opt/fsharvest
bash install.sh --uninstall /opt/fsharvest
```

## Run without installing

```bash
bash /path/to/FSHarvest/fsharvest --help
```

## Install QC dependencies

```bash
python3 -m pip install -r requirements-qc.txt
```

## Verify the installation

These commands do not require FreeSurfer initialization:

```bash
fsharvest --version
fsharvest --help
```

Initialize FreeSurfer before extraction:

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

Alternatively, pass `--freesurfer-home /path/to/freesurfer` directly. At startup, FSHarvest checks that
`recon-all`, `mri_surf2surf`, and `mris_anatomical_stats` are available.
