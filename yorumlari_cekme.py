from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import re
import os

yorumlar_csv = "yorumlar_.csv"
islenenler_dosya = "islenenler.txt"

# Daha önce işlenen ürünlerin ID'lerini okuttuk
if os.path.exists(islenenler_dosya):
    with open(islenenler_dosya, "r", encoding="utf-8") as f:
        islenen_idler = set(line.strip() for line in f if line.strip())
else:
    islenen_idler = set()

# Ürün linklerini okuttuk
    with open("urun_linkleri.txt", "r", encoding="utf-8") as f:
    urun_linkleri = [line.strip() for line in f if line.strip()]

# Ürün ID lerini bulduk
def urun_id_bul(link):
    # p-
    match = re.search(r'p-([A-Z0-9]+)', link)
    if match:
        return match.group(1)
    # pm-
    match = re.search(r'pm-([A-Z0-9]+)', link)
    if match:
        return match.group(1)
    # HBC
    match = re.search(r'(HBC[A-Z0-9]{5,})', link)
    if match:
        return match.group(1)
    # Değişik yapıda Id ler
    match = re.search(r'[-/]([A-Z0-9]{6,})', link)
    if match:
        return match.group(1)
    return "urunid-bulunamadi"

# Yorumlar linki oluşturduk
def yorum_linki_olustur(link):
    if "-pm-" in link:
        return link.split("?")[0] + "-yorumlari?sayfa="
    else:
        return link + "-yorumlari?sayfa="

# Tarayıcı ayarları
ayarlar = Options()
ayarlar.add_argument("--start-maximized")
ayarlar.add_argument("--disable-notifications")
ayarlar.add_experimental_option("excludeSwitches", ["enable-logging"])

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=ayarlar)
# Yorumlar dosyasını ekleme modunda açıp CSV yazıcı oluşturduk
with open(yorumlar_csv, mode="a", newline='', encoding="utf-8") as dosya_yorum:
    yazici_yorum = csv.writer(dosya_yorum)
    # Eğer dosya yeni açıldıysa başlıkları yaz
    if os.stat(yorumlar_csv).st_size == 0:
        yazici_yorum.writerow(["urun_id", "yorum", "star"])

    for urun_linki in urun_linkleri:
        urun_id = urun_id_bul(urun_linki)
        if urun_id == "urunid-bulunamadi":
            print(f"UYARI: Ürün ID bulunamadı! Link: {urun_linki}")
            continue

        # Eğer zaten işlendiyse atla
        if urun_id in islenen_idler:
            print(f"{urun_id} zaten işlenmiş, atlanıyor...")
            continue

        yorum_sayfasi_taban_link = yorum_linki_olustur(urun_linki)
        print(f"\nİşleniyor: {urun_id} ({urun_linki})")
        yorumlar = []
        sayfa_no = 1
        try:
            while True:
                yorum_sayfa_linki = yorum_sayfasi_taban_link + str(sayfa_no)  # O anki sayfa linkini oluştur
                print(f"  Sayfa {sayfa_no}: {yorum_sayfa_linki}")
                driver.get(yorum_sayfa_linki)
                time.sleep(3)

                yorum_kartlari = driver.find_elements(By.CSS_SELECTOR, "div.hermes-ReviewCard-module-KaU17BbDowCWcTZ9zzxw")
                if not yorum_kartlari:
                    print(" ---Yorum sayfaları bitti---")
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
                     # Yıldız puanını bulmak için geziliyor
                        parent = kart.find_element(By.XPATH, "..")
                        rating_div = None
                        try:
                            rating_div = parent.find_element(By.CSS_SELECTOR, "div.hermes-RatingPointer-module-UefD0t2XvgGWsKdLkNoX")
                        except:
                            grandparent = parent.find_element(By.XPATH, "..")
                            try:
                                rating_div = grandparent.find_element(By.CSS_SELECTOR, "div.hermes-RatingPointer-module-UefD0t2XvgGWsKdLkNoX")
                            except:
                                rating_div = None
                        if rating_div:
                            star = len(rating_div.find_elements(By.CSS_SELECTOR, "div.star"))
                    except:
                        star = ""
                    # YORUM EKLEME KISMI
                    if yorum and (yorum, star) not in yorumlar:
                        yorumlar.append((yorum, star))
                        yazici_yorum.writerow([urun_id, yorum, star]) # CSV dosyasına yeni satır olarak ekle
                        yeni_yorum_sayisi += 1

                print(f"  {yeni_yorum_sayisi} yorum eklendi. Toplam: {len(yorumlar)}")
                if yeni_yorum_sayisi == 0:
                    break
                sayfa_no += 1

            # Eğer bu üründen en az bir yorum başarıyla çekildiyse, işlenenlere kaydet
            if len(yorumlar) > 0:
                with open(islenenler_dosya, "a", encoding="utf-8") as f:
                    f.write(urun_id + "\n")
                islenen_idler.add(urun_id)
                print(f"{urun_id} başarıyla kaydedildi ve işlenenler listesine eklendi.")
            else:
                print(f"{urun_id} için hiç yorum bulunamadı.")
        except Exception as e:
            print(f"HATA! {urun_id} çekilirken hata oluştu: {e}")
            # Bu durumda ürün işlenmiş olarak eklenmiyor, bir sonraki çalışmada tekrar denenebilir

driver.quit()
print("\nTüm yorumlar başarıyla 'yorumlar.csv' dosyasına kaydedildi.")