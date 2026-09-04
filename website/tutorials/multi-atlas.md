# 教程：多 Atlas 分析

多 Atlas 会显著增加列数、运行时间与 QC 存储。建议从研究问题需要的尺度开始，而不是一次选择全部分区。

## 分阶段运行

先运行内置 Atlas：

```bash
fsharvest INPUT OUTPUT --jobs 12 --atlases dk68 destrieux
```

确认数据与命名后，再加入外部 Atlas：

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux schaefer100 schaefer400 glasser360
```

有效的前一阶段结果会复用。新增外部 Atlas 会在 `per_subject/` 下建立对应 annotation 和 stats。

## 选择空间尺度

- Schaefer100：较粗网络尺度，宽表较小。
- Schaefer400：常用中等尺度。
- Schaefer1000：精细分区，列数与统计负担明显增加。
- Glasser360：多模态皮层分区。
- Economo：细胞构筑学导向。
- DK308 / Vos de Wael 300：基于解剖边界的细分，但二者不是同一 Atlas。

## 防止变量冲突

Atlas 独立宽表位于 `wide/ATLAS.tsv`。跨 Atlas 使用 `all_features_wide.tsv` 时，列名会带前缀：

```text
dk68__L_bankssts_thickavg
schaefer400__L_7Networks_LH_Vis_1_thickavg
```

## 检查清单

1. 在 `atlas_manifest.tsv` 核对预期区域数。
2. 在 `subjects.tsv` 检查所有 subject-atlas 组合状态。
3. 对外部 Atlas 至少绘制少量代表性 QC。
4. 在统计模型中记录 Atlas、尺度和 FreeSurfer 版本。
