# Data-mining-global-co2-emissions
Xử lý missing value
## 1.Mapping lấy các quốc gia -> bỏ các vùng lãnh thổ
## 2.Bỏ các dòng có df_Co2 bị Missing
## 3.Sử dụng nội suy tuyến tính theo quốc gia
'ft_gdp', 'ft_population','ft_hdi','ft_forest_area_sqkm','ft_forest_area_percent' 
Đối với phương pháp này, các năm missing đầu cuối chuỗi năm hoặc các quốc gia bị missing hết các năm sẽ không điền được. Những dòng chưa được fill missing sẽ tiếp tục bước tiếp theo.
## 4. Sử dụng KNN
Đối với các feature còn lại và những dòng missing value còn sót lại sau bước 3 sẽ sử dụng phương pháp này.
