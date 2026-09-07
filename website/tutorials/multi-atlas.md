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

## 使用自己的 annot 文件

内置分区名称和自定义 JSON 共用 `--atlases` 入口，可以在一次运行中混合选择：

```bash
fsharvest INPUT OUTPUT --atlases dk68 schaefer100 /path/to/lab-atlas.json \
  --qc-plots --qc-atlases lab
```

如果只提取自定义分区，使用 `--atlases /path/to/lab-atlas.json`。
`lab-atlas.json` 内容如下：

```json
{
  "key": "lab",
  "display_name": "实验室自定义分区",
  "source_subject": "fsaverage5",
  "annotations": {
    "lh": "lh.lab.annot",
    "rh": "rh.lab.annot"
  },
  "excluded_regions": ["unknown", "corpuscallosum"]
}
```

- 左右半球文件都必须提供；路径可以是绝对路径，也可以相对于 JSON 文件所在目录。
- `key` 用于输出文件名和 QC 选择。以英文字母或数字开头，只使用英文字母、数字、`_`、`-`，不能与内置分区或本次其他分区重名。
- `source_subject` 必须明确填写 `fsaverage5` 或 `fsaverage`，对应模板需要安装在 `FREESURFER_HOME/subjects/` 下。
- `display_name` 可省略，默认使用 `key`。
- 程序自动排除 FreeSurfer 不输出统计量的 `unknown`、`Unknown`、`corpuscallosum`、`Medial_wall`。`excluded_regions` 可省略，用于追加其他需要排除的准确标签名称。

程序读取 annot 中实际分配给源模板顶点的色表条目，排除标签后，分别确定左右脑区名称和数量；
忽略未使用的色表条目，两侧数量可以不同，脑区名称可以包含空格。
每个保留的脑区都需要出现在生成的统计文件中；投影后丢失的真实脑区仍会报错。
用户不需要制作 manifest 或 SHA 文件。

内置名称加载我们整理的 annot 和配套信息，自定义 JSON 加载用户指定的 annot；两者都进入
“校验 → 投影到受试者 → 生成 stats → 提取汇总与 QC”的流程。
DK68、Destrieux 则直接读取 recon-all 已生成的统计文件。

顶点数检查只能发现与模板不匹配的文件，不能自动判断源空间。
这里接收的是**模板空间** annot，不是逐受试者原生空间 annot。
自定义分区始终以 JSON 指定的文件作为投影来源，不会改用受试者目录中的同名文件；
输出目录中通过检查的缓存仍可复用。

结果按 `key` 命名，例如 `wide/lab.tsv`、`per_subject/SUBJECT/label/lh.lab.annot`。
`atlas_manifest.tsv` 记录文件路径和左右预期脑区数，`run_metadata.json` 保存完整分区定义和脑区清单。

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
