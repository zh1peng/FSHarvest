# 脑区分区与处理方式

脑区分区（atlas）决定皮层如何划分为不同区域。在 `--atlases` 后填写下表中的图谱名称，指定要提取的分区。

## 可用脑区分区

以下按**图谱边界的划分依据**分类，而不是按 FSHarvest 提取的指标分类。脑区数均指排除背景和非皮层标签后的皮层区域数。Cammoun 需要 **FSHarvest 1.0.5 或更新版本**。

### 解剖结构分区

| 命令中的名称 | 皮层总数 | 左 / 右 | 分区依据 | 来源与标准空间 |
| --- | ---: | ---: | --- | --- |
| `dk68` | 68 | 34 / 34 | [脑回解剖](https://pubmed.ncbi.nlm.nih.gov/16530430/) | FreeSurfer 内置，默认 |
| `destrieux` | 148 | 74 / 74 | [脑回与脑沟解剖](https://pubmed.ncbi.nlm.nih.gov/20547229/) | FreeSurfer 内置 |
| `dk308` | 308 | 152 / 156 | [DK 边界内按目标面积细分](https://github.com/KirstieJane/UCHANGE_ProcessingPipeline/blob/b4f8e8a3a56cee6a25187c075ed82157a3a1e67a/NSPN_Parcellation_PostEdits.sh) | NSPN500, `fsaverage` |
| `vosdewael300` | 300 | 150 / 150 | [DK 解剖区域细分](https://brainspace.readthedocs.io/en/stable/pages/matlab_doc/data_loaders/load_parcellation.html) | micapipe, `fsaverage5` |
| `cammoun33` | 68 | 34 / 34 | DK 基础尺度 | netneurotools, `fsaverage` |
| `cammoun60` | 114 | 57 / 57 | DK 多尺度解剖细分 | netneurotools, `fsaverage` |
| `cammoun125` | 219 | 111 / 108 | DK 多尺度解剖细分 | netneurotools, `fsaverage` |
| `cammoun250` | 448 | 225 / 223 | DK 多尺度解剖细分 | netneurotools, `fsaverage` |
| `cammoun500` | 1000 | 499 / 501 | DK 多尺度解剖细分 | netneurotools, `fsaverage` |
| `economo` | 86 | 43 / 43 | [细胞构筑的 MRI 实现](https://doi.org/10.1016/j.neuroimage.2016.12.069) | micapipe，`fsaverage5` |

Economo 描述微观的细胞组织结构，其余分区依据宏观解剖或对解剖区域进一步细分。
DK308 的上游名称 `500.aparc` 指约 500 mm² 的目标脑区面积。
Cammoun 为多尺度连接组分析提供解剖区域；扩散 MRI 纤维追踪用于测量区域之间的连接，
其分区边界并非通过连接模式聚类定义（[Cammoun et al., 2012](https://pubmed.ncbi.nlm.nih.gov/22001222/)）。

### 功能连接分区

| 命令中的名称 | 皮层总数 | 左 / 右 | 分区依据 | 来源与标准空间 |
| --- | ---: | ---: | --- | --- |
| `schaefer100` … `schaefer1000` | 100–1000 | 左右各半 | [静息态 fMRI 功能连接](https://pubmed.ncbi.nlm.nih.gov/28981612/) | micapipe，`fsaverage5` |

Schaefer 综合局部功能连接变化和全局相似性。工具包提供每隔 100 区的十个分辨率，采用 Yeo 7 网络标签。
它的名称后缀就是皮层脑区总数，与 Cammoun 的尺度编号含义不同。

### 多模态分区：结构与功能结合

| 命令中的名称 | 皮层总数 | 左 / 右 | 分区依据 | 来源与标准空间 |
| --- | ---: | ---: | --- | --- |
| `glasser360` | 360 | 180 / 180 | [皮层结构、功能、连接与空间组织](https://www.nature.com/articles/nature18933) | micapipe，`fsaverage5` |

Glasser HCP-MMP1.0 综合结构 MRI 特征、任务反应和静息态连接信息。
FSHarvest 投影随包提供的图谱，不为每位受试者重新运行原始 HCP 多模态分类器。

无论选择哪一类图谱，FSHarvest 都从已有 FreeSurfer 重建结果中提取**形态学指标**，
包括皮层厚度、表面积和灰质体积。选择功能分区不需要额外输入 fMRI，也不会生成功能连接矩阵。

默认只选择 `dk68`。其他分区都必须通过 `--atlases` 明确指定。

`--atlases` 也接受自定义分区 JSON，可与上表的名称混用。
用户提供左右 annot 和源模板后，共用现有投影、统计、汇总及 QC 流程，
详见[使用自己的 annot 文件](../tutorials/multi-atlas.md#使用自己的-annot-文件)。

## 不同图谱如何提取

### FreeSurfer 内置分区

DK68 直接读取 `stats/{lh,rh}.aparc.stats`；Destrieux 读取
`stats/{lh,rh}.aparc.a2009s.stats`。FSHarvest 不重新投影、不复制，也不创建第二份受试者分区标注文件。

### 外部分区

FSHarvest 使用 `mri_surf2surf --sval-annot` 将固定版本的分区标注文件（`.annot`）投影到
受试者自身的表面，再用 `mris_anatomical_stats` 根据 white、pial 和 thickness 文件计算统计量。

生成文件默认保存在：

```text
OUTPUT/per_subject/SUBJECT/label/
OUTPUT/per_subject/SUBJECT/stats/
```

## 如何指定要提取的图谱

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux dk308 \
            schaefer100 schaefer400 schaefer1000 \
            glasser360 economo vosdewael300
```

## 名称与完整性验证

FSHarvest 不只核对行数，还会检查排除内侧壁和背景区域后的固定名称清单，并确认标注顶点数
与受试者表面一致。内容不匹配的 `.annot` 文件不能通过检查。随程序附带的分区文件和区域名称
清单均记录 SHA-256 校验值。

::: warning 三种“300”不能互换
`schaefer300`、`vosdewael300` 与 `dk308` 是不同分区。DK308 上游名称中的 `500` 指目标脑区面积，并不是区域数量。
:::

## Cammoun2012

Cammoun2012 是以 Desikan–Killiany 为基础的多尺度解剖分区。名称后缀
`33/60/125/250/500` 是上游尺度编号，**不是实际皮层脑区数**，实际数量见上表。
标注采用完整分辨率 `fsaverage`（每侧 163842 个顶点），统计时排除 `unknown` 和 `corpuscallosum`。

`cammoun33` 的皮层区域名称集合与 DK68 相同，但它从模板投影到个体；`dk68` 直接读取
个体原生 `recon-all` 分区，因此边界和统计值不一定相同。本次提供皮层表面分区，
不包含 Cammoun 皮层下分区，原有 aseg 提取方式不变。

```bash
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases cammoun33 cammoun60 cammoun125 cammoun250 cammoun500
```

资源遵循[上游许可](https://github.com/LTS5/cmp/blob/93094ce227bda9064512290dd505a7ba75cf7072/COPYRIGHT)，
包括仅限研究用途的条款。使用时请引用 [Cammoun et al. (2012)](https://doi.org/10.1016/j.jneumeth.2011.09.031)。
