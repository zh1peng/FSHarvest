<img class="fsharvest-doc-logo" src="/fsharvest-logo.png" alt="FSHarvest 标志">

# 从 FreeSurfer 目录收获分析就绪特征

FSHarvest 是面向研究队列的 Linux 命令行工具。给它一个包含 FreeSurfer 受试者目录的文件夹，
它会并行提取皮层、皮层下、全局测量、Euler 指标与运行来源信息，并输出可直接进入统计分析的表格。

## 一条清楚的数据路径

<div class="harvest-path">
FreeSurfer subjects → 自动发现 → 多 Atlas 提取 → 完整性验证 → TSV 特征表 + QC 图集 + 审计记录
</div>

输入重建默认只读。外部 Atlas 的投影、统计量和缓存保存在输出目录中；只有显式使用
`--export-to-freesurfer` 时，才会将通过验证的文件复制回受试者目录。

## 三行开始

```bash
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
bash install.sh
fsharvest /path/to/subjects /path/to/output --jobs 12
```

## 从哪里开始

- 第一次使用：先读[五分钟快速开始](/guide/quick-start)。
- 想理解输入识别与安全边界：看[FSHarvest 做什么](/guide/introduction)。
- 要选择 Schaefer、Glasser 或其他分区：看[Atlas 与投影路径](/guide/atlases)。
- 需要生成四视图图片并检查队列：看[QC 工作流](/tutorials/qc-workflow)。
- 准备在计算集群运行：看[在 Slurm 上运行](/tutorials/slurm)。

::: tip 默认选择保持克制
不传 `--atlases` 时只提取 DK68。其他 Atlas 均需显式选择，从而让日常运行更快、输出更紧凑。
:::

::: warning 自动检查不能替代表面重建质控
ROI 数量与区域名称验证可以发现缺失或错误投影，但不能代替在 Freeview 中检查 white/pial 边界。
:::
