# Commodity-Trading-Forecast-System

面向不完整多源数据的商品期货波动预测框架——发布时点对齐、分层信息融合与滚动样本外检验

## Research data pipeline

This branch contains a reproducible, point-in-time data pipeline for the
commodity-volatility research dataset. Frozen inputs are SHA-256 verified before
every build. Market features are independently recomputed from daily log
returns, macro features are rebuilt with backward `merge_asof` joins on
publication timestamps, and labels are computed in a module that does not
import feature code.

The supplied files contain 51 candidate values. `config/features.yaml` freezes
a 29-feature schema: eight multi-scale iron-ore features, six short-term
cross-commodity features, and all fifteen macro publication features. The
root-level CSV files are retained from the original branch; the pipeline uses
the byte-frozen snapshots under `data/raw/` and `data/frozen/`.

### Reproduce

```powershell
python -m pip install -r requirements.txt
python -m src.pipeline.build_dataset
python -m pytest -q
```

The first dataset build creates the frozen-input manifest when it does not yet
exist. Individual stages are also runnable:

```powershell
python -m src.data.freeze_inputs
python -m src.data.verify_inputs
python -m src.features.build_features
python -m src.labels.build_labels
python -m src.audit.asof_audit
```

All timestamps use `Asia/Shanghai`. A macro value is usable only when its
publication timestamp is less than or equal to the 20:00 model timestamp.
Because the supplied source has one published vintage per observation, full
revision-vintage behavior cannot be independently verified; the generated
metadata and audit report record this limitation explicitly.

Generated research artifacts include:

- `data/processed/model_dataset.parquet`
- `data/processed/model_dataset_metadata.json`
- `reports/asof_audit.csv`
- `reports/asof_audit_summary.json`
- `reports/data_quality_report.md`
