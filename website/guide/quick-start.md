# 五分钟快速开始

## 1. 准备输入和输出目录

确认输入目录的下一层是 FreeSurfer 受试者结果目录，并选择一个位于输入目录之外的输出位置。

```bash
export SUBJECTS_ROOT=/data/study/freesurfer
export HARVEST_OUTPUT=/data/derived/fsharvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
```

## 2. 先用 10 位受试者试运行

```bash
fsharvest "$SUBJECTS_ROOT" "$HARVEST_OUTPUT" \
  --jobs 4 \
  --limit 10
```

未指定 `--atlases` 时只提取 DK68。命令返回 0 表示本次选择的所有受试者均通过检查。

## 3. 查看终端结果

以下文本来自 `linux212` 上一次只提取默认 DK68 的真实单受试者运行；受试者名称和输出路径
已替换：

```text
Discovered 1 subjects; jobs=1; FreeSurfer=freesurfer-linux-ubuntu22_x86_64-7.4.1-20230614-7eb8460
[1/1] example-01: OK
Finished: 1 OK, 0 non-OK. Output: /data/derived/fsharvest-example
```

终端中的 `OK` 只说明程序规定的文件和数值检查已经通过，不能替代 Freeview 质控。

## 4. 检查 `subjects.tsv`

```bash
column -t -s $'\t' "$HARVEST_OUTPUT/subjects.tsv" | less -S
```

真实输出中最常用的状态列如下：

```text
folder_id   subject_id  status  fs_version  eTIV_mm3          cortical_rows  aseg_rows
example-01  example-01  OK      7.2.0       1717075.390657    68             45
```

只提取默认 DK68 时，完整受试者应有 68 行皮层结果。`folder_id` 是输入目录名；
`subject_id` 来自 FreeSurfer 统计文件头，两者不一定相同。

状态含义固定为：

- `OK`：本次选择的指标均通过检查；
- `PARTIAL`：生成了部分结果，但至少一项检查失败；
- `FAILED`：没有生成可用的核心结果；
- `NOT_RUN`：本次运行没有完成该受试者。

出现 `PARTIAL` 或 `FAILED` 时，先查看 `per_subject/FOLDER_ID/extract.log` 和
`status.json`。在确认原因前，不要直接使用队列宽表。

## 5. 运行完整队列

确认试运行结果后移除 `--limit`：

```bash
fsharvest "$SUBJECTS_ROOT" "$HARVEST_OUTPUT" --jobs 12
```

通过检查的缓存会自动复用。状态异常或缓存内容损坏的受试者会重新处理。

队列汇总表始终按本次命令重写，并不会自动追加历史运行。这里的试运行与正式运行都使用
默认 DK68；如果改变 `--atlases`，汇总表的列和分区清单也会相应改变。

## 常用命令

```bash
# 递归查找嵌套的受试者目录
fsharvest INPUT OUTPUT --recursive

# 同时提取多个脑区分区
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux schaefer400 glasser360

# 生成 DK68 与 Schaefer100 的四视图 QC
fsharvest INPUT OUTPUT --jobs 8 \
  --atlases dk68 schaefer100 \
  --qc-plots --qc-atlases dk68 schaefer100
```

::: tip 先确认环境，再扩大范围
建议先用 `--limit 10` 检查目录、FreeSurfer 版本、结果表和磁盘空间，再处理完整队列。
:::
