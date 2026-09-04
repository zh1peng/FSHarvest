# 批量提取 FreeSurfer 指标

先用 10 位受试者检查目录和运行环境，确认无误后再处理完整队列。

## 1. 初始化 FreeSurfer

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
source "$FREESURFER_HOME/SetUpFreeSurfer.sh"
```

确认三个命令可以找到：

```bash
command -v recon-all
command -v mri_surf2surf
command -v mris_anatomical_stats
```

示例输出：

```text
/usr/local/freesurfer/7.4.1/bin/recon-all
/usr/local/freesurfer/7.4.1/bin/mri_surf2surf
/usr/local/freesurfer/7.4.1/bin/mris_anatomical_stats
```

## 2. 先用 10 位受试者试运行 DK68

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 4 \
  --limit 10
```

成功结束时，最后一行会给出 `OK` 和非 `OK` 的数量：

```text
Finished: 10 OK, 0 non-OK. Output: /data/derived/fsharvest
```

## 3. 检查状态

```bash
cut -f1,2,7,17 /data/derived/fsharvest/subjects.tsv | column -t -s $'\t'
```

示例：

```text
subject_id  folder_id   status  errors
example-01  example-01  OK
example-02  example-02  PARTIAL  dk68/rh: missing standard FreeSurfer stats
```

理想情况下，每位受试者的 `status` 都应为 `OK`。出现 `PARTIAL` 或 `FAILED` 时，
请先查看对应的 `extract.log` 和 `status.json`。在确认失败原因前，不要直接使用队列宽表。

## 4. 扩展到完整队列

移除 `--limit`：

```bash
fsharvest /data/study/freesurfer \
  /data/derived/fsharvest \
  --jobs 12
```

前十位受试者中通过检查的缓存会被复用。

## 5. 选择要使用的结果表

- 区域级检查或长格式分析：`cortical_long.tsv`；
- 每位受试者一行的建模数据：`all_features_wide.tsv`；
- 全部皮层下结构记录：`aseg_long.tsv`；
- eTIV 等全局指标：`global_measures_long.tsv`。

::: tip 合并区域级结果
请使用 `atlas`、`hemisphere` 和 `region` 三个字段，不要使用行号，也不要假设不同分区
具有相同排序。
:::
