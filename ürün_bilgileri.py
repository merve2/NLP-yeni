from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import time
import re

# Ürün ID'sini bulur. Linkte yoksa sayfa kaynağında arar.
def urun_id_bul(surucu, link):
    # Önce link üzerinden ürün kodunu almaya çalış
    eslesme = re.search(r'-(pm|p)-([A-Z0-9]+)', link)
    if eslesme and (eslesme.group(2).startswith("HBC") or eslesme.group(2).startswith("HBV")):
        return eslesme.group(2)
    # Linkte yoksa, sayfa kaynağında ve özel attribute'larda arama yap
    try:
        kaynak = surucu.page_source
        for p in [r'"productId"\s*:\s*"([A-Z0-9]+)"',
                  r'data-productid="([A-Z0-9]+)"',
                  r'productid=([A-Z0-9]+)',
                  r'"sku":"([A-Z0-9]+)"']:
            eslesme = re.search(p, kaynak)
            if eslesme:
                pid = eslesme.group(1)
                if pid.startswith("HBC") or pid.startswith("HBV"):
                    return pid
        matches = re.findall(r'HB[CV][A-Z0-9]{8,}', kaynak)
        if matches:
            return matches[0]
    except:
        pass
    try:
        tum_elemanlar = surucu.find_elements(By.XPATH, '//*[@data-productid or @data-product-id]')
        for elem in tum_elemanlar:
            for attr in ['data-productid', 'data-product-id']:
                val = elem.get_attribute(attr)
                if val and (val.startswith("HBC") or val.startswith("HBV")):
                    return val.strip()
    except:
        pass
    try:
        meta_etiketler = surucu.find_elements(By.XPATH, '//meta')
        for meta in meta_etiketler:
            content = meta.get_attribute('content') or ''
            if (content.startswith("HBC") or content.startswith("HBV")) and len(content) > 8:
                return content.strip()
    except:
        pass
    return "BILINMIYOR"

# Ürün fiyatını farklı HTML yapılarında bulmaya çalışır.
def fiyat_al(surucu):
    xpathler = [
        '//*[@data-test-id="default-price"]//span',
        '//*[@data-test-id="price-current-price"]',
        '//*[@itemprop="price"]',
        '//*[@id="offering-price"]',
        '//span[contains(@class, "price") and contains(text(),"TL")]',
        '//span[contains(text(),"TL")]',
    ]
    for xp in xpathler:
        try:
            eleman = surucu.find_element(By.XPATH, xp)
            metin = eleman.text.strip()
            if metin and "TL" in metin:
                return metin
        except NoSuchElementException:
            continue
    return "Fiyat bulunamadı"

# Ürün fotoğrafının bağlantısını döndürür.
def foto_link_al(surucu):
    seciciler = [
        "img.i9jTSpEeoI29_M1mOKct",
        "img.hb-HbImage-view__image",
        "img[src*='hepsiburada.net']",
        "img.product-image",
        "img"
    ]
    for sec in seciciler:
        try:
            img = surucu.find_element(By.CSS_SELECTOR, sec)
            src = img.get_attribute("src") or img.get_attribute("data-src")
            if src and len(src) > 10:
                if src.startswith("/"):
                    src = "https://productimages.hepsiburada.net" + src
                elif src.startswith("http"):
                    pass
                else:
                    src = "https://productimages.hepsiburada.net/" + src
                return src
        except:
            continue
    return ""

# Ürünün ortalama yıldız puanını bulur.
def puan_al(surucu):
    try:
        meta = surucu.find_element(By.XPATH, "//meta[@itemprop='ratingValue']")
        v = meta.get_attribute("content")
        if v:
            return v.replace(",", ".").strip()
    except:
        pass

    try:
        el = surucu.find_element(By.XPATH, "//span[@data-test-id='review-score']")
        v = el.text.strip()
        if v:
            return v.replace(",", ".")
    except:
        pass

    try:
        el = surucu.find_element(By.XPATH, "//span[contains(text(),'/5')]")
        v = el.text.strip().split("/")[0].replace(",", ".")
        if v:
            return v
    except:
        pass

    try:
        tum_elemanlar = surucu.find_elements(By.XPATH, "//*[contains(text(), 'puan') or contains(text(), 'yıldız') or contains(text(), '/5')]")
        for el in tum_elemanlar:
            txt = el.text
            eslesenler = re.findall(r'([1-5][\.,]\d{1,2})', txt)
            if eslesenler:
                return eslesenler[0].replace(",", ".")
    except:
        pass

    try:
        tum_elemanlar = surucu.find_elements(By.XPATH, "//span | //div")
        for el in tum_elemanlar:
            txt = el.text.strip().replace(",", ".")
            if re.fullmatch(r"[1-5]\.\d{1,2}", txt):
                return txt
    except:
        pass

    return "0.0"

