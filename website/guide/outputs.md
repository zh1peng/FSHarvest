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
├── region_differences.tsv
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
| `atlas_manifest.tsv` | 分区定义、annot 路径、左右预期区域数和完整受试者数；curated 分区另记录区域名称 SHA-256 |
| `region_differences.tsv` | 相对图谱定义缺少的名称、多出的名称，以及队列中其他受试者有而该受试者没有的名称 |
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

汇总保留本次运行中能够明确对应、成功解析的数据，包括状态为 `PARTIAL` 或 `FAILED` 的
受试者。长表和宽表均携带 `status` 与 `errors`；进入总表不代表重建、图谱检查或 QC 已通过。
`NOT_RUN` 和其他运行留下的数据不进入本次汇总。存在非 OK 状态时，命令仍返回非零退出码。

脑区名称按原样保留。宽表列来自本次队列保留记录中名称的并集，某位受试者缺失的值留空，
不会补零，也不会把 `&` 和 `_and_` 自动合并。`region_differences.tsv` 用 JSON 名称列表记录
`missing_expected`（缺少的预期名称）、`unexpected_names`（额外名称）和
`absent_from_subject`（其他受试者有、该受试者没有的名称）。`reference` 标明是否有图谱定义
可供比较；名称差异不一定代表解剖区域不同。全队列都未观察到的预期脑区只列在差异报告中，
不会凭空创建宽表列。

损坏、缺失、校验和不符或表头无法解析时，只跳过对应的受试者文件。行格式错误、非法数值
或重复键只排除受影响的记录，重复键的所有冲突记录均排除，不选择其中一条覆盖另一条。
aseg 的分割 ID 和结构名、全局指标的 measure 和 metric 均检查歧义。
其他文件、脑区和受试者继续汇总，原因写入 `errors`，原始逐受试者 TSV 不改写。

`subjects.tsv` 目前记录受试者整体状态，没有单独的受试者 × 分区状态表。如果多分区运行失败，
请结合 `errors`、逐受试者 `status.json` 和 `extract.log` 定位具体分区及半球。

如果本次减少了所选分区，程序会核对上一次运行记录中的 SHA-256，然后把不再选择的宽表从
`wide/` 移到 `archive/PREVIOUS_RUN_ID/wide/`。内容被修改或缺少生成记录的旧表不会被自动移动；
程序会停止并要求人工移出该文件，避免把来源不明的表误当作当前结果。

::: info 多分区会产生很宽的表
程序使用运行结束后清理的临时 TSV，保证长表和宽表使用相同记录，不会把整个队列矩阵同时
放入内存。请为临时表预留磁盘空间；选择多个高分辨率分区时，最终 TSV 仍可能包含数万列。
:::

::: warning 共享前检查
表格、状态文件、运行记录、日志和 QC HTML 可能包含受试者标识及本机绝对路径。
请把输出目录按受限数据处理，并在共享或公开前完成审查与去标识化。
:::
