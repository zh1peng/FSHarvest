# 命令行参数

```text
fsharvest SUBJECTS_DIR OUTPUT_DIR [options]
```

## 位置参数

| 参数 | 说明 |
| --- | --- |
| `subjects_dir` | 其子目录为 FreeSurfer subjects 的目录 |
| `output_dir` | 独立输出目录；不能位于输入目录内部 |

## 执行参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--jobs N` | CPU 数限制在 1–8 | 并行处理的受试者数 |
| `--limit N` | 无 | 仅处理排序后的前 N 位受试者 |
| `--recursive` | 关闭 | 递归发现受试者目录 |
| `--overwrite` | 关闭 | 忽略缓存与可复用外部产物，重新投影和计算 |
| `--freesurfer-home PATH` | `$FREESURFER_HOME` | 指定 FreeSurfer 安装目录 |
| `--atlas-dir PATH` | bundled `atlases/` | 使用指定 Atlas 资源目录 |

## Atlas 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--atlases ...` | `dk68` | 选择一个或多个 Atlas |
| `--export-to-freesurfer` | 关闭 | 将验证后的外部 annotation/stats 复制回输入 subject；不覆盖冲突文件 |

Atlas 键包括 `dk68`、`destrieux`、`dk308`、`schaefer100` 至 `schaefer1000`、
`glasser360`、`economo` 和 `vosdewael300`。

## QC 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--qc-plots` | 关闭 | 生成四视图 PNG |
| `--qc-atlases ...` | 所选 Atlas | 只绘制所选 Atlas 的子集 |
| `--qc-surface` | `inflated` | `inflated`、`pial` 或 `white` |
| `--qc-dpi` | `150` | 输出 DPI，最小 72 |

## 信息参数

```bash
fsharvest --version
fsharvest --help
```

当前软件版本为 `1.0.0`。
