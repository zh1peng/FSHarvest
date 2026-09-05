# 验证范围与兼容性

## 已验证的环境

目前的真实数据验证使用：

- Linux x86_64；
- FreeSurfer 7.4.1 运行环境；
- 由 FreeSurfer 7.2.0 完成重建的受试者目录；
- 10 位真实受试者；
- 内置分区、外部分区、缓存复用、导出保护和无图形界面的 QC 绘图。

验证内容包括分区预期脑区数、九类皮层测量值、长表与宽表、四视图 PNG、使用相对路径的 HTML 报告，以及 `.annot` 和统计文件的安全复用。

## 内置分区读取与重新计算的一致性

针对 10 位受试者，DK68 与 Destrieux 均同时走了两条路径：直接读取原生
`aparc.stats` / `aparc.a2009s.stats`，以及从同一受试者 `.annot`、white/pial/thickness
表面重新运行 `mris_anatomical_stats`。双半球共比较 2,160 行脑区结果和九类指标，合计
19,440 个数值。全部数值在 FreeSurfer 统计文件的序列化精度上完全相等，最大绝对误差和
最大相对误差均为 0，也全部通过 `atol=rtol=1e-12`。

原生统计文件由 FreeSurfer 7.2.0 生成，重新计算使用 FreeSurfer 7.4.1，因此这项结果还覆盖
了该数据集上的跨版本一致性。该检查直接使用受试者已有 `.annot`，验证的是统计量计算路径；
它不等同于对 `mri_surf2surf` 分区投影本身的验证。仓库中的
`validation/validate_builtin_recompute.py` 可以重复执行完整检查。

## 1.0.0rc1 的检查结果

本地回归测试共 45 项，并通过 Python 3.12、Ruff 和 mypy 检查。在 `linux212` 上还完成了：

- 45 项回归测试；
- 真实 DK68 与 Schaefer100 提取；
- QC 图片和 HTML 报告生成；
- 缓存重跑与损坏缓存重算；
- 与独立计算结果进行数值比较。

第二轮还在真实 FreeSurfer 环境中验证了同一完整命令连续导出、导出文件改动后的冲突保护、
三人汇总缩小为 `--limit 1`、取消分区后的旧宽表归档，以及预先存在的 `OUTPUT/work` 文件保留。

网站中的终端输出和 QC 示例也来自 `linux212` 上的一次真实运行，受试者名称已替换为 `example-01`，不包含原始文件路径。

## 当前适用边界

这些结果说明上述环境已经验证，不代表所有 FreeSurfer 版本和集群配置都兼容。FreeSurfer 8.x 尚未纳入当前验证范围。在新环境中使用时，请先运行少量受试者，并检查 `subjects.tsv`、脑区数量和 QC 图片。

完整验证方法与记录见仓库根目录的 [`VALIDATION.md`](https://github.com/zh1peng/FSHarvest/blob/main/VALIDATION.md)。
