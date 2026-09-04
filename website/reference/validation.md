# 验证与兼容性

## 已验证基线

真实数据基线使用：

- Linux x86_64；
- FreeSurfer 7.4.1 运行时；
- FreeSurfer 7.2.0 产生的重建；
- 10 位真实受试者；
- 内置和外部 Atlas、缓存复用、导出保护与头less QC。

基线验证覆盖 Atlas 预期区域数、九类皮层测量的有限值、长/宽表聚合、四视图 PNG、
相对路径 HTML 图集以及 annotation/stats 的复用路径。

## 1.0.0 发布候选

1.0.0 增加了缓存内容校验、无依赖 annotation 解析、固定区域名称集合、逐产物 checksum、
更强的 `aseg` 完整性检查、可信结果聚合和运行隔离。

本地回归套件包含 33 项测试，并在 Python 3.12 上通过 Ruff 与 mypy。

::: warning 当前边界
真实 FreeSurfer 提取和 Linux shell gates 仍需在最终 release commit 上重复后，才能把基线结果视为 1.0.0 正式发布声明。
现有数据也不能证明对所有 FreeSurfer 版本兼容，尤其不包括 FreeSurfer 8.x。
:::

完整、可审计的记录见仓库根目录 [`VALIDATION.md`](https://github.com/zh1peng/FSHarvest/blob/main/VALIDATION.md)。
