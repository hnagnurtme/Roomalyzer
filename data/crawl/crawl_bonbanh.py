import requests
from bs4 import BeautifulSoup
import re
import time
import random
import pandas as pd

# ==========================================
# CẤU HÌNH CRAWLER
# ==========================================
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9"
}
base_url = "https://bonbanh.com"
session = requests.Session()
session.headers.update(headers)

# CHÚ Ý: Chỉnh các biến này thành 999 để cào TOÀN BỘ. Mình đang để nhỏ để bạn test.
MAX_BRANDS = 2
MAX_MODELS_PER_BRAND = 2
MAX_PAGES_PER_MODEL = 1

all_cars_data = []
danh_muc_xe = [] # List lưu trữ Hãng và Dòng xe

# ==========================================
# HÀM LÀM SẠCH DỮ LIỆU
# ==========================================
def clean_text(text):
    return re.sub(r'\s+', ' ', str(text)).strip()

def clean_price(price_str):
    if not isinstance(price_str, str) or 'thỏa' in price_str.lower() or 'thương' in price_str.lower():
        return None
    price_str = price_str.lower()
    total_trieu = 0
    ty = re.search(r'(\d+)\s*tỷ', price_str)
    if ty: total_trieu += int(ty.group(1)) * 1000
    tr = re.search(r'(\d+)\s*triệu', price_str)
    if tr: total_trieu += int(tr.group(1))
    return total_trieu if total_trieu > 0 else None

def clean_odo(odo_str):
    if not isinstance(odo_str, str): return None
    nums = re.findall(r'\d+', odo_str)
    if not nums: return None
    return int(''.join(nums))

# ==========================================
# GIAI ĐOẠN 1: QUÉT HÃNG VÀ DÒNG XE
# ==========================================
print("🚀 GIAI ĐOẠN 1: ĐANG THU THẬP DANH MỤC HÃNG VÀ DÒNG XE...")
home_res = session.get(base_url, timeout=10)
home_soup = BeautifulSoup(home_res.text, "html.parser")

brand_tags = home_soup.select("#m-cate ul a.mtop-item")
brands_list = [{"name": t.text.strip(), "href": t['href']} for t in brand_tags if 'href' in t.attrs]

for brand in brands_list[:MAX_BRANDS]:
    brand_name = brand['name']
    brand_href = brand['href'] # VD: "oto/bentley"
    
    print(f"\n👉 Đang quét các dòng xe của hãng: {brand_name.upper()}")
    brand_url = f"{base_url}/{brand_href}"
    
    try:
        b_res = session.get(brand_url, timeout=10)
        b_soup = BeautifulSoup(b_res.text, "html.parser")
        
        # Tìm tất cả các link có dạng "oto/bentley-tên_dòng_xe"
        prefix = f"{brand_href}-"
        models_dict = {}
        
        for a in b_soup.find_all('a', href=True):
            href = a['href']
            # Lọc link dòng xe hợp lệ (Không chứa page, không chứa dấu ?)
            if href.startswith(prefix) and "page," not in href and "?" not in href:
                model_name = clean_text(a.text)
                # Loại bỏ các link rác có chứa cụm từ "Bán xe..."
                if model_name and len(model_name) > 1 and "Bán xe" not in model_name:
                    models_dict[href] = model_name
        
        # Lưu vào danh mục tổng
        for m_href, m_name in models_dict.items():
            danh_muc_xe.append({
                "Hãng_Xe": brand_name,
                "Dòng_Xe": m_name,
                "URL_Dòng_Xe": m_href
            })
            print(f"   + Tìm thấy dòng: {m_name}")
            
        time.sleep(1) # Trễ nhẹ chống block
        
    except Exception as e:
        print(f" Lỗi quét hãng {brand_name}: {e}")

# XUẤT FILE DANH MỤC NGAY LẬP TỨC
if danh_muc_xe:
    df_danhmuc = pd.DataFrame(danh_muc_xe).drop_duplicates()
    df_danhmuc.to_csv('danh_sach_hang_dong_xe.csv', index=False, encoding='utf-8-sig')
    print("\n✅ Đã lưu file 'danh_sach_hang_dong_xe.csv'!")

