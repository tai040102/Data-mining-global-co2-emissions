# Phân tích dữ liệu thăm dò (EDA) - Phát thải CO2

Đây là tài liệu mô tả các bước Phân tích Dữ liệu Thăm dò (EDA) được thực hiện trong file `eda.ipynb` trên tập dữ liệu `final_filled_area_ha_country.csv` nhằm tìm hiểu đặc điểm của dữ liệu và các yếu tố ảnh hưởng đến phát thải CO2.

## 1. Tải và kiểm tra dữ liệu ban đầu

* **Tải thư viện:** Sử dụng `pandas` và `numpy` để xử lý dữ liệu.
* **Tải dữ liệu:** Đọc file CSV (`final_filled_area_ha_country.csv`) vào DataFrame.
* **Kiểm tra tổng quan:**
    * Sử dụng `df.shape` để xem kích thước ban đầu của dữ liệu (6474 hàng, 23 cột).
    * Sử dụng `df.info()` để kiểm tra kiểu dữ liệu (Dtypes) và số lượng giá trị không rỗng (non-null) ở mỗi cột.

## 2. Tiền xử lý dữ liệu

* **Tạo bản sao:** Tạo một bản sao (`df_process`) để thực hiện các bước xử lý tiếp theo.
* **Xử lý trùng lặp:** Sử dụng `df_process.drop_duplicates()` để xóa các hàng trùng lặp.
* **Xử lý dòng bị missing full:** Sử dụng `df_process = df_process.dropna(how='all')` để xóa các hàng miss full.
*
## 3. Phân tích và Xử lý Giá trị thiếu (Missing Values)

* **Tính toán tỷ lệ thiếu (Cột):**
    * Tính toán tỷ lệ phần trăm giá trị thiếu của mỗi cột so với tổng số hàng (`df_process.isnull().sum()/len(df_process)`).
* **Xử lý cột (Lọc Feature):**
    * Xác định và loại bỏ các cột có tỷ lệ giá trị thiếu từ **40%** trở lên (ví dụ: `ft_tax`, `ft_electriccarssold`, `ft_cri`...).
* **Xử lý hàng (Lọc Biến mục tiêu):**
    * Loại bỏ các hàng có giá trị `ft_co2` (biến mục tiêu) bị thiếu (`dropna(subset='ft_co2')`).
    * Loại bỏ các hàng có giá trị `ft_co2` bằng 0.
* **Phân tích giá trị thiếu (Hàng):**
    * Tạo một cột mới `missing_count` để đếm số lượng feature bị thiếu trên *mỗi hàng* (`df_process.isnull().sum(axis=1)`).
* **Xử lý hàng (Lọc hàng thiếu):**
    * Lọc và giữ lại các hàng có `missing_count` nhỏ hơn hoặc bằng **4** (`df_process[df_process["missing_count"] <= 4]`).
* **Xử lý missing cho các giá trị còn lại:**
    * Nhóm 3 features: fill 'ft_forest_area_sqkm','ft_forest_area_percent','ft_deforest_area_ha' bằng giá trị median sau khi groupby "country" vì giá trị diện tích rừng và mất rừng ở các quốc gia là khác nhau. 
    * Sau khi fill 3 nhóm này xong mà vẫn bị nan --> drop dòng `df_imputed = df_imputed.dropna(subset= 'ft_deforest_area_ha')`
    * Nhóm các feature còn lại: fill bằng giá trị median - giữ phân bố. `df_filled_missing = df_imputed.fillna(df_imputed.median(numeric_only=True))`
    
## 4. Phân tích Thống kê và Trực quan hóa

* **Thống kê mô tả:** Sử dụng `df_process.describe()` để xem các thống kê cơ bản (trung bình, độ lệch chuẩn, min, max, tứ phân vị) cho các cột dữ liệu số.
* **Trực quan hóa phân bố (Features):**
    * Sử dụng `matplotlib` và `seaborn` để vẽ biểu đồ **histogram** (biểu đồ phân bố) cho tất cả các cột có tiền tố `ft_`, giúp hiểu rõ phân bố của từng feature.
    
## 5. Phân tích Tương quan (Correlation Analysis)

* **Ma trận tương quan:**
    * Tính toán ma trận tương quan Pearson giữa tất cả các cột `ft_` còn lại.
    * Sử dụng `seaborn.heatmap` để trực quan hóa ma trận này, giúp phát hiện các mối quan hệ tuyến tính mạnh (đa cộng tuyến) giữa các feature.
* **Tương quan với biến mục tiêu:**
    * Tính toán riêng mức độ tương quan của tất cả các feature với biến mục tiêu (`ft_co2`).
    * Sắp xếp và hiển thị kết quả theo giá trị tuyệt đối giảm dần để xác định các yếu tố ảnh hưởng mạnh nhất đến `ft_co2`.