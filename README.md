# Poelsan Katalog Ayırıcı

PDF ürün kataloglarını, **İçindekiler / Table of Contents** bölümündeki kategori ve sayfa numaralarına göre otomatik olarak ayrı PDF dosyalarına bölen bir Python komut satırı aracıdır.

Araç; Türkçe ve İngilizce içindekiler başlıklarını algılar, noktalı satır biçimindeki listeleri ayrıştırır, gerekirse görsel yerleşime göre tablo benzeri içindekiler sayfalarını çözümlemeyi dener ve basılı sayfa numaraları ile PDF içindeki fiziksel sayfalar arasındaki farkı hesaplar. İsteğe bağlı olarak kapak ve içindekiler gibi ortak ön sayfalar her çıktı dosyasına eklenebilir.

## Özellikler

- PDF içindeki metni sayfa bazında çıkarma
- `İÇİNDEKİLER`, `CONTENTS`, `INDEX` ve benzeri başlıkları erken sayfalarda otomatik bulma
- Noktalı, çizgili veya boşlukla ayrılmış kategori–sayfa satırlarını ayrıştırma
- PyMuPDF kuruluysa görsel/grid düzenindeki içindekiler için konumsal ayrıştırma denemesi
- Basılı sayfa numarasını fiziksel PDF indeksine dönüştürmek için otomatik ofset hesaplama
- Gerekirse `--offset` ile manuel ofset belirleme
- Her kategori için güvenli, sıralı dosya adları oluşturma
- Kapak, tanıtım ve içindekiler sayfalarını her kategori PDF’ine ekleme seçeneği
- Birim ve uçtan uca testler

## Gereksinimler

