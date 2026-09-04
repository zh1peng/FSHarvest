# FSHarvest 做什么

FSHarvest 把一个 FreeSurfer 队列目录转换为结构统一、能够直接进入统计分析的数据表，同时保留每次运行的来源、状态与校验信息。

## 输入是什么

输入目录的直接子目录通常是一位受试者：

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

目录名不必以 `sub-` 开头。FSHarvest 根据 `stats/aseg.stats`、`surf/lh.white`、
`scripts/recon-all.log` 等 FreeSurfer 特征文件识别受试者。数据存在嵌套层级时使用 `--recursive`；
如果递归扫描发现重复目录名，程序会拒绝继续，以免输出 ID 产生歧义。

## 收获哪些信息

- 受试者 ID、目录 ID、绝对路径、重建版本和 `recon-all.done` 状态。
- 皮层的九类统计量，包括面积、灰质体积、平均厚度、厚度标准差和曲率指标。
- `aseg.stats` 中的全部结构行，而不是预设的一小组皮层下结构。
- `aseg.stats` 的全部全局 `# Measure` 记录，包括 eTIV。
- 左右半球 surface holes、Euler number 及二者之和。
- Atlas 来源、运行参数、模板和文件指纹等复现信息。

## 数据如何流动

```text
发现 subjects
      │
      ├── 内置 Atlas ── 读取已有 aparc / aparc.a2009s 统计
      │
      └── 外部 Atlas ── 投影 annotation ── 计算 native-surface 统计
                                      │
                                      ▼
                         区域名称 + ROI 数量 + 文件完整性验证
                                      │
                                      ▼
                         long / wide TSV + status + QC
```

## 默认安全边界

输入重建默认只读。外部 Atlas 产生的 annotation 与统计文件写到
`OUTPUT/per_subject/`，因此重复运行可以复用缓存，也不会悄悄改变原始 FreeSurfer 目录。

只有显式传入 `--export-to-freesurfer` 时，验证通过的外部 Atlas 文件才会复制回输入重建；
若目标位置已有不同内容，FSHarvest 会报冲突并拒绝覆盖。

::: warning 输出目录必须独立
输出目录不能等于输入目录，也不能放在输入目录内部。这样可以避免递归发现输出缓存，或把派生文件误认为输入。
:::