# ==========================================
# GIAI ĐOẠN 2: CÀO CHI TIẾT TỪNG XE THEO DÒNG
# ==========================================
print("\n🚀 GIAI ĐOẠN 2: BẮT ĐẦU CÀO CHI TIẾT TỪNG XE...")

# Lặp qua danh sách dòng xe vừa thu thập được
for idx, model_data in enumerate(danh_muc_xe[:MAX_BRANDS * MAX_MODELS_PER_BRAND]):
    hang_xe = model_data["Hãng_Xe"]
    dong_xe = model_data["Dòng_Xe"]
    model_href = model_data["URL_Dòng_Xe"] # VD: oto/bentley-flying_spur
    
    print(f"\n[{idx+1}] ĐANG CÀO: {hang_xe} -> {dong_xe}")
    
    for page in range(1, MAX_PAGES_PER_MODEL + 1):
        list_url = f"{base_url}/{model_href}/page,{page}"
        print(f"  + Trang {page}...")
        
        try:
            res = session.get(list_url, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            car_items = soup.select(".car-item")
            if not car_items:
                print("    -> Hết xe ở dòng này. Chuyển dòng khác.")
                break
                
            for item in car_items:
                a_tag = item.select_one("a[href]")
                if not a_tag: continue
                
                # --- [MỚI] BẮT TỈNH/THÀNH PHỐ TỪ TRANG DANH SÁCH ---
                # Nằm trong thẻ <div class="cb4">
                city_tag = item.select_one(".cb4")
                tinh_thanh = clean_text(city_tag.text) if city_tag else "Không rõ"
                
                car_link = base_url + "/" + a_tag['href']
                
                try:
                    detail_res = session.get(car_link, timeout=10)
                    detail_soup = BeautifulSoup(detail_res.text, "html.parser")
                    
                    car_info = {
                        "URL": car_link,
                        "Hãng_Xe": hang_xe,
                        "Dòng_Xe": dong_xe,
                        "Tỉnh_Thành": tinh_thanh  # <--- Đưa Tỉnh/Thành vào dữ liệu
                    }
                    
                    # Lấy Tên xe & Giá
                    title_tag = detail_soup.select_one("h1")
                    if title_tag:
                        full_title = clean_text(title_tag.text)
                        if " - " in full_title:
                            ten_xe, gia_chu = full_title.rsplit(" - ", 1)
                            car_info["Tên_Xe"] = ten_xe.replace("Xe ", "").strip()
                            car_info["Giá_Triệu_VNĐ"] = clean_price(gia_chu)
                            car_info["Giá_Gốc"] = gia_chu.strip()
                        else:
                            car_info["Tên_Xe"] = full_title.replace("Xe ", "").strip()
                            
                    # Lấy Mã tin
                    code_match = re.search(r'Mã tin\s*:\s*(\d+)', detail_soup.text)
                    if code_match: car_info["Mã_Tin"] = code_match.group(1)
                    
                    # Bóc tách Bảng thông số kỹ thuật
                    for row in detail_soup.select(".row, .row_last"):
                        lbl = row.select_one("label")
                        inp = row.select_one(".inp")
                        if lbl and inp:
                            key = clean_text(lbl.text).replace(":", "")
                            val = clean_text(inp.text)
                            if key == "Số Km đã đi":
                                car_info["Odo_Km"] = clean_odo(val)
                            else:
                                car_info[key] = val
                    
                    # Lấy Mô tả
                    des_tag = detail_soup.select_one(".des_txt, .des-txt")
                    if des_tag: car_info["Mô_Tả"] = clean_text(des_tag.text.replace("\n", " | "))
                    
                    # --- [MỚI] LẤY NGƯỜI BÁN & ĐỊA CHỈ CHI TIẾT TỪ TRANG CHI TIẾT ---
                    contact_box = detail_soup.select_one(".contact-txt, .contact_txt")
                    if contact_box:
                        cname = contact_box.select_one(".cname")
                        if cname: car_info["Người_Bán"] = clean_text(cname.text)
                        
                        # 1. Hack lấy số điện thoại bị ẩn trong thẻ script của Bonbanh
                        phones = []
                        for script in contact_box.find_all("script"):
                            p_match = re.search(r"\'([\d\s\.\-]+)\'", script.text)
                            if p_match: phones.append(p_match.group(1).strip())
                        if phones: car_info["Điện_Thoại"] = " - ".join(phones)
                        
                        # Lấy text thô và xóa tên người bán đi để dễ xử lý
                        raw_contact = contact_box.text
                        if cname: raw_contact = raw_contact.replace(cname.text, "")
                        
                        # Mẹo: Tách các từ khóa bị dính liền nhau (Điện thoạiĐịa chỉ -> Điện thoại Địa chỉ)
                        raw_contact = re.sub(r'(Điện thoại|Địa chỉ|Website|ĐT|Tel)', r' \1 ', raw_contact)
                        raw_contact = clean_text(raw_contact)
                        
                        # 2. Trích xuất Website
                        web_match = re.search(r'Website\s*:?\s*([a-zA-Z0-9\.\-\/]+)', raw_contact, re.IGNORECASE)
                        if web_match: car_info["Website"] = web_match.group(1).strip()
                            
                        # 3. Trích xuất Điện thoại (Dự phòng nếu web không ẩn trong script)
                        if "Điện_Thoại" not in car_info or not car_info["Điện_Thoại"]:
                            phone_match = re.search(r'(?:Điện thoại|ĐT|Tel)\s*:?\s*([\d\.\-\s]{8,})', raw_contact, re.IGNORECASE)
                            if phone_match: car_info["Điện_Thoại"] = phone_match.group(1).strip()
                                
                        # 4. Trích xuất Địa chỉ (Bắt từ chữ "Địa chỉ" đến trước chữ "Điện thoại" hoặc "Website")
                        add_match = re.search(r'Địa chỉ\s*:?\s*(.*?)(?=(?:Điện thoại|ĐT|Tel|Website|$))', raw_contact, re.IGNORECASE)
                        if add_match: 
                            car_info["Địa_Chỉ_Chi_Tiết"] = clean_text(add_match.group(1).strip(" -:"))
                        
                    all_cars_data.append(car_info)
                    time.sleep(random.uniform(0.5, 1.5))
                    
                except Exception as e:
                    print(f"    Lỗi quét chi tiết xe: {e}")
                    continue
                    
        except Exception as e:
            continue

# ==========================================
# XUẤT DỮ LIỆU CUỐI CÙNG
# ==========================================
if all_cars_data:
    df_cars = pd.DataFrame(all_cars_data)
    
    # Sắp xếp các cột quan trọng lên đầu
    priority_cols = ['Mã_Tin', 'Hãng_Xe', 'Dòng_Xe', 'Tên_Xe', 'Giá_Triệu_VNĐ', 'Giá_Gốc', 
                     'Năm sản xuất', 'Tình trạng', 'Odo_Km', 'Xuất xứ', 'Động cơ', 'Hộp số', 
                     'Màu ngoại thất', 'Số chỗ ngồi', 'Số cửa', 'Dẫn động', 
                     'Tỉnh_Thành', 'Người_Bán', 'Điện_Thoại', 'Địa_Chỉ_Chi_Tiết', 'Website', 'Mô_Tả']
    existing_cols = [c for c in priority_cols if c in df_cars.columns]
    other_cols = [c for c in df_cars.columns if c not in existing_cols]
    df_cars = df_cars[existing_cols + other_cols]
    
    df_cars.to_csv('clean_data_oto_chuan_hoa.csv', index=False, encoding='utf-8-sig')
    print(f"\n🎉 HOÀN TẤT CÀO DỮ LIỆU! Đã xuất {len(df_cars)} dòng xe siêu sạch vào 'clean_data_oto_chuan_hoa.csv'.")
else:
    print("\n[!] Không thu thập được dữ liệu.")