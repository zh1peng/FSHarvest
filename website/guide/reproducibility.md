# 缓存、审计与复现

## 缓存何时可复用

外部投影与统计只有在以下信息仍匹配时才会复用：

- 源文件、Atlas 资产和区域 schema；
- FreeSurfer 运行时与模板；
- 运行选项和成功状态；
- TSV schema、语义检查和输出 checksum。

`PARTIAL`、`FAILED` 或损坏的缓存不会被当作成功结果。

## 强制重算

```bash
fsharvest INPUT OUTPUT --jobs 8 --overwrite
```

`--overwrite` 会忽略私有输出缓存和可复用的 subject-level annotation，重新完成投影与统计。
缺少受控 FSHarvest provenance 的 subject-level `.stats` 默认不会被复用。
它绝不授权覆盖 FreeSurfer 输入目录中已经存在的冲突文件。

## 运行来源

`run_metadata.json` 记录：

- 唯一 `run_id` 与开始/结束时间；
- 输入、输出根目录和命令选项；
- Atlas、区域集合与源文件 SHA-256；
- FreeSurfer 运行时和模板指纹；
- FSHarvest 版本与运行状态。

## FreeSurfer 版本

`fs_version` 描述产生重建的 FreeSurfer 版本；运行元数据另行记录执行提取时使用的 FreeSurfer。
不要在没有记录和建模版本效应的情况下混用不同版本重建。

当前真实数据基线覆盖 FreeSurfer 7.4.1 运行时与 7.2.0 重建。其他版本应先在代表性受试者上验证；
FreeSurfer 8.x 目前不在已验证范围内。
