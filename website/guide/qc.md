# 表面 QC

FSHarvest 可以为选择的 Atlas 生成紧凑四视图 PNG，并汇总成可移动的队列级 HTML 图集。

## 安装绘图依赖

```bash
python3 -m pip install -r requirements-qc.txt
```

## 生成四视图图片

```bash
fsharvest INPUT OUTPUT \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

每张图片依次包含左外侧、左内侧、右外侧和右内侧。默认绘制 inflated surface；也可以选择：

```bash
--qc-surface pial
--qc-surface white
--qc-dpi 150
```

`--qc-dpi` 的最小值为 72。

## 队列图集

`all_qc.html` 在每次运行结束时重新生成。它为每个 Atlas 提供标签页、受试者过滤和缩略图网格，
缺失图片会被明确标出。图像 URL 全部相对于 HTML 文件，因此整个输出目录移动后仍可浏览。

## 应该检查什么

- 分区是否覆盖预期皮层范围。
- 左右半球是否明显错位或缺失。
- medial wall 是否异常扩张。
- 某位受试者是否与队列中的其他样本明显不同。

::: danger QC 的边界
这些图适合发现严重投影或重建异常，但不能替代在 Freeview 中交互检查 white/pial 边界。
:::
