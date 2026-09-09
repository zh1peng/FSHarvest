# 五分钟快速开始

下面以 **FSHarvest 1.0.4** 在 linux212 上前 10 位受试者的真实运行作为示例。
默认读取 DK68，5 个并行任务，不生成 QC 图片。先完成[安装](./installation)，并确认
`fsharvest --version` 显示 1.0.4 或更高版本。

## 1. 复制命令或保存为脚本

修改输入、输出和 FreeSurfer 路径后运行。输入目录的下一层应是受试者目录，输出目录要放在
输入目录之外。代码块右上角的按钮可以复制全部代码；两个选项执行相同的提取任务。

::: code-group

```bash [CLI：直接在终端运行]
subjects_dir=/data/study/freesurfer
output_dir=/data/derived/fsharvest-dk68-example
freesurfer_home=/usr/local/freesurfer/7.4.1

fsharvest "$subjects_dir" "$output_dir" \
  --freesurfer-home "$freesurfer_home" \
  --atlases dk68 --jobs 5 --limit 10
```

<<< @/public/examples/run_fsharvest_example.sh{bash} [SH：run_fsharvest_example.sh]

:::

也可以<a href="/FSHarvest/examples/run_fsharvest_example.sh" download>下载同一份 SH 脚本</a>，修改其中的路径后执行：

```bash
bash run_fsharvest_example.sh
```

修改路径后，我们已在 linux212 上实际运行此脚本，10/10 为 `OK`；生成的三类长表和总宽表与 CLI
运行结果完全一致。

`--limit 10` 从程序识别到的受试者中，按目录名排序取前 10 位；并行任务按完成顺序报告进度。
`--atlases dk68` 在这里显式写出，省略时也默认选择 DK68。无需在脚本中添加 `echo`、
`tee` 或 FreeSurfer 初始化步骤，FSHarvest 会准备环境、显示进度并保存日志。

## 2. 运行时会看到什么

以下为 2026-09-09 的首次运行记录。原始受试者名称和私有路径已替换为 `example-01` 至
`example-10` 及示例路径；时间、完成顺序和状态保持原样。执行提取的 FreeSurfer 为 7.4.1，
输入重建版本为 7.2.0。

::: details 展开完整终端输出：横幅、10 位受试者和最终汇总
<<< @/public/examples/v1.0.4/dk68-run.log{text}
:::

这次运行的关键结果是：

```text
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
```

上面三行是终端记录的节选，省略了 `[DONE]` 前的时间戳。`[CHECK]` 和 `[PREPARE]` 表示正在
检查输入与模板；`[EXTRACT]` 在首位受试者完成前出现；`[1/10]` 至 `[10/10]` 显示已完成数量；
`[AGGREGATE]` 表示正在写汇总表。`OK` 是程序检查状态，不能替代对重建边界的人工评估。

## 3. 总日志已经自动保存

终端开头和结尾都会显示 `Run log:`。每次调用会在输出目录下生成一份新日志，里面包含
横幅、环境准备、进度、错误和退出码；重复运行不会覆盖上一次的总日志。

```bash
# 列出各次运行的总日志
ls -lt /data/derived/fsharvest-dk68-example/logs/

# 从终端复制 Run log: 后的实际路径，查看完整记录
less /data/derived/fsharvest-dk68-example/logs/run_20260909T011641_543148Z_74b3105e.log
```

上面的文件名来自本次示例，你的时间戳和后缀会不同。下载<a href="/FSHarvest/examples/v1.0.4/dk68-run.log" download>首次运行总日志</a>
或<a href="/FSHarvest/examples/v1.0.4/dk68-cached-run.log" download>缓存复用总日志</a>可对照查看。
逐受试者的详细命令仍保存在 `per_subject/受试者目录名/extract.log`。

## 4. 确认输出表

本次前 10 位受试者实际生成：

| 文件 | 数据行数，不含表头 | 列数 |
| --- | ---: | ---: |
| `subjects.tsv` | 10 | 30 |
| `cortical_long.tsv` | 680 | 18 |
| `aseg_long.tsv` | 450 | 16 |
| `global_measures_long.tsv` | 200 | 11 |
| `wide/dk68.tsv` | 10 | 622 |
| `all_features_wide.tsv` | 10 | 687 |
| `region_differences.tsv` | 0 | 7 |

680 = 10 位受试者 × 68 个 DK 区域。差异报告只有表头，表示本次未报告名称差异。
这些是此数据集的实测数量，其他数据的 aseg 或全局指标数量可能不同。

```bash
column -t -s $'\t' /data/derived/fsharvest-dk68-example/subjects.tsv | less -S
```

状态为 `PARTIAL` 或 `FAILED` 时，查看 `subjects.tsv` 的 `errors`、逐受试者 `status.json`
和 `extract.log`。已成功解析、对应关系明确的数据仍会进入汇总；缺失脑区在对应列留空。
详见[输出表及真实数据示例](./outputs)和[10 位受试者完整示例](../tutorials/ten-subject-example)。

## 5. 重复运行与处理全部受试者

重复执行第 1 步的同一条命令，本例的 10 位受试者全部命中缓存，进度行增加 `(cached)`。
汇总表仍会重新写出，总日志另存为新文件。

处理全部受试者时，建议使用另一个输出目录，并移除 `--limit 10`：

```bash
fsharvest /data/study/freesurfer /data/derived/fsharvest-dk68-full \
  --freesurfer-home /usr/local/freesurfer/7.4.1 \
  --atlases dk68 --jobs 5
```

汇总表始终对应本次选中的受试者和图谱。在全部受试者的输出目录再次执行 `--limit 10`，
会把汇总表改写成这 10 位的结果；采用独立试运行目录可避免这种混淆。

需要 DK308、Destrieux 和 Schaefer？继续看[六图谱 CLI 与 SH 实例](../tutorials/ten-subject-example#six-atlas)。
