# 同时提取多个脑区分区

同时选择多个分区会增加运行时间、输出列数和 QC 图片数量。建议根据研究目的选择必要的分区，
不要默认一次运行全部分区。

## 分阶段运行

先读取 FreeSurfer 内置分区：

```bash
fsharvest INPUT OUTPUT --jobs 12 --atlases dk68 destrieux
```

检查输出和列名，确认输入目录及 FreeSurfer 环境无误后，再加入需要投影的外部分区：

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux schaefer100 schaefer400 glasser360
```

已通过检查的缓存可以在后续运行中复用。外部分区生成的 `.annot` 和 `.stats` 文件保存在
各受试者的 `per_subject/` 目录中。

## 检查实际选择和完成数量

`atlas_manifest.tsv` 会记录每个分区的预期区域数和完整受试者数。下面是一次真实单受试者
DK68 + Schaefer100 运行的简化输出：

```text
key          expected_total  kind      source_subject  observed_subjects_complete
dk68         68              builtin                   1
schaefer100  100             external  fsaverage5      1
```

## 如何选择分区尺度

- Schaefer100：网络尺度较粗，宽表列数较少；
- Schaefer400：常用的中等尺度；
- Schaefer1000：区域更细，会增加模型变量数量和多重比较负担；
- Glasser360：多模态皮层分区；
- Economo：以细胞构筑学为依据；
- DK308 与 Vos de Wael 300：均为解剖边界细分，但不是同一个分区。

## 不同分区的列名如何区分

每个分区的独立宽表位于 `wide/ATLAS.tsv`。`all_features_wide.tsv` 中的列名会增加
分区前缀：

```text
dk68__L_bankssts_thickavg
schaefer400__L_7Networks_LH_Vis_1_thickavg
```

## 检查清单

1. 在 `atlas_manifest.tsv` 检查每个分区的预期区域数和完整受试者数；
2. 在 `subjects.tsv` 查看每位受试者的整体 `status` 和 `errors`；
3. 如果某个分区失败，从逐受试者 `status.json` 和 `extract.log` 定位分区及半球；
4. 对每个外部分区至少查看若干代表性受试者的 QC 图；
5. 在分析方法中记录分区名称、尺度、来源和 FreeSurfer 版本。

::: warning 当前没有逐分区状态表
`subjects.tsv` 目前不是受试者 × 分区状态表。只要一个所选分区失败，该受试者的整体状态
就不是 `OK`，也不会进入本次严格汇总表。
:::
