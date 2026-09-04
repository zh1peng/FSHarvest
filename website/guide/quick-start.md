# 五分钟快速开始

## 1. 准备目录

确认输入目录的下一层是 FreeSurfer 受试者目录，并准备一个位于输入目录之外的新输出位置。

```bash
export SUBJECTS_ROOT=/data/study/freesurfer
export HARVEST_OUTPUT=/data/derived/fsharvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1
```

## 2. 先做小规模冒烟测试

```bash
fsharvest "$SUBJECTS_ROOT" "$HARVEST_OUTPUT" \
  --jobs 4 \
  --limit 10
```

不指定 `--atlases` 时只运行 DK68。命令返回 0 表示本次选择的所有受试者均通过完整性检查。

## 3. 查看结果

```bash
column -t -s $'\t' "$HARVEST_OUTPUT/subjects.tsv" | less -S
head "$HARVEST_OUTPUT/cortical_long.tsv"
```

重点检查 `subjects.tsv` 的状态和错误信息。失败或部分完成的受试者会保留在
`per_subject/` 中，修复问题后可直接重跑。

## 4. 运行完整队列

```bash
fsharvest "$SUBJECTS_ROOT" "$HARVEST_OUTPUT" --jobs 12
```

有效缓存会被自动复用。`PARTIAL`、`FAILED` 或缓存内容损坏的受试者会重新处理。

## 常用变化

```bash
# 嵌套搜索受试者目录
fsharvest INPUT OUTPUT --recursive

# 加入多个 Atlas
fsharvest INPUT OUTPUT --jobs 12 \
  --atlases dk68 destrieux schaefer400 glasser360

# 同时输出 DK68 与 Schaefer100 的四视图 QC
fsharvest INPUT OUTPUT --jobs 8 \
  --atlases dk68 schaefer100 \
  --qc-plots --qc-atlases dk68 schaefer100
```

::: tip 从小到大
先用 `--limit 10` 验证目录结构、FreeSurfer 版本与磁盘空间，再启动完整队列，通常比直接提交大任务更容易定位问题。
:::
