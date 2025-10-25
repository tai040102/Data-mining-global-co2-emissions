Filling Missing:
1. Missing quá nhiều --> Drop:
   - ft_tax
   - ft_electriccarssold
   - ft_nonelectriccarsales
   - ft_cri
   - ft_environmental_protection
   - ft_area_ha (ý nghĩa của trường dữ liệu này không đúng)
   - ft_deforestation
2. Nội suy tuyến tính : interpolate(method='linear') theo (groupby) quốc gia (country - isocode):
   - ft_gdp
   - ft_population
   - ft_hdi
   - ft_forest_area_sqkm
   - ft_forest_area_percent
3. Sử dụng KNN: các feature còn lại + các record missing không thể fill theo interpolate
