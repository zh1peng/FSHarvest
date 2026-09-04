# 输出与数据表

FSHarvest 同时提供规范化 long table、便于建模的 wide table、逐受试者缓存和运行审计文件。

## 输出结构

```text
OUTPUT/
├── subjects.tsv
├── cortical_long.tsv
├── aseg_long.tsv
├── global_measures_long.tsv
├── all_features_wide.tsv
├── atlas_manifest.tsv
├── run_metadata.json
├── all_qc.html
├── wide/
│   ├── dk68.tsv
│   └── ATLAS.tsv
└── per_subject/FOLDER_ID/
    ├── label/
    ├── stats/
    ├── cortical.tsv
    ├── aseg.tsv
    ├── global.tsv
    ├── qc/ATLAS_inflated_4view.png
    ├── qc/ATLAS_inflated_4view.png.json
    ├── extract.log
    └── status.json
```

## 队列级文件

| 文件 | 用途 |
| --- | --- |
| `subjects.tsv` | 每位受试者的状态、来源、QC 和错误信息 |
| `cortical_long.tsv` | 规范皮层长表，也是皮层输出的 source of truth |
| `aseg_long.tsv` | `aseg.stats` 中的全部结构行 |
| `global_measures_long.tsv` | 全部全局 `# Measure` 记录 |
| `all_features_wide.tsv` | 每位受试者一行，组合全部特征家族 |
| `atlas_manifest.tsv` | Atlas 定义、预期数量和完成度 |
| `run_metadata.json` | 运行 ID、参数、时间、软件与输入指纹 |

## Long 与 wide 的选择

分析或检查区域级数据时优先使用 `cortical_long.tsv`，并以 `atlas + hemisphere + region`
作为连接键。不要假设不同 Atlas 的行顺序一致。

每个 Atlas 也有独立的宽表，例如：

```text
L_bankssts_thickavg
```

合并后的 `all_features_wide.tsv` 会加入 Atlas 前缀，避免同名区域碰撞：

```text
dk68__L_bankssts_thickavg
```

## 状态与可信聚合

只有本次运行状态为 `OK`，并且序列化结果和外部产物重新验证通过的受试者，才会进入可信的队列特征表。
部分结果仍会保留，方便诊断和恢复，但不会被静默当作完整数据。

::: info 大型宽表
宽表按流式方式聚合，不会把整个队列矩阵同时保存在内存中；但多 Atlas 队列的最终 TSV 仍可能非常宽，需要预留磁盘空间。
:::

::: warning 共享前检查
表格、状态、运行元数据、日志和 QC HTML 可能包含受试者标识及本机绝对路径。请把输出目录按受限数据处理，并在共享或公开前完成审查与去标识化。
:::
