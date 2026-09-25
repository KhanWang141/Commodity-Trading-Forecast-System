# Commodity-Trading-Forecast-System

面向不完整多源数据的商品期货波动预测框架——发布时点对齐、分层信息融合与滚动样本外检验

## Research data pipeline

这个分支有一个可复现的、按时间点的数据源，用于商品波动性研究数据集。每次构建前都会用 SHA-256 检查冻结的输入。市场特征是从每日对数收益重新计算的，宏观特征通过在发布时间戳上使用 backward merge_asof 重新构建，标签是在一个不导入任何特征代码的模块中计算的。

提供的文件包含 51 个候选值。config/features.yaml 锁定了一个 29 特征的 schema：包括八个多尺度铁矿特征、六个短期跨商品特征，以及全部十五个宏观发布特征。根目录下的 CSV 文件保留自原始分支；管道使用存储在 data/raw/ 和 data/frozen/ 下的字节冻结快照。

### Reproduce

```powershell
python -m pip install -r requirements.txt
python -m src.pipeline.build_dataset
python -m pytest -q
```

第一个数据集构建会在输入清单尚不存在时创建它。各个阶段也可以单独运行：

```powershell
python -m src.data.freeze_inputs
python -m src.data.verify_inputs
python -m src.features.build_features
python -m src.labels.build_labels
python -m src.audit.asof_audit
```

所有时间戳都使用 `Asia/Shanghai`。宏值只有在其发布时间戳小于或等于 20:00 的模型时间戳时才可使用。由于提供的源数据每个观测值只有一个已发布版本，因此无法独立验证完整的修订版本行为；生成的元数据和审计报告明确记录了这一限制。
Generated research artifacts include:

- `data/processed/model_dataset.parquet`
- `data/processed/model_dataset_metadata.json`
- `reports/asof_audit.csv`
- `reports/asof_audit_summary.json`
- `reports/data_quality_report.md`
