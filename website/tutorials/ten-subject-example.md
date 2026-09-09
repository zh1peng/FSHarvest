# 10 位受试者真实运行示例

这页把可执行命令、终端输出和结果表放在一起。示例于 **2026-09-09** 在 **linux212**
使用正式发布的 **FSHarvest 1.0.4** 运行，输入为该数据集按目录名排序的前 10 位可发现受试者。
公开示例中的名称统一替换为 `example-01` 至 `example-10`，私有路径替换为示例路径；
保留实际数值、时间和并行完成顺序。

| 项目 | 本次设置 |
| --- | --- |
| 提取环境 | Linux；FreeSurfer 7.4.1 |
| 输入重建版本 | FreeSurfer 7.2.0 |
| 被试数量 / 并行数 | 10 / 5 |
| 首个示例 | DK68：首次运行与缓存复用 |
| 扩展示例 | DK68、DK308、Destrieux、Schaefer100/200/300 |
| QC / 向 FreeSurfer 导出 | 均未启用 |

两个示例使用独立输出目录。DK68 从已有统计文件读取；六图谱示例还实际执行了外部分区
投影和统计计算。运行耗时取决于硬件、文件系统及缓存，不能把本次时间作为性能保证。

## DK68：从命令到总日志

[快速开始](../guide/quick-start)提供完全对应的 CLI / SH 两种用法。运行时无需额外的日志包装：

```bash
fsharvest /data/study/freesurfer /data/derived/fsharvest-dk68-example \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 --jobs 5 --limit 10
```

首次运行读取 10 位受试者，全部 `OK`，输出 680 行皮层结果；总日志自动保存。

::: details 首次运行的完整终端记录
<<< @/public/examples/v1.0.4/dk68-run.log{text}
:::

紧接着重复同一条命令，10 位受试者全部命中缓存，进度中显示 `(cached)`：

::: details 第二次运行：缓存命中与另一份总日志
<<< @/public/examples/v1.0.4/dk68-cached-run.log{text}
:::

`[已完成/总数]` 是完成计数，后面的受试者名才是具体对象。并行时 `example-02` 可以先于
`example-01` 完成，不影响最终按脑区名称汇聚。缓存命中后仍会按本次选择重写队列汇总表。

## 六图谱运行：包含 DK308 {#six-atlas}

以下 CLI 和 SH 执行相同任务。修改路径后复制运行，SH 版本可直接<a href="/FSHarvest/examples/run_fsharvest_multi_atlas.sh" download>下载</a>。

::: code-group

```bash [CLI：六图谱]
fsharvest /data/study/freesurfer /data/derived/fsharvest-six-atlas-example \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 dk308 destrieux schaefer100 schaefer200 schaefer300 \
  --jobs 5 --limit 10
```

<<< @/public/examples/run_fsharvest_multi_atlas.sh{bash} [SH：run_fsharvest_multi_atlas.sh]

:::

保存、修改路径后执行：

```bash
bash run_fsharvest_multi_atlas.sh
```

外部分区的投影与统计发生在每位受试者完成之前，因此 `[EXTRACT]` 与首个 `[1/10]` 之间
可能等待数分钟。可查看终端显示的总日志，或相应受试者的 `extract.log` 了解具体命令。

## 六图谱的实际结果

本次六图谱运行 **10/10 `OK`**，退出码为 **0**，`[DONE]` 记录的耗时为 **00:19:37**。
这是当前主机负载下的实测时间，包括实际投影、统计与汇总，并非预计时间。

::: details 六图谱完整总日志
<<< @/public/examples/v1.0.4/six-atlas-run.log{text}
:::

### 每个图谱提取了多少脑区

下表直接来自本次 `atlas_manifest.tsv`，左右数量是本图谱定义的预期统计行数。

