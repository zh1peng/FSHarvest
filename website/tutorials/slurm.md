# 教程：在 Slurm 上运行

仓库提供 `submit_slurm.sh` 和 `slurm/extract.sbatch`。默认 wrapper 请求 12 个 CPU，并在一个 job 中并行处理 12 位受试者。

## 提交任务

```bash
export FREESURFER_HOME=/path/to/freesurfer
bash ./submit_slurm.sh /path/to/subjects /path/to/output
```

## 提交前调整

根据集群策略编辑 `slurm/extract.sbatch`：

- account 与 partition；
- wall time；
- CPU 与内存；
- 日志路径；
- FreeSurfer module 或安装路径。

## 并发原则

`--jobs` 控制同时处理的受试者数。它应与分配的 CPU 数量和单个 FreeSurfer 操作的内存峰值共同考虑。
开启 QC 后，渲染阶段的内存需求通常高于纯提取阶段。

## 已在 allocation 中

如果已经位于交互式 allocation 或其他作业脚本内部，直接使用 `run_extract.sh` 更简单：

```bash
bash ./run_extract.sh INPUT OUTPUT --jobs 12
```

::: warning 先做 smoke test
集群上的 FreeSurfer module、模板目录和许可证配置可能与登录节点不同。提交完整队列前，先用 `--limit 10` 验证实际计算节点。
:::
