# 批量查看 QC 图

下面以 DK68 和 Schaefer100 为例，先为 10 位受试者生成质量控制（QC）图片，再说明如何
检查异常结果。

## 1. 先对少量受试者生成图片

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

每位受试者正常完成后，终端会显示生成的 PNG 数量：

```text
[QC 1/10] example-01: 2 PNGs
```

## 2. 打开队列页面

```bash
xdg-open OUTPUT/all_qc.html
```

在页面中切换不同脑区分区，并使用受试者 ID 搜索。先浏览多数受试者，了解本队列中
通常的图像外观，再检查明显异常的个体。

![实际 all_qc.html 页面截图](/examples/qc-report-example.png)

## 3. 查看异常受试者的图片和日志

```text
OUTPUT/per_subject/FOLDER_ID/qc/ATLAS_inflated_4view.png
OUTPUT/per_subject/FOLDER_ID/qc/ATLAS_inflated_4view.png.json
OUTPUT/per_subject/FOLDER_ID/extract.log
OUTPUT/per_subject/FOLDER_ID/status.json
```

PNG 的 `.json` 文件记录输入表面、分区标注、DPI 和 run ID。它可以帮助确认图片是否对应
当前输入和当前运行。

## 4. 根据问题进行处理

- 没有生成图片：检查 QC 依赖、`qc_status` 和日志；
- 分区覆盖明显异常：检查 `.annot`、`sphere.reg` 和 FreeSurfer 版本；
- white/pial 边界可疑：在 Freeview 中进一步检查；
- 只需更清晰的图片：提高 `--qc-dpi`，无需重新定义提取指标。

::: info 预留足够内存
生成表面图片通常比提取表格占用更多内存。对于大型队列，可以只为必要的分区生成图片，
或先使用 `--limit` 对少量受试者测试。
:::
