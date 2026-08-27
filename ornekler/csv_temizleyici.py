"""CSV / Excel liste temizleyici.

Freelance platformlarinda en sik gorulen "data entry / data cleaning" isinin
otomatiklestirilmis hali. Musteriden gelen dagini bir kisi listesini alir:

  - bastaki/sondaki bosluklari ve cift bosluklari temizler
  - isimleri duzgun buyuk/kucuk harfe cevirir (Turkce karakterlere dikkat ederek)
  - e-postalari kucuk harfe cevirir ve gecerli olmayanlari isaretler
  - telefon numaralarini tek bir formata getirir (+90 5XX XXX XX XX)
  - tarihleri ISO formatina (YYYY-MM-DD) cevirir
  - e-postaya gore tekrar eden satirlari birlestirir
  - temiz dosyayi ve "elle bakilmasi gerekenler" raporunu ayri ayri yazar

Kullanim:
    python csv_temizleyici.py girdi.csv
    python csv_temizleyici.py girdi.csv --cikti temiz.csv --rapor sorunlu.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path

EPOSTA_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.I)

# Turkce'de "i" -> "I" degil "İ" olur; .title() bunu bozar, o yuzden elle esliyoruz.
_BUYUK = {"i": "İ", "ı": "I", "ş": "Ş", "ğ": "Ğ", "ü": "Ü", "ö": "Ö", "ç": "Ç"}
_KUCUK = {"I": "ı", "İ": "i", "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç"}

TR_AYLAR = {
    "ocak": "01", "şubat": "02", "subat": "02", "mart": "03", "nisan": "04",
    "mayıs": "05", "mayis": "05", "haziran": "06", "temmuz": "07", "ağustos": "08",
    "agustos": "08", "eylül": "09", "eylul": "09", "ekim": "10", "kasım": "11",
    "kasim": "11", "aralık": "12", "aralik": "12",
}

# Cok denenen tarih yazimlari - ilk tutan kazanir
TARIH_KALIPLARI = [
    "%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y",
    "%d-%m-%Y", "%Y/%m/%d", "%d %B %Y", "%d.%m.%y",
]


def bosluk_temizle(deger) -> str:
    """Bosluklari sadelestirir.

    Gercek musteri dosyalarinda satirlarda fazladan virgul olabiliyor; csv.DictReader
    bu durumda deger olarak liste veriyor. Bu yuzden tip kontrolu sart.
    """
    if deger is None:
        return ""
    if isinstance(deger, (list, tuple)):
        deger = " ".join(str(p) for p in deger if p)
    return re.sub(r"\s+", " ", str(deger).strip())


def tr_buyuk(harf: str) -> str:
    return _BUYUK.get(harf, harf.upper())


def tr_kucuk(harf: str) -> str:
    return _KUCUK.get(harf, harf.lower())


def isim_duzelt(ham: str) -> str:
    """'ahMET   yILMAZ' -> 'Ahmet Yılmaz'. Turkce i/I sorununu dogru cozer."""
    temiz = bosluk_temizle(ham)
    if not temiz:
        return ""
    kelimeler = []
    for kelime in temiz.split(" "):
        if not kelime:
            continue
        kelimeler.append(tr_buyuk(kelime[0]) + "".join(tr_kucuk(h) for h in kelime[1:]))
    return " ".join(kelimeler)


def eposta_duzelt(ham: str) -> tuple[str, str]:
    """(temiz_eposta, sorun) dondurur. Sorun yoksa bos string."""
    temiz = bosluk_temizle(ham).lower().replace(" ", "")
    if not temiz:
        return "", "e-posta bos"
    # yaygin yazim hatalari
    temiz = temiz.replace("gmail.co m", "gmail.com").replace(",", ".")
    if not EPOSTA_RE.match(temiz):
        return temiz, "e-posta formati gecersiz"
    return temiz, ""


def telefon_duzelt(ham: str, ulke_kodu: str = "90") -> tuple[str, str]:
    """Turkiye cep numarasini +90 5XX XXX XX XX formatina getirir."""
    rakamlar = re.sub(r"\D", "", ham or "")
    if not rakamlar:
        return "", "telefon bos"

    if rakamlar.startswith("00" + ulke_kodu):
        rakamlar = rakamlar[len("00" + ulke_kodu):]
    elif rakamlar.startswith(ulke_kodu) and len(rakamlar) > 10:
        rakamlar = rakamlar[len(ulke_kodu):]
    elif rakamlar.startswith("0"):
        rakamlar = rakamlar[1:]

    if len(rakamlar) != 10:
        return ham.strip(), f"telefon {len(rakamlar)} haneli (10 bekleniyor)"
    if not rakamlar.startswith("5"):
        return f"+{ulke_kodu} {rakamlar}", "cep numarasi gibi gorunmuyor"

    return f"+{ulke_kodu} {rakamlar[:3]} {rakamlar[3:6]} {rakamlar[6:8]} {rakamlar[8:]}", ""


def tarih_duzelt(ham: str) -> tuple[str, str]:
    temiz = bosluk_temizle(ham)
    if not temiz:
        return "", ""
    # "03 Mart 2024" gibi Turkce ay adlarini once sayiya cevir
    # (strptime'in %B'si sistem yereline bagli, guvenilmez)
    for ad, no in TR_AYLAR.items():
        if ad in temiz.lower():
            temiz = re.sub(ad, no, temiz, flags=re.I).replace(" ", ".")
            break
    for kalip in TARIH_KALIPLARI:
        try:
            return datetime.strptime(temiz, kalip).strftime("%Y-%m-%d"), ""
        except ValueError:
            continue
    return temiz, "tarih cozumlenemedi"


def sutun_bul(basliklar: list[str], adaylar: list[str]) -> str | None:
    """Baslik adi degisebilir ('E-Mail', 'eposta', 'email adres') - esnek eslestirme."""
    for baslik in basliklar:
        sade = re.sub(r"[^a-z]", "", baslik.lower())
        for aday in adaylar:
            if aday in sade:
                return baslik
    return None


def temizle(girdi: Path, cikti: Path, rapor: Path) -> dict:
    with girdi.open(encoding="utf-8-sig", newline="") as f:
        # restkey: baslik sayisindan fazla alani olan satirlar sessizce kaybolmasin
        satirlar = list(csv.DictReader(f, restkey="_fazla_alan"))

    if not satirlar:
        raise SystemExit("Dosya bos veya okunamadi.")

    basliklar = [b for b in satirlar[0].keys() if b != "_fazla_alan"]
    s_isim = sutun_bul(basliklar, ["isim", "ad", "name"])
    s_eposta = sutun_bul(basliklar, ["eposta", "email", "mail"])
    s_telefon = sutun_bul(basliklar, ["telefon", "phone", "gsm", "tel"])
    s_tarih = sutun_bul(basliklar, ["tarih", "date"])

    temiz_satirlar: list[dict] = []
    sorunlu: list[dict] = []
    gorulen_eposta: dict[str, int] = {}
    tekrar = 0

    for sira, satir in enumerate(satirlar, start=2):  # 1 = baslik satiri
        yeni = {k: bosluk_temizle(satir.get(k)) for k in basliklar}
        sorunlar: list[str] = []

        fazla = bosluk_temizle(satir.get("_fazla_alan"))
        if fazla:
            sorunlar.append(f"satirda fazladan alan var: '{fazla}' (kacak virgul olabilir)")

        if s_isim:
            yeni[s_isim] = isim_duzelt(satir.get(s_isim, ""))
        if s_eposta:
            yeni[s_eposta], sorun = eposta_duzelt(satir.get(s_eposta, ""))
            if sorun:
                sorunlar.append(sorun)
        if s_telefon:
            yeni[s_telefon], sorun = telefon_duzelt(satir.get(s_telefon, ""))
            if sorun:
                sorunlar.append(sorun)
        if s_tarih:
            yeni[s_tarih], sorun = tarih_duzelt(satir.get(s_tarih, ""))
            if sorun:
                sorunlar.append(sorun)

        anahtar = yeni.get(s_eposta or "", "")
        if anahtar and anahtar in gorulen_eposta:
            tekrar += 1
            sorunlar.append(f"tekrar kayit (ilk gorulus: satir {gorulen_eposta[anahtar]})")
            sorunlu.append({"satir_no": sira, **yeni, "sorunlar": "; ".join(sorunlar)})
            continue
        if anahtar:
            gorulen_eposta[anahtar] = sira

        if sorunlar:
            sorunlu.append({"satir_no": sira, **yeni, "sorunlar": "; ".join(sorunlar)})
        temiz_satirlar.append(yeni)

    with cikti.open("w", encoding="utf-8-sig", newline="") as f:
        yazici = csv.DictWriter(f, fieldnames=basliklar)
        yazici.writeheader()
        yazici.writerows(temiz_satirlar)

    if sorunlu:
        with rapor.open("w", encoding="utf-8-sig", newline="") as f:
            yazici = csv.DictWriter(f, fieldnames=["satir_no", *basliklar, "sorunlar"])
            yazici.writeheader()
            yazici.writerows(sorunlu)

    return {
        "okunan": len(satirlar),
        "yazilan": len(temiz_satirlar),
        "tekrar": tekrar,
        "sorunlu": len(sorunlu),
    }


def main() -> None:
    ayristirici = argparse.ArgumentParser(description="Dagini kisi listesini temizler.")
    ayristirici.add_argument("girdi", type=Path, help="Kaynak CSV dosyasi")
    ayristirici.add_argument("--cikti", type=Path, help="Temiz CSV (varsayilan: <girdi>_temiz.csv)")
    ayristirici.add_argument("--rapor", type=Path, help="Sorunlu satirlar (varsayilan: <girdi>_sorunlu.csv)")
    args = ayristirici.parse_args()

    if not args.girdi.exists():
        sys.exit(f"Dosya bulunamadi: {args.girdi}")

    cikti = args.cikti or args.girdi.with_name(args.girdi.stem + "_temiz.csv")
    rapor = args.rapor or args.girdi.with_name(args.girdi.stem + "_sorunlu.csv")

    sonuc = temizle(args.girdi, cikti, rapor)

    print(f"Okunan satir      : {sonuc['okunan']}")
    print(f"Temiz dosyaya yazilan: {sonuc['yazilan']}  -> {cikti.name}")
    print(f"Tekrar eden kayit : {sonuc['tekrar']} (cikarildi)")
    print(f"Elle bakilmasi gereken: {sonuc['sorunlu']}" + (f"  -> {rapor.name}" if sonuc["sorunlu"] else ""))


if __name__ == "__main__":
    main()
