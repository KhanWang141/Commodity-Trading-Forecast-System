# Data quality report

## Dataset Summary

- Time range: 2019-01-02T20:00:00+08:00 to 2026-08-31T20:00:00+08:00
- Samples: 1859
- Features: 29
- Labels: 2

| source             | sha256                                                           | rows | date_range                                 |
| ------------------ | ---------------------------------------------------------------- | ---- | ------------------------------------------ |
| features_asof      | fc6ab0de922bd446ab8be41406e0edf8c0ae7f63cc61b69cede8ddcd426ba892 | 1859 | 2019-01-02T00:00:00 to 2026-08-31T00:00:00 |
| targets_and_splits | 552ea65522ad762f4a7a8d5632552d938f869bc7877da990817a714d71fc7924 | 1859 | 2019-01-02T00:00:00 to 2026-08-31T00:00:00 |

## Missing Values

| column                        | count | missing_pct |
| ----------------------------- | ----- | ----------- |
| I_cumret_5                    | 11    | 0.592%      |
| I_daily_squared_return_vol_5  | 11    | 0.592%      |
| I_cumret_10                   | 21    | 1.130%      |
| I_daily_squared_return_vol_10 | 21    | 1.130%      |
| I_cumret_22                   | 45    | 2.421%      |
| I_daily_squared_return_vol_22 | 45    | 2.421%      |
| I_cumret_66                   | 133   | 7.154%      |
| I_daily_squared_return_vol_66 | 133   | 7.154%      |
| J_r                           | 3     | 0.161%      |
| J_cumret_5                    | 11    | 0.592%      |
| JM_r                          | 3     | 0.161%      |
| JM_cumret_5                   | 11    | 0.592%      |
| RB_r                          | 3     | 0.161%      |
| RB_cumret_5                   | 11    | 0.592%      |
| cpi_mom                       | 41    | 2.205%      |
| cpi_yoy                       | 41    | 2.205%      |
| crude_steel_yoy               | 1011  | 54.384%     |
| industrial_value_added_yoy    | 46    | 2.474%      |
| pig_iron_yoy                  | 1011  | 54.384%     |
| pmi_input_prices              | 898   | 48.306%     |
| pmi_manufacturing             | 21    | 1.130%      |
| pmi_new_orders                | 134   | 7.208%      |
| ppi_iron_mining_mom           | 402   | 21.625%     |
| ppi_iron_mining_yoy           | 402   | 21.625%     |
| ppi_mom                       | 28    | 1.506%      |
| ppi_steel_mom                 | 485   | 26.089%     |
| ppi_steel_yoy                 | 485   | 26.089%     |
| ppi_yoy                       | 28    | 1.506%      |
| steel_products_yoy            | 1011  | 54.384%     |
| logV_h5                       | 11    | 0.592%      |
| logV_h20                      | 41    | 2.205%      |

## Feature Statistics

