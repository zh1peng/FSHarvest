# 生成表面 QC 图

FSHarvest 可以为所选脑区分区生成四视图 PNG，并在 `all_qc.html` 中集中显示所有受试者。
复制或移动整个输出目录后，HTML 仍可通过相对路径打开其中的图片。

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

每张图片依次包含左外侧、左内侧、右外侧和右内侧。默认使用 inflated 表面，也可以改为：

```bash
--qc-surface pial
--qc-surface white
--qc-dpi 150
```

`--qc-dpi` 的最小值为 72。以下 DK68 图片是 `linux212` 使用 FreeSurfer 7.4.1
生成的真实输出，没有包含受试者文字标识：

![DK68 inflated 表面四视图真实输出](/examples/dk68-inflated-example.png)

同一次运行生成的 Schaefer100 图片如下：

![Schaefer100 inflated 表面四视图真实输出](/examples/schaefer100-inflated-example.png)

## 在浏览器中查看所有受试者

```bash
xdg-open OUTPUT/all_qc.html
```

打开页面后，可以切换不同脑区分区、按受试者 ID 搜索，并点击缩略图查看原图。
下面是实际生成页面的截图；受试者名称已替换为 `example-01`：

![all_qc.html 页面截图](/examples/qc-report-example.png)

每张 PNG 都有一个同名 `.json` 文件，其中记录本次 run ID、表面类型、DPI、输入表面和
`.annot` 文件的 SHA-256。HTML 只显示与当前运行及当前输入一致的图片；本次没有请求 QC
或绘图失败时，旧图片不会代替新结果出现在报告中。

## 应该检查什么

- 分区是否覆盖预期的皮层区域；
- 左右半球是否缺失或明显错位；
- 内侧壁区域是否异常；
- 是否有个别受试者与队列中多数图像明显不同。

::: danger 这些图片不能替代 Freeview 检查
四视图图片适合快速发现明显的投影或重建异常，但不能用于判断细微的 white/pial 边界错误。
最终质控仍应在 Freeview 中完成。
:::