| 图谱 | 左半球 | 右半球 | 每位总计 | 完整受试者 |
| --- | ---: | ---: | ---: | ---: |
| `dk68` | 34 | 34 | 68 | 10/10 |
| `dk308` | 152 | 156 | 308 | 10/10 |
| `destrieux` | 74 | 74 | 148 | 10/10 |
| `schaefer100` | 50 | 50 | 100 | 10/10 |
| `schaefer200` | 100 | 100 | 200 | 10/10 |
| `schaefer300` | 150 | 150 | 300 | 10/10 |

DK308 在本包中的有效统计区域为左侧 152、右侧 156，总计 308，并不要求左右各 154。
六图谱共 1,124 个皮层区域，每位一组，10 位合计 11,240 行。

### 与默认 DK68 相比，哪些文件变大了

下面的“行 × 列”来自实际文件，行数不含表头。增加皮层图谱后，aseg 和全局指标仍按每位
受试者保留一份，不会被重复六次。

| 文件 | DK68 | 六图谱 |
| --- | ---: | ---: |
| `subjects.tsv` | 10 × 30 | 10 × 30 |
| `cortical_long.tsv` | 680 × 18 | 11,240 × 18 |
| `aseg_long.tsv` | 450 × 16 | 450 × 16 |
| `global_measures_long.tsv` | 200 × 11 | 200 × 11 |
| `all_features_wide.tsv` | 10 × 687 | 10 × 10,191 |
| `region_differences.tsv` | 0 × 7 | 0 × 7 |

两次示例的名称差异报告都只有表头。每张图谱宽表均为 10 行；六图谱运行的 `wide/` 下有
`dk68.tsv`、`dk308.tsv`、`destrieux.tsv`、`schaefer100.tsv`、`schaefer200.tsv` 和
`schaefer300.tsv` 六个文件。
本次没有生成 QC PNG；输出目录中的 `all_qc.html` 仅说明没有可用的 QC 图片。

### 前 10 位受试者的状态

以下为六图谱首次运行的状态列片段，`cache_hit=0`；`qc_status` 为空，因为未请求 QC。

<<< @/public/examples/v1.0.4/six-atlas-subjects.tsv{text}

原始 `subjects.tsv` 还包含 `subject_id`、路径、Euler 数、错误和运行版本等字段。
长表与宽表的实际数值片段及字段含义见[输出与数据表](../guide/outputs)。

## 下载示例与核对记录

这些下载文件来自上面的真实运行。TSV 为选取的行列片段，JSON 是核对摘要，均不替代完整的
原始输出文件；受试者名和私有路径已替换，没有公开输入影像或身份映射表。

| 文件 | 用途 |
| --- | --- |
| <a href="/FSHarvest/examples/run_fsharvest_example.sh" download>DK68 SH 脚本</a> | 修改路径后运行前 10 位受试者 |
| <a href="/FSHarvest/examples/run_fsharvest_multi_atlas.sh" download>六图谱 SH 脚本</a> | 含 DK308，不启用 QC |
| <a href="/FSHarvest/examples/v1.0.4/dk68-run.log" download>DK68 首次总日志</a> / <a href="/FSHarvest/examples/v1.0.4/dk68-cached-run.log" download>缓存复用总日志</a> | 对比启动、进度、缓存与日志文件名 |
| <a href="/FSHarvest/examples/v1.0.4/six-atlas-run.log" download>六图谱总日志</a> | 查看 10 位受试者的真实完成顺序和耗时 |
| [六图谱状态片段](/examples/v1.0.4/six-atlas-subjects.tsv) | 对照状态、行数、缓存和 QC 字段 |
| [六图谱 manifest 片段](/examples/v1.0.4/six-atlas-atlas_manifest.tsv) | 核对每个图谱的预期区域数与完成数 |
| [DK68 核对摘要](/examples/v1.0.4/dk68-summary.json) / [六图谱核对摘要](/examples/v1.0.4/six-atlas-summary.json) | 查看版本、参数、行列数及公开示例来源 |

程序是否成功仍需结合退出码、`subjects.tsv` 和错误信息判断。若你的脑区名称与预期不同，
以实际名称对齐、保留已有数据，并查看 `region_differences.tsv` 中的具体差异。
