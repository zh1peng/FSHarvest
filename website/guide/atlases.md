# 脑区分区与处理方式

脑区分区（atlas）决定皮层如何划分为不同区域。命令中使用下表的键选择需要提取的分区。

## 可用脑区分区

| 命令键 | 分区 | 每半球预期区域 | 来源路径 |
| --- | ---: | ---: | --- |
| `dk68` | 68 | 34 / 34 | FreeSurfer 内置，默认 |
| `destrieux` | 148 | 74 / 74 | FreeSurfer 内置 |
| `dk308` | 308 | 152 / 156 | NSPN500，`fsaverage` |
| `schaefer100` … `schaefer1000` | 100–1000 | N/2 | micapipe，`fsaverage5` |
| `glasser360` | 360 | 180 / 180 | micapipe，`fsaverage5` |
| `economo` | 86 | 43 / 43 | micapipe，`fsaverage5` |
| `vosdewael300` | 300 | 150 / 150 | micapipe，`fsaverage5` |

默认只选择 `dk68`。其他分区都必须通过 `--atlases` 明确指定。

## 两条提取路径

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

## 选择示例

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
`schaefer300`、`vosdewael300` 与 `dk308` 是不同分区。DK308 上游名称中的 `500` 指目标 parcel 面积，并不是区域数量。
:::
