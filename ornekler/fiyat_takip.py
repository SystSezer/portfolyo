"""Ürün fiyat takibi — nazik ve kurallara uyan web scraping örneği.

Freelance platformlarındaki "scrape this site into a spreadsheet" / "price monitoring"
işlerinin temiz bir uygulaması. Öne çıkan noktalar:

  - robots.txt kontrol edilir; izin yoksa o adres atlanır
  - istekler arasında bekleme var, User-Agent gizlenmez
  - geçici ağ hataları artan bekleme ile tekrar denenir
  - sonuç CSV'ye eklenir; her çalıştırmada fiyat geçmişi birikir
  - önceki çalıştırmaya göre fiyat değişimi raporlanır

Varsayılan hedef books.toscrape.com — bu site scraping alıştırması için
açıkça bu amaçla yayınlanmış bir demo sitesidir.

Kullanım:
    python fiyat_takip.py
    python fiyat_takip.py --url <adres> --secici "h1" --fiyat-secici ".price_color"
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.robotparser
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Windows konsolu varsayilan olarak cp1254 kullaniyor ve Turkce karakterlerle
# ok isaretlerinde patliyor. Ciktiyi UTF-8'e sabitliyoruz.
for akis in (sys.stdout, sys.stderr):
    if hasattr(akis, "reconfigure"):
        akis.reconfigure(encoding="utf-8", errors="replace")

KULLANICI_AJANI = "FiyatTakip/1.0 (kisisel fiyat takibi; iletisim: ornek@eposta.com)"
BEKLEME_SANIYE = 2.0
DENEME_SAYISI = 3

VARSAYILAN_URLLER = [
    "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
    "https://books.toscrape.com/catalogue/soumission_998/index.html",
]


def robots_izin_veriyor(url: str) -> bool:
    """robots.txt'e uy. Dosya yoksa/okunamazsa izinli sayilir (yaygin kabul)."""
    parca = urlparse(url)
    kok = f"{parca.scheme}://{parca.netloc}"
    ayristirici = urllib.robotparser.RobotFileParser()
    ayristirici.set_url(f"{kok}/robots.txt")
    try:
        ayristirici.read()
    except Exception:
        return True
    return ayristirici.can_fetch(KULLANICI_AJANI, url)


def sayfayi_getir(url: str) -> str | None:
    """Gecici hatalarda artan bekleme ile tekrar dener; kalici hatada vazgecer."""
    for deneme in range(1, DENEME_SAYISI + 1):
        try:
            cevap = requests.get(url, headers={"User-Agent": KULLANICI_AJANI}, timeout=20)
        except requests.RequestException as hata:
            print(f"  ağ hatası ({deneme}/{DENEME_SAYISI}): {hata}")
        else:
            if cevap.status_code == 200:
                # Sunucu Content-Type'ta charset bildirmezse requests latin-1 varsayar
                # ve '£' -> 'Â£', 'ş' -> 'ÅŸ' olur. Gercek kodlamayi tespit ettiriyoruz.
                if "charset" not in cevap.headers.get("Content-Type", "").lower():
                    cevap.encoding = cevap.apparent_encoding or "utf-8"
                return cevap.text
            if 400 <= cevap.status_code < 500 and cevap.status_code != 429:
                print(f"  kalıcı hata {cevap.status_code} — bu adres atlanıyor")
                return None
            print(f"  geçici hata {cevap.status_code} ({deneme}/{DENEME_SAYISI})")
        time.sleep(BEKLEME_SANIYE * deneme)  # her denemede biraz daha bekle
    return None


def fiyati_sayiya_cevir(ham: str) -> float | None:
    """'£51.77' / '1.299,90 TL' gibi yazımlardan sayı çıkarır."""
    temiz = re.sub(r"[^\d,.]", "", ham or "")
    if not temiz:
        return None
    # Son ayırıcı ondalık kabul edilir: '1.299,90' -> 1299.90 ; '1,299.90' -> 1299.90
    if "," in temiz and "." in temiz:
        if temiz.rfind(",") > temiz.rfind("."):
            temiz = temiz.replace(".", "").replace(",", ".")
        else:
            temiz = temiz.replace(",", "")
    elif "," in temiz:
        temiz = temiz.replace(",", ".")
    try:
        return float(temiz)
    except ValueError:
        return None


