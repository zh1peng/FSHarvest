# 输出与数据表

FSHarvest 生成长表（long format）、宽表（wide format）、逐受试者缓存和运行记录。
下列片段来自 `linux212` 上的真实结果；公开展示时已将受试者名称和路径替换。

## 输出目录

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
│   └── schaefer100.tsv
├── archive/RUN_ID/wide/          # 上一次运行中已取消选择的宽表
└── per_subject/example-01/
    ├── label/
    ├── stats/
    ├── cortical.tsv
    ├── aseg.tsv
    ├── global.tsv
    ├── qc/dk68_inflated_4view.png
    ├── qc/dk68_inflated_4view.png.json
    ├── extract.log
    └── status.json
```

选择外部分区时，程序会创建名称唯一的 `.fsharvest-work-*` 临时目录。该目录及其中的符号链接
会在正常退出、失败或中断后清理。程序不会删除输出目录中原本存在的 `work/` 或其他目录。

## 队列级文件

| 文件 | 内容 |
| --- | --- |
| `subjects.tsv` | 每位受试者的整体状态、FreeSurfer 版本、Euler 数、行数和错误信息 |
| `cortical_long.tsv` | 所选分区的全部皮层区域和九类皮层指标；区域级分析建议优先使用此表 |
| `aseg_long.tsv` | `aseg.stats` 中每个结构的体积及其他原始字段 |
| `global_measures_long.tsv` | eTIV、BrainSegVol 和 surface holes 等 `# Measure` 记录 |
| `wide/ATLAS.tsv` | 每个分区一张宽表，每位受试者一行 |
| `all_features_wide.tsv` | 所选分区的九类皮层指标、皮层下结构体积和全局指标；不复制 `aseg.stats` 的其他非体积列 |
| `atlas_manifest.tsv` | 分区定义、预期区域数、区域名称 SHA-256 和完整受试者数 |
| `run_metadata.json` | run ID、时间、参数、软件版本、分区校验值和输入指纹 |

## `cortical_long.tsv` 示例

为了便于阅读，下例只显示部分列：

```text
folder_id   subject_id  atlas  hemisphere  region                      numvert  surfarea  grayvol  thickavg
example-01  example-01  dk68   lh          bankssts                    1283     864       1975     2.501
example-01  example-01  dk68   lh          caudalanteriorcingulate     1332     858       2481     2.694
example-01  example-01  dk68   lh          caudalmiddlefrontal         3908     2495      7550     2.750
```

`folder_id` 是输入受试者目录名，程序要求它在一次运行中唯一；`subject_id` 来自 FreeSurfer
统计文件头，可能在不同目录或多次扫描之间重复。

合并两张受试者级脑区结果表时，请使用 `folder_id`、`atlas`、`hemisphere` 和 `region`
共同匹配，并检查这些字段在每张表中是否唯一。只有合并不含受试者维度的脑区说明表时，
才使用 `atlas`、`hemisphere` 和 `region`。存在多次扫描时，应使用能够唯一标识该次扫描的
`folder_id`，不能只用参与者编号。

## 宽表列名示例

单个分区的宽表使用半球、区域和指标组成列名：

```text
L_bankssts_thickavg
R_bankssts_thickavg
```

`all_features_wide.tsv` 再增加分区前缀，避免不同分区出现同名列：

```text
dk68__L_bankssts_thickavg
schaefer100__L_7Networks_LH_Vis_1_thickavg
aseg__Left-Hippocampus__volume_mm3
global__eTIV
```

## 如何判断结果是否进入汇总表

输出目录中的 `subjects.tsv`、长表、宽表、分区清单和运行记录始终表示**本次命令**选择的
受试者和分区，并不是对历史结果的自动追加。完整队列之后在同一输出目录执行 `--limit 10`，
会把这些汇总文件改写为本次十位受试者的结果；逐受试者缓存仍可保留并在后续复用。

当前版本使用严格汇总：只有本次运行状态为 `OK`，且表格和外部分区文件重新检查通过的受试者，
才会进入队列级长表和宽表。状态为 `PARTIAL`、`FAILED` 或 `NOT_RUN` 的受试者仍保留
逐受试者文件，但不会进入本次队列汇总。

`subjects.tsv` 目前记录受试者整体状态，没有单独的受试者 × 分区状态表。如果多分区运行失败，
请结合 `errors`、逐受试者 `status.json` 和 `extract.log` 定位具体分区及半球。

如果本次减少了所选分区，程序会核对上一次运行记录中的 SHA-256，然后把不再选择的宽表从
`wide/` 移到 `archive/PREVIOUS_RUN_ID/wide/`。内容被修改或缺少生成记录的旧表不会被自动移动；
程序会停止并要求人工移出该文件，避免把来源不明的表误当作当前结果。

::: info 多分区会产生很宽的表
程序逐个受试者写入汇总表，不会把整个队列矩阵同时放入内存；但选择多个高分辨率分区时，
最终 TSV 仍可能包含数万列，需要预留磁盘空间并确认下游软件能够读取。
:::

::: warning 共享前检查
表格、状态文件、运行记录、日志和 QC HTML 可能包含受试者标识及本机绝对路径。
请把输出目录按受限数据处理，并在共享或公开前完成审查与去标识化。
:::
