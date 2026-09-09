<img class="fsharvest-doc-logo" src="/fsharvest-logo.png" alt="FSHarvest 标志">

# 批量提取 FreeSurfer 脑区指标

FSHarvest 是一个在 Linux 上运行的命令行工具，用于批量整理多个受试者的 FreeSurfer 结果。
指定输入目录和输出目录后，程序会提取皮层、皮层下和全局指标，计算 Euler 数，并记录
FreeSurfer 版本与运行参数。结果保存为长表和宽表，便于后续统计分析；质量控制（QC）图片可按需生成。

## 处理流程

<div class="harvest-path">
FreeSurfer 受试者结果 → 识别受试者 → 提取所选脑区分区 → 检查结果完整性 → 生成 TSV 表格和运行记录（可选 QC 图片）
</div>

FSHarvest 默认不会修改原始 FreeSurfer 结果。外部分区生成的 `.annot`、`.stats` 和缓存
均保存在输出目录中。只有显式使用 `--export-to-freesurfer` 时，程序才会把通过检查的文件
复制到受试者目录；已有的不同文件不会被覆盖。

## 安装后运行

先按照[安装说明](/guide/installation)获取仓库、安装命令并设置 `PATH`。安装完成后运行：

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
fsharvest /path/to/subjects /path/to/output --jobs 12
```

1.0.4 会自动显示 ASCII 横幅、版本和开发者，报告阶段进度，并保存整次运行的总日志。
下面摘自 linux212 上前 10 位受试者的真实 DK68 运行（省略时间戳和中间行，路径已替换）：

```text
FSHarvest v1.0.4 | FreeSurfer regional feature extraction
Developer: zh1peng
[EXTRACT] Starting 10 subjects; progress is reported after each subject finishes.
...
[10/10] example-10: OK
[DONE] Finished: 10 OK, 0 non-OK across all requested phases.
Table status: OK=10, PARTIAL=0, FAILED=0, NOT_RUN=0
Run exit code: 0
Run log: /data/derived/fsharvest-dk68-example/logs/run_20260909T011641_543148Z_74b3105e.log
```

## 使用指南

- 第一次使用：阅读[五分钟快速开始](/guide/quick-start)。
- 复制 CLI 或下载 SH 脚本，并对照实际结果：阅读[10 位受试者真实运行示例](/tutorials/ten-subject-example)。
- 查看输入目录要求和工具范围：阅读[工具概述](/guide/introduction)。
- 选择 Schaefer、Glasser 等脑区分区：阅读[脑区分区与处理方式](/guide/atlases)。
- 了解每个表格的内容：阅读[输出与数据表](/guide/outputs)。
- 生成并批量查看 QC 图片：阅读[批量查看 QC 图](/tutorials/qc-workflow)。
- 在计算集群上运行：阅读[在 Slurm 上运行](/tutorials/slurm)。

::: tip 默认仅提取 DK68
未指定 `--atlases` 时，FSHarvest 只读取 DK68。其他分区需要显式选择。
:::

::: warning 自动检查不能替代 Freeview 质控
区域数量和名称检查只能发现明显缺失或错配。white 和 pial 边界仍需在 Freeview 中检查。
:::
