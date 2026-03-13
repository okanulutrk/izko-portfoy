"""
İZKO Portföy Hesaplayıcı
========================
Kurulum:
    pip install playwright
    playwright install chromium

Çalıştırma:
    python izko_portfoy.py
"""

import asyncio
from datetime import datetime
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────
# 💼  PORTFÖYÜNÜZ
# Yeni/Eski ayrımı olan ürünler: (yeni_adet, eski_adet)
# Tek fiyatlı ürünlerde eski_adet=0 bırakın.
# Dolar/Euro için adet = kaç birim döviziniz var.
# ──────────────────────────────────────────────
PORTFOY = {
    "22 Ayar":    (6,  0),
    "18 Ayar":    (0,  0),
    "14 Ayar":    (0,  0),
    "Gram Altın": (0,  0),
    "Ata Altın":  (3,  0),
    "Çeyrek":     (0,  6),
    "Yarım":      (0,  0),
    "Ziynet":     (0,  0),
    "Paketli Has":(2,  0),
    "Has Altın":  (0,  0),
    "Dolar":      (0,  0),
    "Euro":       (0,  0),
}

# ──────────────────────────────────────────────
# 🌐  VERİ ÇEKME
# ──────────────────────────────────────────────
async def kur_cek() -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("  → izko.org.tr bağlanılıyor...")
        await page.goto("https://www.izko.org.tr/guncel-kur", timeout=30000)

        print("  → Veriler yükleniyor...")
        try:
            await page.wait_for_function(
                "document.querySelectorAll('table td')[1]?.innerText.trim() !== '-'",
                timeout=15000
            )
        except Exception:
            pass

        veriler = await page.evaluate("""() => {
            const t1 = {};   // tek fiyatlı: { isim: fiyat }
            const t2 = {};   // yeni/eski:   { isim: {yeni, eski} }

            const TEK  = ['22 Ayar','18 Ayar','14 Ayar','Gram Altın','Ata Altın'];
            const YENI_ESKI = ['Çeyrek','Yarım','Ziynet'];

            const rows = document.querySelectorAll('table')[0]?.querySelectorAll('tr') || [];
            rows.forEach(tr => {
                const cells = Array.from(tr.querySelectorAll('td, th'))
                                   .map(c => c.innerText.trim());

                // Tek fiyatlı (<td> satırları)
                if (cells.length >= 2 && TEK.includes(cells[0])) {
                    t1[cells[0]] = cells[1];
                }
                // Yeni/Eski (<th> satırları, 3 hücre)
                if (cells.length >= 3 && YENI_ESKI.includes(cells[0])) {
                    t2[cells[0]] = { yeni: cells[1], eski: cells[2] };
                }
                // Paketli Has / Has Altın — Satir 10: 4 hücreli th satırı
                // "Paketli Has:" | fiyat | "Has Altın:" | fiyat
                if (cells.length >= 4 && cells[0].includes('Paketli')) {
                    t1['Paketli Has'] = cells[1];
                    t1['Has Altın']   = cells[3];
                }
            });

            // Dolar / Euro — tablo dışı SPAN elementleri
            const spanlar = Array.from(document.querySelectorAll('span'));
            for (let i = 0; i < spanlar.length; i++) {
                const txt = spanlar[i].innerText.trim();
                if (txt === 'Dolar:' && spanlar[i+1]) t1['Dolar'] = spanlar[i+1].innerText.trim();
                if (txt === 'Euro:'  && spanlar[i+1]) t1['Euro']  = spanlar[i+1].innerText.trim();
            }

            return { t1, t2 };
        }""")

        await browser.close()

    return {
        "t1":    veriler["t1"],
        "t2":    veriler["t2"],
        "zaman": datetime.now().strftime("%d.%m.%Y %H:%M")
    }

# ──────────────────────────────────────────────
# 🧮  HESAPLAMA
# ──────────────────────────────────────────────
def parse(metin: str) -> float:
    try:
        return float(metin.replace(".", "").replace(",", ".").strip())
    except Exception:
        return 0.0

