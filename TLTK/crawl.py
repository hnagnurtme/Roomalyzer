import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

# Cấu hình trình duyệt
options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = uc.Chrome(use_subprocess=True, options=options)

list_links = set()


total_pages = 35

for page in range(1, total_pages + 1):
    url = f"https://www.nhatot.com/thue-phong-tro-da-nang?page={page}"
    print(f"🔎 Đang truy cập: {url}")
    driver.get(url)
    time.sleep(5)

    for _ in range(3):  
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "webeqpz"))
        )

   
        divs = driver.find_elements(By.CLASS_NAME, "webeqpz")
        for div in divs:
            try:
                link_element = div.find_element(By.TAG_NAME, "a")
                link = link_element.get_attribute("href")
                if link and link.startswith("https"):
                    list_links.add(link)
            except:
                pass  
    
    except Exception as e:
        print(f" Không tìm thấy dữ liệu trên trang {page}: {e}")

    print(f" Trang {page} lấy được {len(list_links)} link")
    time.sleep(2)


driver.quit()

# Lưu kết quả vào file CSV
df = pd.DataFrame({"Links": list(list_links)})
df.to_csv("links_nhatot.csv", index=False, encoding="utf-8-sig")
print("🎉✅ Đã lưu danh sách link vào links_nhatot.csv")
