# Data-mining-global-co2-emissions
## Cách filling missing
| Cột                                                                                               | Cách fill                            | Giải thích                                              |
| ------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------- |
| `ft_gdp`, `ft_population`, `ft_forest_area_percent`, `ft_forest_area_sqkm`, `ft_renewable_energy` | **Group Mean theo country**           | Các biến này ổn định theo quốc gia và tăng dần theo năm |
| `ft_hdi`, `ft_industr_on_gdp`, `ft_deforest_area_ha`, `ft_area_ha` | **Interpolate theo năm trong từng country** | Các biến có xu hướng mượt theo thời gian |
| `ft_globalclimatephysicalriskindexgcpri`                           | **Group Mean theo country**                 | Ổn định trong giai đoạn ngắn             |
| `ft_fossil_fuel`, `ft_government_expenditure_on_education`, `ft_deforestation` | **Iterative Imputer (MICE)** | Có thể dự đoán dựa trên GDP, HDI, forest,... |                              |
| `ft_tax`, `ft_electriccarssold`, `ft_nonelectriccarsales`, `ft_environmental_protection``ft_cri`                     |  Drop         | Thiếu quá nhiều                        |
|       
