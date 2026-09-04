# 教程：在 Slurm 集群上运行

FSHarvest 自带 `submit_slurm.sh` 和 `slurm/extract.sbatch`。一次作业处理一个输入目录，并把所有结果写入一个独立的输出目录。下面的模板可直接复制，再按集群要求修改账户、分区和 FreeSurfer 路径。

## 方式一：使用仓库自带的提交脚本

先进入仓库并设置 FreeSurfer 安装目录：

```bash
cd /path/to/FSHarvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1

bash ./submit_slurm.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

`submit_slurm.sh` 会把前两个参数转换为绝对路径，然后调用 `sbatch`。后面的参数会原样传给 FSHarvest。提交成功时，Slurm 会返回作业编号：

```text
Submitted batch job 482731
```

仓库中的默认作业申请 12 个 CPU、24 GB 内存和 24 小时运行时间。FSHarvest 会读取 `SLURM_CPUS_PER_TASK`，因此该配置等价于 `--jobs 12`。

## 方式二：复制一份作业模板

如果集群要求在作业文件中填写账户或分区，可新建 `fsharvest_job.sbatch`：

```bash
#!/usr/bin/env bash
#SBATCH --job-name=fsharvest
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --partition=YOUR_PARTITION
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=12
#SBATCH --mem=24G
#SBATCH --output=logs/fsharvest_%j.out
#SBATCH --error=logs/fsharvest_%j.err

set -euo pipefail

REPO=/path/to/FSHarvest
INPUT=/data/freesurfer/subjects
OUTPUT=/data/results/fsharvest
export FREESURFER_HOME=/usr/local/freesurfer/7.4.1

mkdir -p "$OUTPUT" logs

bash "$REPO/run_extract.sh" "$INPUT" "$OUTPUT" \
  --jobs "${SLURM_CPUS_PER_TASK:-1}" \
  --atlases dk68 schaefer100 \
  --qc-plots \
  --qc-atlases dk68 schaefer100
```

提交前先检查路径，然后运行：

```bash
mkdir -p logs
sbatch fsharvest_job.sbatch
```

如果集群通过环境模块提供 FreeSurfer，可把 `export FREESURFER_HOME=...` 换成集群要求的命令，例如 `module load freesurfer/7.4.1`。最终仍应确认 `FREESURFER_HOME` 已设置，并且 `recon-all`、`mri_surf2surf` 和 `mris_anatomical_stats` 都能找到。

## 查看进度和日志

```bash
squeue -j 482731
sacct -j 482731 --format=JobID,State,Elapsed,AllocCPUS,MaxRSS,ExitCode
tail -f logs/fsharvest_482731.out
```

计算节点上的日志会包含主机名、实际命令和处理进度。例如：

```text
Host: compute-17
FreeSurfer: /usr/local/freesurfer/7.4.1
Discovered 10 subjects; jobs=12; FreeSurfer=freesurfer-linux-ubuntu22_x86_64-7.4.1-20230614-7eb8460
[1/10] example-01: OK
...
Finished: 10 OK, 0 non-OK. Outputs: /data/results/fsharvest
```

作业正常结束后，还应查看 `OUTPUT/subjects.tsv`。Slurm 显示 `COMPLETED` 只说明进程正常退出；是否每位受试者都成功，仍以 `subjects.tsv` 中的 `status` 为准。

## 交互式调试：`salloc` 和 `srun`

首次在新集群上运行时，建议先申请一个计算节点并只处理少量受试者：

```bash
salloc --time=01:00:00 --cpus-per-task=4 --mem=12G

srun bash /path/to/FSHarvest/run_extract.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest-test \
  --jobs 4 \
  --limit 2 \
  --atlases dk68 schaefer100
```

也可以直接让 `srun` 申请资源并执行：

```bash
srun --time=01:00:00 --cpus-per-task=4 --mem=12G \
  bash /path/to/FSHarvest/run_extract.sh \
  /data/freesurfer/subjects \
  /data/results/fsharvest-test \
  --jobs 4 --limit 2
```

`srun` 适合检查 FreeSurfer 环境、许可证、挂载路径和内存占用。确认测试输出无误后，再用 `sbatch` 提交完整队列。

## CPU、内存与并发

- `--jobs` 是同时处理的受试者数，通常不要超过 `--cpus-per-task`。
- 外部分区投影和 QC 绘图会增加内存需求。若出现内存不足，先降低 `--jobs`，再根据 `sacct` 的 `MaxRSS` 调整 `--mem`。
- 不要让两个作业同时写入同一个输出目录；输出锁会阻止这种情况。不同队列或不同参数组合应使用不同的输出目录。
- 当前聚合表按一次完整运行生成。若自行使用作业数组，请先让每个数组任务写入独立目录，再单独设计汇总步骤；不要直接并发写同一目录。

::: warning 不要只在登录节点测试
登录节点与计算节点可能使用不同的模块、许可证配置和数据挂载。正式提交前，请在实际计算节点上用 `--limit 2` 或 `--limit 10` 验证一次。
:::
