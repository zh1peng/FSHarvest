# 教程：基础批量提取

本教程从十位受试者的冒烟测试开始，再扩展到完整队列。

## 1. 初始化 FreeSurfer

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

确认关键命令可用：

```bash
command -v recon-all
command -v mri_surf2surf
command -v mris_anatomical_stats
```

## 2. 运行 DK68 冒烟测试

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 4 \
  --limit 10
```

## 3. 检查状态

```bash
cut -f1-6 /data/derived/fsharvest/subjects.tsv | column -t -s $'\t'
```

每位受试者应显示为 `OK`。如果出现 `PARTIAL` 或 `FAILED`，先查看对应目录下的
`extract.log` 与 `status.json`，不要直接使用队列宽表。

## 4. 扩展到完整队列

移除 `--limit` 即可：

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 12
```

此前十位受试者的有效缓存会被复用。

## 5. 选择分析入口

- 区域级整理和长格式模型：`cortical_long.tsv`。
- 每位受试者一行的建模矩阵：`all_features_wide.tsv`。
- 全部皮层下结构：`aseg_long.tsv`。
- eTIV 等全局测量：`global_measures_long.tsv`。

::: tip 连接键
区域级表格应按 `atlas`、`hemisphere` 和 `label` 连接，不要使用行号或假设固定排序。
:::
