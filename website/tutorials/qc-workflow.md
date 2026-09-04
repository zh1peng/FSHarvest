# 教程：QC 工作流

这里用 DK68 与 Schaefer100 建立一个成本可控的队列质控流程。

## 1. 先对少量受试者绘图

```bash
fsharvest INPUT OUTPUT \
  --jobs 4 \
  --limit 10 \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100 \
  --qc-surface inflated \
  --qc-dpi 100
```

## 2. 打开队列图集

```bash
xdg-open OUTPUT/all_qc.html
```

按 Atlas 切换标签页，并使用 subject ID 过滤。先建立“正常样本”的视觉范围，再定位明显离群者。

## 3. 回到逐受试者记录

异常图片对应：

```text
OUTPUT/per_subject/FOLDER_ID/qc/ATLAS_inflated_4view.png
OUTPUT/per_subject/FOLDER_ID/extract.log
OUTPUT/per_subject/FOLDER_ID/status.json
```

## 4. 决定后续动作

- 图片缺失：检查绘图依赖、状态和日志。
- Atlas 覆盖异常：重新检查 annotation、sphere.reg 与 FreeSurfer 版本。
- white/pial 边界可疑：转到 Freeview 进行交互检查。
- 仅提高输出清晰度：增加 `--qc-dpi`，不需要改变提取表格。

::: info 内存规划
表面渲染通常比表格提取占用更多内存。大型队列可以限制 `--qc-atlases`，或先对代表性子集绘图。
:::
