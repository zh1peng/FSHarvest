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
| `--atlas-dir PATH` | 仓库的 `atlases/` | 指定随程序提供的图谱资源目录；自定义 annot 路径由 JSON 定义 |

`--overwrite` 不会覆盖输入目录中的文件；只有显式使用 `--export-to-freesurfer` 才会尝试向输入目录复制文件。

## 脑区分区

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--atlases NAME_OR_JSON ...` | `dk68` | 接受内置分区名称或自定义分区 JSON 路径，可混合使用 |
| `--export-to-freesurfer` | 关闭 | 把验证通过的外部分区 `.annot` 和统计文件复制到输入受试者目录；遇到同名文件时不会替换 |

可用的图谱名称：

```text
dk68 destrieux dk308
schaefer100 schaefer200 schaefer300 schaefer400 schaefer500
schaefer600 schaefer700 schaefer800 schaefer900 schaefer1000
glasser360 economo vosdewael300
```

自定义分区示例：

```bash
fsharvest INPUT OUTPUT --atlases dk68 /path/to/lab-atlas.json --qc-plots --qc-atlases lab
```

JSON 声明左右 `.annot` 文件、分区 `key` 和源模板（`fsaverage5` 或 `fsaverage`）。
`--qc-atlases` 使用 JSON 中的 `key`，不使用 JSON 路径。
完整格式见[自定义分区教程](../tutorials/multi-atlas.md#使用自己的-annot-文件)。

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
fsharvest 1.0.4
```

## 启动横幅、运行进度与日志

正常运行时会自动显示 ASCII 字符标志、版本、开发者 `zh1peng`、许可证和仓库地址。
通过安装后的 `fsharvest` 命令运行时，横幅只显示一次，随后报告 FreeSurfer 环境准备情况。
`--help` 和 `--version` 保持简洁，不显示横幅，也不初始化 FreeSurfer。

运行期间会显示输入输出路径、所选图谱和并行数，并在检查、发现受试者、开始提取、可选的
导出与 QC、开始汇总时输出阶段提示。每个受试者完成后显示 `[已完成/总人数]`、状态和
是否命中缓存；进度消息带时间戳和已用时间，并立即输出，方便终端查看及保存到批处理日志。
第一个受试者尚未完成时也会先显示“开始提取”，不需要用户在脚本中自行添加 echo。

结束时会显示本次启用的所有阶段的总体结果、独立的表格状态计数、已用时间、输出目录和逐受试者
日志位置；启用 QC 才显示 QC 报告路径。部分结果仍保留并返回非零退出码，不会被显示为
全部成功。进度采用纯文本，不依赖彩色终端或额外 Python 包。

命令会自动把终端输出和错误同时保存到 `OUTPUT_DIR/logs/run_时间戳_唯一后缀.log`，
在启动和结束时显示日志路径。总日志覆盖横幅、环境准备、阶段进度、错误和退出码，
每次运行生成独立文件；逐受试者的 `extract.log` 继续保留详细命令记录。
安装后的 `fsharvest`、`run_extract.sh` 和直接运行 `python fs_extract_all.py` 均自动保存日志，
用户脚本不需要添加 `tee`。帮助和版本查询不创建日志；参数解析失败、输入输出路径冲突，
或无法创建日志文件时，错误会直接显示在终端。

## 退出码

| 退出码 | 含义 |
| --- | --- |
| `0` | 所有受试者均为 `OK` |
| `2` | 运行完成，但至少一位受试者为 `PARTIAL`、`FAILED` 或 `NOT_RUN` |
| `1` | 参数、环境或运行阶段发生错误 |
| `130` | 用户中断，例如按下 `Ctrl+C` |

自动化脚本应同时检查退出码和 `subjects.tsv`，不要只依据汇总表是否存在来判断成功。
