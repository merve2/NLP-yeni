
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import re
import os

txt_dosya = "link_parca_1.txt"
csv_dosya = "yorumlar_parca_1.csv"
dosya_var = os.path.exists(csv_dosya)

zaten_yazilan_yorumlar = set()
if dosya_var:
    with open(csv_dosya, "r", encoding="utf-8") as f:
        import csv
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 3:
                urun_id, yorum, star = row[0], row[1], row[2]
                zaten_yazilan_yorumlar.add((urun_id, yorum, star))

with open(txt_dosya, "r", encoding="utf-8") as f:
    urun_linkleri = [line.strip() for line in f if line.strip()]

def urun_id_bul(link):
    match = re.search(r'pm-([A-Z0-9]+)', link)
    if match:
        return match.group(1)
    match = re.search(r'-p-([A-Z0-9]+)', link)
    if match:
        return match.group(1)
    match = re.search(r'(HBC[A-Z0-9]{5,})', link)
    if match:
        return match.group(1)
    return "urunid-bulunamadi"

def yorum_linki_olustur(link):
    if "-pm-" in link:
        return link.split("?")[0] + "-yorumlari?sayfa="
    else:
        return link + "-yorumlari?sayfa="

def restart_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver = restart_driver()

with open(csv_dosya, mode="a", newline='', encoding="utf-8") as dosya_yorum:
    yazici_yorum = csv.writer(dosya_yorum)
    if not dosya_var:
        yazici_yorum.writerow(["urun_id", "yorum", "star"])

    for urun_linki in urun_linkleri:
        urun_id = urun_id_bul(urun_linki)
        if urun_id == "urunid-bulunamadi":
            print(f"[!] ID bulunamadı, ürün atlanıyor: {urun_linki}")
            continue

        yorum_sayfasi_taban_link = yorum_linki_olustur(urun_linki)
        print(f"\n🔍 Ürün işleniyor: {urun_id}")
        sayfa_no = 1

        while True:
            yorum_sayfa_linki = yorum_sayfasi_taban_link + str(sayfa_no)
            print(f"  Sayfa {sayfa_no}: {yorum_sayfa_linki}")

            try:
                driver.get(yorum_sayfa_linki)
            except (InvalidSessionIdException, WebDriverException):
                print("⚠️ Tarayıcı bağlantısı koptu, yeniden başlatılıyor...")
                driver.quit()
                driver = restart_driver()
                driver.get(yorum_sayfa_linki)

            time.sleep(2)

            try:
                yorum_kartlari = driver.find_elements(By.CSS_SELECTOR, "div.hermes-ReviewCard-module-KaU17BbDowCWcTZ9zzxw")
            except Exception as e:
                print(f"⚠️ Yorumlar alınamadı: {e}")
                break

            if not yorum_kartlari:
                print("  🔚 Yorum sayfaları bitti.")
                break

            yeni_yorum_sayisi = 0
            for kart in yorum_kartlari:
                try:
                    yorum_span = kart.find_element(By.TAG_NAME, "span")
                    yorum = yorum_span.text.strip()
                except:
                    yorum = ""

                star = ""
                try:
                    rating_div = kart.find_element(By.XPATH, "..//div[contains(@class,'RatingPointer')]")
                    if rating_div:
                        star = len(rating_div.find_elements(By.CSS_SELECTOR, "div.star"))
                except:
                    star = ""

                if yorum and (urun_id, yorum, star) not in zaten_yazilan_yorumlar:
                    yazici_yorum.writerow([urun_id, yorum, star])
                    zaten_yazilan_yorumlar.add((urun_id, yorum, star))
                    yeni_yorum_sayisi += 1

            print(f"  ➕ {yeni_yorum_sayisi} yorum eklendi.")
            if yeni_yorum_sayisi == 0:
                break

            sayfa_no += 1
            time.sleep(1)

driver.quit()
print(f"\n🎉 Tüm yorumlar başarıyla '{csv_dosya}' dosyasına kaydedildi.")
