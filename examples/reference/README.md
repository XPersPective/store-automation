# Yerel referans ürün

Yalnız sentetik veriyle ürün akışını sınamak için. Üretim uygulaması, kimlik doğrulama veya bulut servisi değildir. Python standart kitaplığı; bağımlılık yok.

Kök klasörden PowerShell:

```powershell
python examples/reference/app.py --port 8765 --db "$env:TEMP/store-automation-reference.db"
```

Tarayıcı: `http://127.0.0.1:8765` (tam bu adres; localhost Host kontrolünden geçmez). Ctrl+C ile durdur. Veriler verilen SQLite dosyasında kalır. Yeni boş deneme için farklı dosya adı ver. Başka kullanıcı uygulamasını kullanmaz.

Akış: boş liste → Yeni not → boş başlık hatası → başlık/açıklama → kaydet → liste → sayfayı yenile. Diyalog Escape/İptal ile kapanır ve odak Yeni not düğmesine döner. Bekleyen kayıtta tekrar gönderim engellenir; kayıp yanıt sonrası aynı içerikle retry aynı kimliği kullanır. Sonuç belirsizken alanlar korunur ve değiştirilmez; Kaydı kontrol et önce requestId ile listeyi geri okur, kayıt yoksa aynı kimlikle dener. Kaydetme hatası metni korur. Yerel sunucuyu durdurup yenileme/yeniden deneme hata akışını kontrol edebilirsin.

`python -m unittest discover -s tests -p test_reference.py -v` gerçek HTTP, SQLite, sunucu yeniden açılışı, idempotency, doğrulama ve Host/Origin sınırlarını sınar. Görsel/klavye/mobil/zoom değerlendirmesi ayrı tarayıcı kanıtı ister. Lokal Host/Origin kontrolü oturum açmış aynı bilgisayar kullanıcısına karşı izolasyon sağlamaz. Bu demo az sayıda not içindir; sayfalama veya çok kullanıcılı işletim içermez.
