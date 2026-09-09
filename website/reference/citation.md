# 引用与许可证

## 论文中如何描述 FSHarvest {#methods}

下面提供可复制的英文 Methods 段落。点击代码块右上角的复制按钮，然后按实际研究流程修改。
FSHarvest 从已有的 FreeSurfer 重建结果中提取指标；重建方法和质控流程应另外说明。

### 通用写法

将方括号内容替换为实际使用的版本、图谱和分析指标，并补充相应的软件及图谱文献引用：

<div class="methods-copy">

```text
Regional morphometric measures were extracted from existing FreeSurfer reconstructions using FSHarvest (version [FSHARVEST_VERSION]; https://github.com/zh1peng/FSHarvest). Cortical measures were obtained for the [ATLAS_NAMES] parcellation(s), and [MEASURES_USED_IN_ANALYSIS] were retained for analysis. FSHarvest organized the extracted measurements into participant-level tables, aligning cortical measurements by atlas, hemisphere, and region name. Software versions, processing status, and run parameters were recorded for reproducibility.
```

</div>

`MEASURES_USED_IN_ANALYSIS` 可填写研究实际使用的指标，例如 `regional mean cortical thickness,
surface area, and gray matter volume`。如果只分析皮层下指标，应相应改写皮层图谱的句子。
重建版本可从 `subjects.tsv` 的 `fs_version` 查看；执行提取时调用的 FreeSurfer 版本见
`run_metadata.json`。二者可能不同，写作时请区分。

### 六图谱示例的具体写法

以下段落对应本站[10 位受试者的六图谱示例](../tutorials/ten-subject-example#six-atlas)：
FSHarvest 1.0.4，输入重建版本为 FreeSurfer 7.2.0，提取环境为 FreeSurfer 7.4.1。
复制用于论文时，请替换为自己实际使用的版本、图谱和流程。

<div class="methods-copy">

```text
Regional morphometric measures were extracted using FSHarvest (version 1.0.4; https://github.com/zh1peng/FSHarvest) from reconstructions previously generated with FreeSurfer 7.2.0. Six cortical parcellations were included: Desikan-Killiany (68 regions), DK308, Destrieux (148 regions), and Schaefer parcellations with 100, 200, and 300 regions. Desikan-Killiany and Destrieux measurements were read from the existing FreeSurfer statistics files. DK308 and Schaefer annotations were mapped from their source template surfaces to each participant's cortical surfaces using mri_surf2surf, and regional statistics were computed using mris_anatomical_stats in FreeSurfer 7.4.1. Outputs included regional cortical thickness, surface area, gray matter volume, aseg structure volumes, and global measures. Measurements were aggregated across participants by atlas, hemisphere, and region name, with processing status and run parameters retained alongside the results.
```

</div>

这次示例没有启用 FSHarvest 的 QC 绘图，也没有执行重建。不要把运行状态为 `OK` 写成
“所有受试者均通过人工质控”；论文中的质控、排除标准及后续统计处理应依据实际工作补充。

### 需要说明缺失值处理时

下面描述的是 FSHarvest 的汇总行为。若后续分析进行了插补、名称标准化或受试者排除，需另行说明：

<div class="methods-copy">

```text
FSHarvest retained successfully parsed measurements with unambiguous identifiers even when other measurements were unavailable. Original region names were preserved, and missing measurements were left empty in the exported tables without imputation. Differences from expected region names and processing errors were recorded for review.
```

</div>

## 引用 FSHarvest

软件引用信息保存在 [`CITATION.cff`](https://github.com/zh1peng/FSHarvest/blob/main/CITATION.cff)。
可在 GitHub 仓库首页点击 **Cite this repository**，复制 BibTeX 或 APA 格式的引用。
请引用实际使用的版本；本站运行示例使用 [v1.0.4](https://github.com/zh1peng/FSHarvest/releases/tag/v1.0.4)。

当前软件信息：

| 项目 | 内容 |
| --- | --- |
| 名称 | FSHarvest |
| 版本 | 1.0.4 |
| 发布日期 | 2026-09-09 |
| 代码许可证 | MIT |

## 引用脑区分区

除 FSHarvest 外，还应引用 FreeSurfer 及实际使用的各套脑区图谱的原始论文，包括内置的
DK68、Destrieux。随程序提供的外部图谱，其来源、提交版本、DOI、标准模板和再分发许可证记录在：

- [`atlases/README.md`](https://github.com/zh1peng/FSHarvest/blob/main/atlases/README.md)
- [`THIRD_PARTY_NOTICES.md`](https://github.com/zh1peng/FSHarvest/blob/main/THIRD_PARTY_NOTICES.md)

## 许可证范围

FSHarvest 源代码采用 MIT 许可证。仓库附带的 `.annot` 文件继续受其原始许可证约束；MIT 许可证不会替代分区作者要求的科学引用或数据使用条款。分发或发表结果前，请按实际使用的分区逐项核对。