def fmt(sayi: float) -> str:
    return f"{sayi:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def hesapla(kurlar: dict) -> list:
    satirlar = []
    t1, t2 = kurlar["t1"], kurlar["t2"]

    for urun, (yeni_adet, eski_adet) in PORTFOY.items():
        if yeni_adet == 0 and eski_adet == 0:
            continue

        if urun in t2:
            yf = parse(t2[urun]["yeni"])
            ef = parse(t2[urun]["eski"])
            satirlar.append({
                "urun": urun,
                "yeni_adet": yeni_adet, "yeni_fiyat": yf,
                "eski_adet": eski_adet,  "eski_fiyat": ef,
                "toplam": yf * yeni_adet + ef * eski_adet,
            })
        elif urun in t1:
            fiyat = parse(t1[urun])
            satirlar.append({
                "urun": urun,
                "yeni_adet": yeni_adet, "yeni_fiyat": fiyat,
                "eski_adet": 0,          "eski_fiyat": 0.0,
                "toplam": fiyat * yeni_adet,
            })
        else:
            print(f"  ⚠️  '{urun}' sitede bulunamadı.")

    return satirlar

# ──────────────────────────────────────────────
# 🖨️  TERMİNAL RAPORU
# ──────────────────────────────────────────────
def rapor_yazdir(kurlar: dict, satirlar: list):
    t1, t2 = kurlar["t1"], kurlar["t2"]
    zaman  = kurlar["zaman"]
    W = 72

    def cizgi(c="─"): print(c * W)
    def baslik(m):
        print(); cizgi(); print(f"  {m}"); cizgi()

    # ── Başlık ──
    print()
    cizgi("═")
    print(f"{'📊  İZKO ALTIN PORTFÖY RAPORU':^{W}}")
    print(f"{'İzmir Kuyumcular Odası — Tavsiye Fiyatları':^{W}}")
    print(f"{zaman:^{W}}")
    cizgi("═")

    # ── Referans Kurlar ──
    baslik("📌  REFERANS KURLAR")
    for k in ["Has Altın", "Paketli Has", "Dolar", "Euro"]:
        v = t1.get(k, "-")
        print(f"  {k:<20} {v:>12} ₺")

    # ── Güncel Fiyatlar ──
    baslik("💰  GÜNCEL FİYATLAR (SATIŞ)")
    for k in ["22 Ayar","18 Ayar","14 Ayar","Gram Altın","Ata Altın"]:
        v = t1.get(k, "-")
        print(f"  {k:<20} {v:>12} ₺")

    print()
    print(f"  {'Ürün':<20} {'YENİ':>14} {'ESKİ':>14}")
    cizgi()
    for isim, fiyatlar in t2.items():
        y = fiyatlar["yeni"] or "-"
        e = fiyatlar["eski"] or "-"
        print(f"  {isim:<20} {y+' ₺':>14} {e+' ₺':>14}")

    # ── Portföy Detayı ──
    baslik("💼  PORTFÖY DETAYI")
    print(f"  {'Ürün':<16} {'Adet':<18} {'Birim Fiyat':<22} {'Toplam':>12}")
    cizgi()

    for s in satirlar:
        if s["eski_adet"] > 0 and s["yeni_adet"] > 0:
            adet_str  = f"{s['yeni_adet']}Y + {s['eski_adet']}E"
            fiyat_str = f"{fmt(s['yeni_fiyat'])} / {fmt(s['eski_fiyat'])} ₺"
        elif s["eski_adet"] > 0:
            adet_str  = f"{s['eski_adet']} (eski)"
            fiyat_str = f"{fmt(s['eski_fiyat'])} ₺"
        else:
            adet_str  = str(s["yeni_adet"])
            fiyat_str = f"{fmt(s['yeni_fiyat'])} ₺"

        print(f"  {s['urun']:<16} {adet_str:<18} {fiyat_str:<22} {fmt(s['toplam']):>12} ₺")

    # ── Genel Toplam ──
    genel = sum(s["toplam"] for s in satirlar)
    cizgi("═")
    print(f"  {'GENEL TOPLAM':<54} {fmt(genel):>12} ₺")
    cizgi("═")
    print()

# ──────────────────────────────────────────────
# 🚀  ÇALIŞTIR
# ──────────────────────────────────────────────
async def main():
    print("\n🔍 Veriler çekiliyor...")
    try:
        kurlar   = await kur_cek()
        satirlar = hesapla(kurlar)
        rapor_yazdir(kurlar, satirlar)
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")

if __name__ == "__main__":
    asyncio.run(main())