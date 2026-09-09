# 安装

## 环境要求

- Linux
- Python 3.9 或更高版本
- 已安装 FreeSurfer，并完成许可证配置
- 重新下载脑区分区文件时需要 `curl`

核心表格提取不依赖第三方 Python 包。只有生成表面 QC 图片时需要 NumPy、Nibabel、
Matplotlib 和 Pillow。

## 安装 fsharvest 命令

```bash
git clone https://github.com/zh1peng/FSHarvest.git
cd FSHarvest
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
```

默认安装到 `~/.local/lib/fsharvest/VERSION/`。安装并检查通过后，`current` 链接会指向
新版本，并在 `~/.local/bin/fsharvest` 创建启动命令。各版本单独存放；
安装后的命令不依赖下载的源码目录。

需要安装到其他位置时，在 `install.sh` 后指定安装目录：

```bash
bash install.sh /opt/fsharvest
```

安装后检查或移除启动链接：

```bash
bash install.sh --check /opt/fsharvest
bash install.sh --uninstall /opt/fsharvest
```

## 不安装直接运行

```bash
bash /path/to/FSHarvest/fsharvest --help
```

## 安装 QC 依赖

```bash
python3 -m pip install -r requirements-qc.txt
```

## 确认安装结果

下面两个命令不需要初始化 FreeSurfer：

```bash
fsharvest --version
fsharvest --help
```

正式提取前，初始化 FreeSurfer：

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

也可以直接传入 `--freesurfer-home /path/to/freesurfer`。程序会在启动时确认
`recon-all`、`mri_surf2surf` 和 `mris_anatomical_stats` 是否可用。
