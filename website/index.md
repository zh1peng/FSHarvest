<img class="fsharvest-doc-logo" src="/fsharvest-logo.png" alt="FSHarvest 标志">

# 批量提取 FreeSurfer 脑区指标

FSHarvest 是一个在 Linux 上运行的命令行工具，用于批量整理多个受试者的 FreeSurfer 结果。
指定输入目录和输出目录后，程序会提取皮层、皮层下和全局指标，计算 Euler 数，并记录
FreeSurfer 版本与运行参数。结果保存为长表、宽表和质量控制（QC）文件，便于后续统计分析。

## 处理流程

<div class="harvest-path">
FreeSurfer 受试者结果 → 识别受试者 → 提取所选脑区分区 → 检查结果完整性 → 生成 TSV 表格、QC 图片和运行记录
</div>

FSHarvest 默认不会修改原始 FreeSurfer 结果。外部分区生成的 `.annot`、`.stats` 和缓存
均保存在输出目录中。只有显式使用 `--export-to-freesurfer` 时，程序才会把通过检查的文件
复制到受试者目录；已有的不同文件不会被覆盖。

## 快速开始

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
bash install.sh
fsharvest /path/to/subjects /path/to/output --jobs 12
```

一次正常运行会显示受试者数量、FreeSurfer 版本和处理结果：

```text
Discovered 1 subjects; jobs=1; FreeSurfer=freesurfer-linux-ubuntu22_x86_64-7.4.1-20230614-7eb8460
[1/1] example-01: OK
Finished: 1 OK, 0 non-OK. Output: /data/derived/fsharvest-example
```

## 使用指南

- 第一次使用：阅读[五分钟快速开始](/guide/quick-start)。
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