def urunu_oku(url: str, baslik_secici: str, fiyat_secici: str) -> dict | None:
    print(f"→ {url}")
    if not robots_izin_veriyor(url):
        print("  robots.txt izin vermiyor — atlanıyor")
        return None

    html = sayfayi_getir(url)
    if html is None:
        return None

    corba = BeautifulSoup(html, "html.parser")
    baslik_etiketi = corba.select_one(baslik_secici)
    fiyat_etiketi = corba.select_one(fiyat_secici)

    if baslik_etiketi is None or fiyat_etiketi is None:
        # Sitenin HTML yapısı değişmiş olabilir — sessizce boş satır yazmak yerine uyar
        print("  seçici eşleşmedi (site yapısı değişmiş olabilir)")
        return None

    ham_fiyat = fiyat_etiketi.get_text(strip=True)
    return {
        "tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "url": url,
        "urun": baslik_etiketi.get_text(strip=True),
        "fiyat_ham": ham_fiyat,
        "fiyat": fiyati_sayiya_cevir(ham_fiyat),
    }


def onceki_fiyatlar(dosya: Path) -> dict[str, float]:
    """CSV'deki her ürün için en son kaydedilen fiyat."""
    if not dosya.exists():
        return {}
    son: dict[str, float] = {}
    with dosya.open(encoding="utf-8-sig", newline="") as f:
        for satir in csv.DictReader(f):
            try:
                son[satir["url"]] = float(satir["fiyat"])
            except (KeyError, TypeError, ValueError):
                continue
    return son


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Ürün fiyatlarını takip eder.")
    ayristirici.add_argument("--url", action="append", help="Takip edilecek adres (birden fazla kez verilebilir)")
    ayristirici.add_argument("--secici", default="h1", help="Ürün adı CSS seçicisi")
    ayristirici.add_argument("--fiyat-secici", default=".price_color", help="Fiyat CSS seçicisi")
    ayristirici.add_argument("--cikti", type=Path, default=Path("fiyat_gecmisi.csv"))
    args = ayristirici.parse_args()

    urller = args.url or VARSAYILAN_URLLER
    onceki = onceki_fiyatlar(args.cikti)
    sonuclar: list[dict] = []

    for sira, url in enumerate(urller):
        if sira:
            time.sleep(BEKLEME_SANIYE)  # siteye yüklenmemek için
        kayit = urunu_oku(url, args.secici, args.fiyat_secici)
        if kayit:
            sonuclar.append(kayit)

    if not sonuclar:
        print("\nHiçbir ürün okunamadı.")
        return

    yeni_dosya = not args.cikti.exists()
    with args.cikti.open("a", encoding="utf-8-sig", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=["tarih", "url", "urun", "fiyat_ham", "fiyat"])
        if yeni_dosya:
            yazici.writeheader()
        yazici.writerows(sonuclar)

    print(f"\n{len(sonuclar)} ürün kaydedildi -> {args.cikti}")
    print("\nDeğişim raporu")
    print("-" * 60)
    for kayit in sonuclar:
        eski = onceki.get(kayit["url"])
        yeni = kayit["fiyat"]
        if eski is None or yeni is None:
            durum = "ilk kayıt"
        elif yeni > eski:
            durum = f"↑ zam  {eski:.2f} → {yeni:.2f}  (+{yeni - eski:.2f})"
        elif yeni < eski:
            durum = f"↓ indirim  {eski:.2f} → {yeni:.2f}  (-{eski - yeni:.2f})"
        else:
            durum = "= değişmedi"
        print(f"{kayit['urun'][:38]:38s} {kayit['fiyat_ham']:>10s}  {durum}")


if __name__ == "__main__":
    main()
