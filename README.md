# Portfolyo

Freelance başvurularında kullanmak üzere tek sayfalık portfolyo sitesi ve çalışan kod örnekleri.

```
index.html                    portfolyo sayfası (GitHub Pages'e hazır)
ornekler/
  csv_temizleyici.py          dağınık kişi listesini temizler
  fiyat_takip.py              ürün fiyatlarını takip eder (web scraping)
  ornek_liste.csv             temizleyiciyi denemek için kasten bozuk örnek veri
```

---

## 1. Kişisel bilgiler

Sayfadaki iletişim bilgileri dolduruldu:

| Alan | Değer |
|---|---|
| Ad | Sezer Kıraş |
| E-posta | sezerkiras28@gmail.com |
| GitHub | SystSezer |
| WhatsApp | +90 542 179 15 42 |

**Kontrol edilmesi gerekenler:**

- **Diller** bölümünde Almanca/İspanyolca/İtalyanca/Çince/Japonca "temel seviye" yazıyor.
  Birinde gerçekten ileriysen düzelt; hiç bilmediğin varsa sil.
- **Fiyatlar** başlangıç seviyesi (5–8 $/saat). İlk 5-10 işten sonra yükselt.

## 2. Yayınlama (GitHub Pages — ücretsiz)

Önce <https://github.com> üzerinden hesap aç ve `portfolyo` adında **public** bir depo oluştur.
Sonra bu klasörde:

```bash
cd C:\Users\ogune\PycharmProjects\portfolyo; git init; git add .; git commit -m "portfolyo"; git branch -M main; git remote add origin https://github.com/SystSezer/portfolyo.git; git push -u origin main
```

Ardından depo sayfasında **Settings → Pages → Source: `main` / `root` → Save**.

Birkaç dakika içinde sayfan şu adreste yayında olur:

```
https://SystSezer.github.io/portfolyo/
```

Bu adresi FreelanceRadar'daki **Profil → Portfolyo linkleri** alanına yapıştır — teklif
metinlerine otomatik olarak eklenir.

---

## 3. Örnekleri çalıştırma

FreelanceRadar'ın sanal ortamını kullanabilirsin:

```bash
cd C:\Users\ogune\PycharmProjects\portfolyo\ornekler; ..\..\FreelanceRadar\.venv\Scripts\python.exe csv_temizleyici.py ornek_liste.csv
```

```bash
cd C:\Users\ogune\PycharmProjects\portfolyo\ornekler; ..\..\FreelanceRadar\.venv\Scripts\python.exe fiyat_takip.py
```

---

## 4. Önemli: kodu anla, sonra göster

Bu örnekleri portfolyona koyuyorsun — müşteri "burada ne yapıyorsun?" diye sorabilir.
Her iki dosyanın da yorum satırları Türkçe ve açıklayıcı; **göstermeden önce bir kez
baştan sona oku.** Anlatamayacağın bir şeyi portfolyoya koyma.

En hızlı öğrenme yolu: `ornek_liste.csv`'yi kendin boz (yeni bir bozuk satır ekle),
temizleyiciyi çalıştır, ne yakaladığına bak. `fiyat_takip.py`'yi de kendi takip etmek
istediğin bir ürün sayfasına yönlendirip dene:

```bash
..\..\FreelanceRadar\.venv\Scripts\python.exe fiyat_takip.py --url "https://site.com/urun" --secici "h1" --fiyat-secici ".fiyat"
```

Seçicileri bulmak için: tarayıcıda sayfayı aç → fiyata sağ tıkla → **İncele** → seçili
elemanın `class` değerini kullan.
