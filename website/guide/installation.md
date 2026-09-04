# 安装

## 环境要求

- Linux
- Python 3.9 或更高版本
- 已授权并可用的 FreeSurfer
- 重新下载 Atlas 时需要 `curl`

核心提取没有第三方 Python 包依赖。只有绘制表面 QC 时需要 NumPy、Nibabel、Matplotlib 和 Pillow。

## 安装为用户命令

```bash
git clone https://github.com/zh1peng/FSHarvest.git
cd FSHarvest
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
```

默认安装到 `~/.local/lib/fsharvest/VERSION/`，复制与自检完成后原子切换 `current`
链接，并在 `~/.local/bin/fsharvest` 创建入口。不同版本不会相互合并。
安装后的命令不依赖源码检出目录。

可以把其他前缀作为第一个参数：

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

## 检查安装

下面两个命令不需要初始化 FreeSurfer：

```bash
fsharvest --version
fsharvest --help
```

真正提取前，设置运行时：

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

也可以在命令中使用 `--freesurfer-home /path/to/freesurfer`。
