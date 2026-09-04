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

## 1.0.0rc1 发布候选

1.0.0rc1 分离了工具、缓存和输出 schema 版本，拒绝降级复用缓存，并增加 `aseg`
头校验、不可信 subject stats 拒绝、输出锁、临时链接清理和当前 run 的 QC 指纹。

本地回归套件包含 40 项测试，并在 Python 3.12 上通过 Ruff 与 mypy。`linux212` 上的
40 项回归、真实 DK68 + Schaefer100 + QC、缓存重跑、损坏缓存重算及独立数值比较也已通过。
这些结果仍需在最终提交后以该 commit SHA 重跑，才构成 release attestation。

::: warning 当前边界
真实 FreeSurfer 提取和 Linux shell gates 仍需在最终 release commit 上重复后，才能把基线结果视为 1.0.0 正式发布声明。
现有数据也不能证明对所有 FreeSurfer 版本兼容，尤其不包括 FreeSurfer 8.x。
:::

完整、可审计的记录见仓库根目录 [`VALIDATION.md`](https://github.com/zh1peng/FSHarvest/blob/main/VALIDATION.md)。
