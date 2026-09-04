# 工具概述

FSHarvest 从多个受试者的 FreeSurfer 结果中提取脑区指标，整理为统一的 TSV 表格，
并记录每位受试者的处理状态、软件版本、运行参数和文件校验值。

## 输入目录要求

输入目录的直接子目录通常对应一位受试者：

```text
subjects/
├── sub-001/
│   ├── label/
│   ├── mri/
│   ├── scripts/
│   ├── stats/
│   └── surf/
└── sub-002/
    └── ...
```

目录名不必以 `sub-` 开头。FSHarvest 通过 `stats/aseg.stats`、`surf/lh.white` 或
`scripts/recon-all.log` 等关键文件判断一个目录是否为 FreeSurfer 受试者结果。
数据存在嵌套层级时使用 `--recursive`。如果不同路径下存在同名目录，程序会停止运行，
避免它们写入同一个输出位置。

## 可提取的指标

- 受试者 ID、文件夹名称、重建所用的 FreeSurfer 版本，以及 `recon-all.done` 是否存在；
- 各皮层区域的顶点数、表面积、灰质体积、平均厚度、厚度标准差和曲率指标；
- `aseg.stats` 中的所有结构记录；
- `aseg.stats` 中的全局测量，包括估计颅内容积（eTIV）；
- 左右半球的表面孔洞数（surface holes）、Euler 数及其总和；
- 所用脑区分区（atlas）、运行参数、模板版本和输入文件校验信息。

## 处理流程

```text
识别受试者目录
      │
      ├── FreeSurfer 内置分区 ── 读取已有的 aparc / aparc.a2009s 统计文件
      │
      └── 外部分区 ── 将标注投影到受试者表面 ── 计算脑区统计量
                                                │
                                                ▼
                               检查区域名称、区域数量和文件完整性
                                                │
                                                ▼
                               生成长表、宽表、状态文件和 QC 文件
```

## 默认不会修改原始结果

默认运行只读取输入目录。外部分区生成的 `.annot`、`.stats` 和缓存保存在
`OUTPUT/per_subject/`，不会写入原始 FreeSurfer 结果。

只有显式传入 `--export-to-freesurfer` 时，通过检查的外部分区文件才会复制回输入目录。
若目标位置已有不同内容，FSHarvest 会报告冲突并拒绝覆盖。

::: warning 输出目录必须独立
输出目录不能等于输入目录，也不能位于输入目录内部，否则派生文件可能被误识别为新的输入。
:::