- Python 3.9 veya üzeri
- Zorunlu paket: [`pypdf`](https://pypdf.readthedocs.io/)
- İsteğe bağlı paket: [`PyMuPDF`](https://pymupdf.readthedocs.io/) (`fitz` modülü) — görsel/grid düzenindeki içindekiler için

Kurulum için önerilen akış:

```bash
cd /Users/nisacol/poelsan-katalog
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pypdf PyMuPDF
```

> `PyMuPDF` kurulmadığında uygulama çalışmaya devam eder; yalnızca görsel yerleşim tabanlı içindekiler ayrıştırması devre dışı kalır.

## Hızlı Başlangıç

Depodaki ana katalogla çalıştırma örneği:

```bash
cd /Users/nisacol/poelsan-katalog
python3 src/main.py \
  --input data/poelsan_katalog.pdf \
  --output output
```

Komut tamamlandığında `output/` klasöründe aşağıdakine benzer dosyalar oluşturulur:

```text
01. CUP BT PİLLİ SULAMA KONTROL ÜNİTESİ.pdf
02. SOLENOİD VANA.pdf
03. SPREYLER.pdf
...
```

Her çıktı dosyası, içindekilerde ilgili kategoriye ait başlangıç sayfasından sonraki kategorinin başlangıç sayfasından bir önceki sayfaya kadar olan aralığı kapsar. Son kategori, kaynak PDF’in sonuna kadar devam eder.

## Komut Satırı Kullanımı

```bash
python3 src/main.py --input KAYNAK.pdf [seçenekler]
```

| Seçenek | Açıklama |
| --- | --- |
| `-i`, `--input` | Bölünecek PDF dosyasının yolu. Zorunludur. |
| `-o`, `--output` | Çıktı PDF’lerinin yazılacağı klasör. Varsayılan: `./output` |
| `--offset` | Basılı sayfa ile fiziksel PDF indeksi arasındaki manuel fark. Otomatik tespiti geçersiz kılar. |
| `--include-prefix` | Kapak, kurumsal/tanıtım ve içindekiler gibi ilk kategori öncesindeki sayfaları her çıktıya ekler. |
| `-v`, `--verbose` | Tanılama için ayrıntılı (`DEBUG`) günlük kaydını etkinleştirir. |

### Ortak ön sayfaları dahil etme

Her kategori PDF’inin kapak ve içindekilerle başlaması istenirse:

```bash
python3 src/main.py \
  --input data/poelsan_katalog.pdf \
  --output output-with-prefix \
  --include-prefix
```

### Manuel ofset kullanma

Otomatik sayfa eşlemesi katalog yapısına uymuyorsa, `--offset` ile kontrol sağlayabilirsiniz:

```bash
python3 src/main.py \
  --input data/poelsan_katalog.pdf \
  --output output \
  --offset -3 \
  --verbose
```

Ofset dönüşümünün temel mantığı şudur:

```text
fiziksel PDF indeksi = içindekilerdeki basılı sayfa + offset
```

PDF indeksleri sıfırdan başlar. Mevcut uygulama akışında hesaplanan veya `--offset` ile verilen değere ayrıca `2` eklenir; bu nedenle manuel değer girerken ayrıntılı günlükte bildirilen **Final Page Offset** değerini esas alın. Ayrıntılı günlük çıktısı, algılanan içindekiler sayfalarını, bulunan kategorileri ve kullanılan son ofset değerini gösterir.

## Nasıl Çalışır?

```text
Kaynak PDF
    │
    ├─ 1. Her sayfanın metnini çıkar
    ├─ 2. İçindekiler sayfalarını tespit et
    ├─ 3. Kategori adı + basılı başlangıç sayfasını ayrıştır
    ├─ 4. Basılı/fiziksel sayfa ofsetini hesapla
    ├─ 5. Her kategori için sayfa aralığını belirle
    └─ 6. Ayrı PDF dosyalarını yaz
```

Ofset hesaplanırken sırasıyla şu yaklaşımlar denenir:

1. İlk kategori adını içindekilerden sonraki fiziksel PDF sayfalarında aramak.
2. İlk kategorinin basılı sayfa numarasını (`Sayfa 12`, `Page 12` vb.) aramak.
3. PDF’nin sayfa etiketi metadatasını kullanmak.
4. İçindekiler sayfasının konumuna dayalı bir geri dönüş kestirimi kullanmak.

## Proje Yapısı

```text
poelsan-katalog/
├── data/
│   ├── poelsan_katalog.pdf       # Örnek/ana kaynak katalog
│   └── sample_catalog.pdf        # Test için örnek katalog
├── output/                       # Oluşturulmuş kategori PDF’leri
├── src/
│   ├── main.py                   # CLI giriş noktası
│   ├── splitter.py               # Uçtan uca ayırma akışı
│   ├── toc_parser.py             # İçindekiler tespiti ve ayrıştırması
│   ├── offset_calculator.py      # Sayfa ofseti hesabı
│   ├── pdf_processor.py          # PDF okuma, metin çıkarma ve yazma
│   ├── utils.py                  # Metin/dosya adı/log yardımcıları
│   └── config.py                 # Anahtar sözcükler, regex’ler, varsayılanlar
└── tests/
    ├── create_sample_catalog.py  # Sentetik katalog üretimi
    └── test_splitter.py          # Birim ve entegrasyon testleri
```

`database.py` ve `model_helper.py` şu an uygulama akışında kullanılmayan yer tutucu modüllerdir.

## Testler

Tüm testleri proje kökünden çalıştırın:

```bash
cd /Users/nisacol/poelsan-katalog
python3 -m unittest discover -s tests -v
```

Testler; dosya adı temizleme, Türkçe metin normalizasyonu, içindekiler tespiti/ayrıştırması, ofset hesabı ve sentetik bir PDF üzerinde kategori bazlı bölme akışını kapsar.

Yalnızca test kataloğunu yeniden oluşturmak için:

```bash
python3 tests/create_sample_catalog.py
```

## Sorun Giderme

### “Could not extract any valid category entries” hatası

- PDF’nin metin katmanı olup olmadığını kontrol edin. Taranmış/görüntü tabanlı PDF’lerde OCR olmadan metin çıkarılamaz.
- İçindekiler sayfasının ilk 25 fiziksel sayfa içinde olduğundan emin olun. Bu tarama sınırı `src/config.py` içindeki `MAX_TOC_SEARCH_PAGES` ile değiştirilir.
- İçindekiler biçimi farklıysa `src/config.py` içindeki `TOC_LINE_PATTERNS` desenlerini katalog yapınıza göre genişletin.
- Görsel sütun veya grid düzenindeki içindekiler için `PyMuPDF` paketinin kurulu olduğundan emin olun.

### Kategoriler yanlış sayfalardan başlıyor

- Önce `--verbose` ile çalıştırıp hesaplanan ofseti inceleyin.
- Ardından uygun değeri `--offset` ile vererek sonucu doğrulayın.
- Basılı sayfa numarası ile PDF görüntüleyicideki sayfa numarasının farklı kavramlar olduğunu unutmayın; araç fiziksel indeksleri kullanır.

### Dosya adı sorunları

Kategori adlarındaki işletim sistemi için geçersiz karakterler otomatik kaldırılır. Aynı ada sahip birden fazla kategori oluşursa dosya adına sayısal ek getirilir.

## Geliştirme Notları

- Yeni içindekiler anahtar sözcükleri `src/config.py` içindeki `TOC_KEYWORDS` listesine eklenebilir.
- Yeni satır biçimleri için `TOC_LINE_PATTERNS` içine adlandırılmış `title` ve `page` grupları olan bir regex eklenmelidir.
- Çıktı bilgileri `CatalogSplitter.process()` çağrısından `CategoryPDFInfo` nesneleri olarak da alınabilir; bu, aracı başka bir Python uygulamasına entegre etmeyi kolaylaştırır.

## Lisans

Bu depoda henüz bir lisans dosyası bulunmamaktadır. Dağıtım veya üçüncü taraf kullanımından önce uygun lisansın eklenmesi önerilir.
