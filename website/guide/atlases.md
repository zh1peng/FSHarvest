# Atlas 与投影路径

## 可用 Atlas

| 命令键 | 分区 | 每半球预期区域 | 来源路径 |
| --- | ---: | ---: | --- |
| `dk68` | 68 | 34 / 34 | FreeSurfer 内置，默认 |
| `destrieux` | 148 | 74 / 74 | FreeSurfer 内置 |
| `dk308` | 308 | 152 / 156 | NSPN500，`fsaverage` |
| `schaefer100` … `schaefer1000` | 100–1000 | N/2 | micapipe，`fsaverage5` |
| `glasser360` | 360 | 180 / 180 | micapipe，`fsaverage5` |
| `economo` | 86 | 43 / 43 | micapipe，`fsaverage5` |
| `vosdewael300` | 300 | 150 / 150 | micapipe，`fsaverage5` |

默认只选择 `dk68`。所有其他 Atlas 都必须通过 `--atlases` 明确指定。

## 两条提取路径

### FreeSurfer 内置 Atlas

DK68 直接读取 `stats/{lh,rh}.aparc.stats`；Destrieux 读取
`stats/{lh,rh}.aparc.a2009s.stats`。FSHarvest 不重新投影、不复制，也不创建第二份 subject-level annotation。

### 外部 Atlas

FSHarvest 使用 `mri_surf2surf --sval-annot` 将固定版本的 annotation 投影到受试者，
再用 `mris_anatomical_stats` 在 native white/pial/thickness surfaces 上计算分区统计。

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

FSHarvest 不只核对行数，还会检查排除 medial wall/background 后的固定区域名称集合。
同样大小但语义不同的 annotation 不能通过验证。Bundled atlas 文件与区域 schema 都有 SHA-256 指纹。

::: warning 三种“300”不能互换
`schaefer300`、`vosdewael300` 与 `dk308` 是不同分区。DK308 上游名称中的 `500` 指目标 parcel 面积，并不是区域数量。
:::