# Ürünün "Değerlendirme özeti" metnini bulur.
def ozet_al(surucu, urun_url):
    yorum_url = urun_url
    if not yorum_url.endswith("/"):
        yorum_url += "-"
    if "-yorumlari" not in yorum_url:
        yorum_url += "yorumlari?sayfa=1"
    else:
        if "?sayfa=" not in yorum_url:
            yorum_url += "?sayfa=1"
    surucu.get(yorum_url)

    try:
        # Özet başlığının hemen altındaki paragrafı bekle ve al
        p_elem = WebDriverWait(surucu, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//h2[normalize-space()='Değerlendirme özeti']/following-sibling::p[1]"
            ))
        )
        ozet = p_elem.text.strip()
        if len(ozet) > 40 and len(ozet.split()) > 7:
            return ozet
    except TimeoutException:
        return ""
    except Exception:
        return ""
    return ""

# 5-4-3-2-1 yıldız dağılımını döndürür.
def star_dagilimi_al(surucu):
    stars = {"5": "0", "4": "0", "3": "0", "2": "0", "1": "0"}
    try:
        kutular = surucu.find_elements(By.CSS_SELECTOR, "div.hermes-RateBox-module-wUSygDPCtThyMtSVappE")
        for kutu in kutular:
            try:
                star = kutu.find_element(By.CSS_SELECTOR, "span.hermes-RateBox-module-xeSDRZIpi8v5UAr4zqkt").text.strip()
                sayi = kutu.find_element(By.CSS_SELECTOR, "span.hermes-RateBox-module-NOZHKkFJSLqZCPcw8l1c").text.strip()
                if star in stars:
                    stars[star] = sayi
            except:
                continue
    except:
        pass
    return stars

# ANA İŞLEM BLOĞU BAŞLIYOR

# Tarayıcı başlatma ayarlarını yap
ayarlar = Options()
ayarlar.add_argument("--start-maximized")
ayarlar.add_argument("--disable-notifications")
ayarlar.add_experimental_option("excludeSwitches", ["enable-logging"])
surucu = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=ayarlar)

# Daha önce topladığın ürün linklerini oku
with open("urun_linkleri.txt", "r", encoding="utf-8") as f:
    urun_linkleri = [satir.strip() for satir in f if satir.strip()]

# Sonuçları yazacağın CSV dosyasını oluştur
with open("urunler.csv", "w", newline='', encoding="utf-8") as dosya:
    yazici = csv.writer(dosya)
    # Kolon başlıklarını yaz
    yazici.writerow([
        "urun_id", "urun_adi", "fiyat", "foto_link",
        "yorum_ozeti", "ortalama_star_puani",
        "5star", "4star", "3star", "2star", "1star"
    ])
    # Her ürün linki için döngü başlat
    for sira, link in enumerate(urun_linkleri, 1):
        print(f"{sira}. ürün işleniyor...")
        try:
            # Ürün sayfasına git
            surucu.get(link)
            # Ürün adı geldiyse işlemlere başla
            try:
                WebDriverWait(surucu, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
                )
            except:
                time.sleep(2)
            urun_id = urun_id_bul(surucu, link)
            try:
                urun_adi = surucu.find_element(By.CSS_SELECTOR, "h1").text.strip()
            except:
                urun_adi = "Ürün adı bulunamadı!"
            fiyat = fiyat_al(surucu)
            foto_link = foto_link_al(surucu)
            puan = puan_al(surucu)
            ozet = ozet_al(surucu, link)
            star_dagilimi = star_dagilimi_al(surucu)
            # Tüm ürün bilgisini csv'ye yaz
            yazici.writerow([
                urun_id, urun_adi, fiyat, foto_link,
                ozet, puan,
                star_dagilimi["5"], star_dagilimi["4"], star_dagilimi["3"], star_dagilimi["2"], star_dagilimi["1"]
            ])
            print(f"   {urun_adi[:40]}... (ID: {urun_id}) ***Puan: {puan} ***Değerlendirme Özeti Uzunluk: {len(ozet)}")
        except Exception as ex:
            print(f" HATA: {link} - {ex}")

# Tüm ürünler işlendiyse tarayıcıyı kapat
surucu.quit()
print("\nTüm ürünler başarıyla 'urunler.csv' dosyasına kaydedildi.")