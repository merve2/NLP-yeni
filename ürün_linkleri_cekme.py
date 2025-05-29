from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

# Tarayıcı ayarlarını yapıyoruz
options = Options()
options.add_argument("--disable-notifications")
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(options=options)

# Kategori linklerini tanımlıyoruz
kategoriler = [
    "https://www.hepsiburada.com/bilgisayarlar-c-2147483646",
    "https://www.hepsiburada.com/yazicilar-c-3013118",
    "https://www.hepsiburada.com/elektrikli-ev-aletleri-c-17071",
    "https://www.hepsiburada.com/foto-kameralari-c-2147483606",
    "https://www.hepsiburada.com/ses-goruntu-sistemleri-c-17201",
    "https://www.hepsiburada.com/ipl-lazerler-c-60003905",
    "https://www.hepsiburada.com/gunes-koruyucu-urunler-c-32010889",
    "https://www.hepsiburada.com/makyaj-urunleri-c-341425",
    "https://www.hepsiburada.com/erkek-tiras-urunleri-c-26012116",
    "https://www.hepsiburada.com/sac-bakim-urunleri-c-26012111",
    "https://www.hepsiburada.com/cilt-bakim-urunleri-c-32000005",
    "https://www.hepsiburada.com/agiz-bakim-urunleri-c-26012110",
    "https://www.hepsiburada.com/epilasyon-agda-c-80216049",
    "https://www.hepsiburada.com/deterjan-temizlik-urunleri-c-28001525",
    "https://www.hepsiburada.com/bebek-bezi-c-60001048",
    "https://www.hepsiburada.com/mutfak-sarf-malzemeleri-c-60001205",
    "https://www.hepsiburada.com/pet-shop-c-2147483616",
    "https://www.hepsiburada.com/oyuncaklar-c-23031884",
    "https://www.hepsiburada.com/dekorasyon-c-18021300",
    "https://www.hepsiburada.com/elektrik-aydinlatma-urunleri-c-13003201",
    "https://www.hepsiburada.com/mutfak-gerecleri-c-22500",
    "https://www.hepsiburada.com/ev-tekstili-c-2147483618",
    "https://www.hepsiburada.com/kirtasiye-ofis-urunleri-c-2147483643",
    "https://www.hepsiburada.com/ofis-mobilyalari-c-15312",
    "https://www.hepsiburada.com/bayan-giyim-modelleri-c-12087178"
]

# Aynı ürün tekrar eklenmesin diye set kullanıyoruz
uygun_linkler = set()

# Her kategori için işlemleri başlatıyoruz
for kategori_link in kategoriler:
    print("\n---Kategori Başladı:", kategori_link)
    for sayfa in range(1,51):  # Her kategoride ilk 50 sayfaya bak
        url = f"{kategori_link}?sayfa={sayfa}"
        driver.get(url)
        time.sleep(3)  # Sayfanın yüklenmesini bekle

        # Ürün kartlarını bul
        urun_kartlari = driver.find_elements(By.CSS_SELECTOR, "li.productListContent-zAP0Y5msy8OHn5z7T_K_")
        print("Sayfa:", sayfa, "Ürün kartı:", len(urun_kartlari))
        urun_linkleri = []

        # Her ürün kartı için link ve yorum sayısı kontrolü yap
        for kart in urun_kartlari:
            try:
                link = kart.find_element(By.TAG_NAME, "a").get_attribute("href")
                yorum_sayisi = 0
                try:
                    yorum_text = kart.find_element(By.CSS_SELECTOR, "span.rate-module_count__fjUng").text
                    yorum_text = yorum_text.strip("()").replace(".", "")
                    yorum_sayisi = int(yorum_text)
                except:
                    yorum_sayisi = 0

                # 1000'den fazla yorumu olan ürünleri seçiyoruz
                if yorum_sayisi >= 1000:
                    urun_linkleri.append(link)
            except:
                continue

        #  Bu ürünlerin yorumlar sayfasında "Değerlendirme özeti" var mı bakıyoruz
        for link in urun_linkleri:
            if link in uygun_linkler:
                continue  # Önceden eklenen ürünleri atla

            yorumlar_link = link + "-yorumlari"
            driver.execute_script("window.open(arguments[0]);", yorumlar_link)
            driver.switch_to.window(driver.window_handles[-1])  # Yeni açılan sekmeye geç
            time.sleep(4)

            try:
                # Eğer özet varsa, bu ürünü ekle
                driver.find_element(By.XPATH, "//h2[contains(text(), 'Değerlendirme özeti')]")
                uygun_linkler.add(link)
                print("++Eklendi:", link, "Toplam:", len(uygun_linkler))
                if len(uygun_linkler) >= 1000:
                    break
            except:
                print("--Özet yok:", link)

            driver.close()  # Yorumlar sekmesini kapat
            driver.switch_to.window(driver.window_handles[0])  # Ana sekmeye dön

        if len(uygun_linkler) >= 1000:
            break  # 1000 ürün bulunduysa bu kategoriyi bitir

    if len(uygun_linkler) >= 1000:
        print("1000 ürüne ulaşıldı.")
        break  # Tüm aramayı bitir

# Sonuçları dosyaya yazıyoruz
with open("urun_linkleri.txt", "w", encoding="utf-8") as f:
    for link in uygun_linkler:
        f.write(link + "\n")

driver.quit()  # Tarayıcıyı kapatıyoruz
print("Tamamlandı. Toplam uygun ürün:", len(uygun_linkler))