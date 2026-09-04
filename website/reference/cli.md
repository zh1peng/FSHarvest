# 命令行参数

```text
fsharvest SUBJECTS_DIR OUTPUT_DIR [options]
```

## 位置参数

| 参数 | 说明 |
| --- | --- |
| `SUBJECTS_DIR` | 直接包含各个 FreeSurfer 受试者目录的输入目录；配合 `--recursive` 时可递归查找 |
| `OUTPUT_DIR` | FSHarvest 的独立输出目录，不能放在输入目录内部 |

## 运行方式

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--jobs N` | `min(8, CPU 数)` | 同时处理的受试者数，必须为正整数 |
| `--limit N` | 不限制 | 只处理按名称排序后的前 N 位受试者，适合小规模测试 |
| `--recursive` | 关闭 | 在输入目录下递归查找 FreeSurfer 受试者目录 |
| `--overwrite` | 关闭 | 忽略可复用的缓存和受试者目录内已有的外部分区文件，重新投影并计算统计量 |
| `--force-unlock` | 关闭 | 在确认同一主机上记录的进程已经结束后，移除遗留的输出锁 |
| `--freesurfer-home PATH` | `$FREESURFER_HOME` | 指定 FreeSurfer 安装目录 |
| `--atlas-dir PATH` | 仓库的 `atlases/` | 指定分区资源目录 |

`--overwrite` 不会覆盖输入目录中的文件；只有显式使用 `--export-to-freesurfer` 才会尝试向输入目录复制文件。

## 脑区分区

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--atlases KEY ...` | `dk68` | 选择一个或多个脑区分区 |
| `--export-to-freesurfer` | 关闭 | 把验证通过的外部分区 `.annot` 和统计文件复制到输入受试者目录；遇到同名文件时不会替换 |

可用键：

```text
dk68 destrieux dk308
schaefer100 schaefer200 schaefer300 schaefer400 schaefer500
schaefer600 schaefer700 schaefer800 schaefer900 schaefer1000
glasser360 economo vosdewael300
```

## QC 图片

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--qc-plots` | 关闭 | 为皮层分区生成四视图 PNG，并更新 HTML 报告 |
| `--qc-atlases KEY ...` | 所有已选分区 | 只为指定的已选分区绘图 |
| `--qc-surface` | `inflated` | 绘制表面：`inflated`、`pial` 或 `white` |
| `--qc-dpi N` | `150` | 图片分辨率，最小值为 72 |

## 帮助与版本

```bash
fsharvest --help
fsharvest --version
```

当前版本输出为：

```text
fsharvest 1.0.0rc1
```

`rc1` 表示第一个候选发布版，还不是 1.0.0 正式版。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 所有受试者均为 `OK` |
| `2` | 运行完成，但至少一位受试者为 `PARTIAL`、`FAILED` 或 `NOT_RUN` |
| `1` | 参数、环境或运行阶段发生错误 |
| `130` | 用户中断，例如按下 `Ctrl+C` |

自动化脚本应同时检查退出码和 `subjects.tsv`，不要只依据聚合表是否存在来判断成功。