| feature                       | mean          | std         | min         | 1%           | 25%           | 50%           | 75%          | 99%         | max         |
| ----------------------------- | ------------- | ----------- | ----------- | ------------ | ------------- | ------------- | ------------ | ----------- | ----------- |
| I_cumret_5                    | 0.0062619334  | 0.049597658 | -0.20853744 | -0.12528043  | -0.022152234  | 0.0056514964  | 0.034936765  | 0.13638582  | 0.24753227  |
| I_daily_squared_return_vol_5  | 0.31276695    | 0.16630895  | 0.040213414 | 0.072511131  | 0.19642834    | 0.27478432    | 0.38522435   | 0.85116623  | 0.95832924  |
| I_cumret_10                   | 0.012489652   | 0.069315313 | -0.25617053 | -0.17076963  | -0.02738202   | 0.011856563   | 0.04972028   | 0.18603085  | 0.25287356  |
| I_daily_squared_return_vol_10 | 0.32129717    | 0.15078224  | 0.073068775 | 0.10621172   | 0.21792378    | 0.28466163    | 0.38773959   | 0.75418023  | 0.85786871  |
| I_cumret_22                   | 0.025656346   | 0.10004204  | -0.32727273 | -0.22682485  | -0.038989069  | 0.020268747   | 0.086070043  | 0.27382355  | 0.41415067  |
| I_daily_squared_return_vol_22 | 0.3273258     | 0.14000598  | 0.11459653  | 0.12787753   | 0.22711587    | 0.28836969    | 0.38669238   | 0.6870304   | 0.72857874  |
| I_cumret_66                   | 0.068576702   | 0.17309451  | -0.43653734 | -0.37119676  | -0.036743307  | 0.051370371   | 0.18120213   | 0.46632542  | 0.52812762  |
| I_daily_squared_return_vol_66 | 0.33324511    | 0.13101777  | 0.14878917  | 0.15325565   | 0.2406035     | 0.30564176    | 0.38953649   | 0.62299327  | 0.65400711  |
| J_r                           | 0.00021440357 | 0.021486373 | -0.11087422 | -0.06023803  | -0.011827868  | 0             | 0.012339675  | 0.057223603 | 0.09376065  |
| J_cumret_5                    | 0.0019868672  | 0.046717085 | -0.22547447 | -0.10815165  | -0.027651523  | 0.0011094604  | 0.031655047  | 0.11833371  | 0.24524138  |
| JM_r                          | 0.00029391249 | 0.023967436 | -0.13455313 | -0.06281839  | -0.011840777  | 0             | 0.012398047  | 0.06341263  | 0.11632064  |
| JM_cumret_5                   | 0.0026644487  | 0.054345027 | -0.27133479 | -0.12499962  | -0.028091139  | 0.0024262034  | 0.03015468   | 0.14372607  | 0.35961123  |
| RB_r                          | 0.00012392438 | 0.013558555 | -0.07935247 | -0.039210836 | -0.0067120819 | 0.00026677886 | 0.0076516369 | 0.033846495 | 0.060959091 |
| RB_cumret_5                   | 0.00099617388 | 0.030001594 | -0.14466158 | -0.089409825 | -0.015542038  | 0.0021607993  | 0.018654103  | 0.07003807  | 0.15030774  |
| cpi_mom                       | 0.09229923    | 0.48427796  | -1.2        | -1.166       | -0.2          | 0             | 0.4          | 1.4         | 1.4         |
| cpi_yoy                       | 1.239714      | 1.3765935   | -0.8        | -0.7         | 0.2           | 0.9           | 2.3          | 5.4         | 5.4         |
| crude_steel_yoy               | -4.3949292    | 8.0059237   | -23.3       | -23.3        | -7.8          | -4.6          | -0.475       | 17.6        | 17.6        |
| industrial_value_added_yoy    | 5.3781577     | 4.48021     | -13.5       | -13.5        | 4.4           | 5.3           | 6.4          | 35.1        | 35.1        |
| pig_iron_yoy                  | -2.8570755    | 6.8782151   | -19.4       | -19.4        | -6.2          | -3.3          | 0            | 13          | 13          |
| pmi_input_prices              | 54.800728     | 6.512967    | 44.3        | 44.3         | 50.9          | 53.2          | 60           | 72.1        | 72.1        |
| pmi_manufacturing             | 49.791513     | 1.8150414   | 35.7        | 35.7         | 49.3          | 49.8          | 50.4         | 52.6        | 52.6        |
| pmi_new_orders                | 49.934377     | 2.9341014   | 29.3        | 29.3         | 49.2          | 49.9          | 51.3         | 54.1        | 54.1        |
| ppi_iron_mining_mom           | 0.050102951   | 3.2154463   | -8.9        | -8.9         | -0.9          | 0.3           | 2.2          | 5.9         | 5.9         |
| ppi_iron_mining_yoy           | 1.3177076     | 14.63048    | -29.5       | -29.5        | -7.2          | 1             | 8.8          | 54.6        | 54.6        |
| ppi_mom                       | 0.050245767   | 0.64516588  | -1.3        | -1.3         | -0.3          | 0             | 0.3          | 2.5         | 2.5         |
| ppi_steel_mom                 | -0.20247453   | 2.0948853   | -6.2        | -6.2         | -1            | -0.1          | 1.1          | 5.6         | 5.6         |
| ppi_steel_yoy                 | -1.3860262    | 13.064228   | -21.1       | -21.1        | -10           | -4            | -0.5         | 39.9        | 39.9        |
| ppi_yoy                       | 0.44849809    | 4.418447    | -5.4        | -5.4         | -2.5          | -1.3          | 1.7          | 13.5        | 13.5        |
| steel_products_yoy            | 0.33891509    | 6.6496021   | -14.9       | -14.9        | -2.6          | -1.1          | 5            | 14.5        | 14.5        |

## Extreme Values

The diagnostic below counts observations more than 10 population standard deviations from the column mean; it does not alter data.

| feature                       | abs_z_gt_10_count |
| ----------------------------- | ----------------- |
| I_cumret_5                    | 0                 |
| I_daily_squared_return_vol_5  | 0                 |
| I_cumret_10                   | 0                 |
| I_daily_squared_return_vol_10 | 0                 |
| I_cumret_22                   | 0                 |
| I_daily_squared_return_vol_22 | 0                 |
| I_cumret_66                   | 0                 |
| I_daily_squared_return_vol_66 | 0                 |
| J_r                           | 0                 |
| J_cumret_5                    | 0                 |
| JM_r                          | 0                 |
| JM_cumret_5                   | 0                 |
| RB_r                          | 0                 |
| RB_cumret_5                   | 0                 |
| cpi_mom                       | 0                 |
| cpi_yoy                       | 0                 |
| crude_steel_yoy               | 0                 |
| industrial_value_added_yoy    | 0                 |
| pig_iron_yoy                  | 0                 |
| pmi_input_prices              | 0                 |
| pmi_manufacturing             | 0                 |
| pmi_new_orders                | 0                 |
| ppi_iron_mining_mom           | 0                 |
| ppi_iron_mining_yoy           | 0                 |
| ppi_mom                       | 0                 |
| ppi_steel_mom                 | 0                 |
| ppi_steel_yoy                 | 0                 |
| ppi_yoy                       | 0                 |
| steel_products_yoy            | 0                 |

## Integrity

- Input hash verification: PASS
- Duplicated instrument/timestamp samples: 0
- Infinite values: 0
- Constant features: none
- Feature count: 29 (required: 29)
- Schema consistency: PASS

## Leakage Audit

LOOK-AHEAD AUDIT: PASS

- Rows checked: 53911
- Critical violations: 0
- Warnings: 15
- Pass rate: 100.000000%

### Vintage limitations

- cpi_mom: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- cpi_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- crude_steel_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- industrial_value_added_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- pig_iron_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- pmi_input_prices: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- pmi_manufacturing: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- pmi_new_orders: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_iron_mining_mom: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_iron_mining_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_mom: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_steel_mom: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_steel_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- ppi_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
- steel_products_yoy: No revision vintages are present in the supplied source; final-vintage contamination cannot be independently ruled out.
