# Ürün kalitesi ve erken geri bildirim

Bu referansı ürün/akış/arayüz işi için kullan. Küçük teknik işte bütün ürün fazlarını açma. Mevcut ürün kararları ve görsel dil başlangıçtır; kullanıcı hedefi değişmedikçe şablon uğruna değiştirme.

## İşin biçimi

| İş | En küçük yararlı teslim | Genişlemeyi gerektiren durum |
|---|---|---|
| Küçük hata | Yeniden üretim + ortak kök neden düzeltmesi + ilgili kontrol | Güvenlik, veri kaybı, ortak akış veya platform etkisi |
| Akış özelliği | Etkilenen yolculuk + erken gösterim + gerçek çalışan dilim | Birden çok rol, servis, migration veya yeni ürün kararı |
| Yeni ürün | Amaç/kapsam + risk denemesi + ilk gerçek görev | Temel deneyim kabul edildikten sonra kalan akışlar |
| Benimseme | Kaynak/test/tasarım/yayın haritası + kanıtlanmış başlangıç | Eski planda çelişki; değişiklik gerekçesiyle sınırlı geçiş |
| Tasarım geri bildirimi | Somut fark + etkilenen bileşenler + yeni temsilî çıktı | Yanlış ihtiyaç veya yeni kapsam varsa ilgili ürün kararı |

## Faz bazında kalite

| Faz / uzmanlık | Girdi → çıktı | Ölçüt ve doğrulama | Kullanıcı kararı / geri dönüş |
|---|---|---|---|
| Ürün / ürün sorumlusu | İhtiyaç, mevcut iş → kısa amaç, kullanıcı, akış, kapsam dışı | Gözlenebilir başarı; ana ihtiyaç için örnek görev | Yanlış anlaşılma veya çelişki varsa amacı düzelt |
| Araştırma / alan uzmanı | Kararı değiştiren bilinmeyen → kanıtlı cevap | Tarih/kaynak, uygulanabilirlik, bilinmeyenlerin sınırı | Maliyet/veri/ürün seçimini değiştiren sonuca dön |
| UX / tasarımcı | Ana görev ve durumlar → akış/prototip | Kullanıcı başlangıcı, sonraki adımı ve sonucu anlayıp görevi tamamlayabiliyor; gözlenen sürtünme kaydı | Kullanım mantığını erken göster; akışa dön |
| Görsel / UI tasarımcı | Akış ve mevcut dil → temsilî ekran/bileşen | Gerçek render; tutarlı tipografi, boşluk, hizalama, hiyerarşi; taşma yok | Görsel yönü tüm ekranlara yaymadan göster |
| Mimari / mühendis | Akış, platform, veriler → sahiplik ve sınırlar | En riskli varsayımın dar denemesi; mevcut/native alternatif karşılaştırması | Maliyet, veri veya yetki kapsamı değişiyorsa karar |
| Frontend / uygulayıcı | Ekran ve durum → çalışan etkileşim | Geçerli/geçersiz giriş, klavye/odak, bekleme/hata/boş/başarı, geri/iptal | Ortak bileşen ve kardeş ekranları birlikte düzelt |
| Backend / gerektiğinde uzman | Veri/yetki sözleşmesi → gerçek davranış | İzolasyon, giriş doğrulama, timeout/retry, migration/geri dönüş ve veri kaybı riskine uygun kontroller | Sözleşme değişirse iki tarafı hizala; gerekmiyorsa backend ekleme |
| Entegrasyon / akış sahibi | İstemci + gerçek storage/service → bütün yolculuk | UI eylemi doğru kalıcı sonucu üretir ve okur; ilgili hata/toparlanma da çalışır | İlk çalışan akışı geniş kapsamdan önce göster |
| Doğrulama / bağımsız uzman | Son kaynak/paket → sınırlı kabul | İlgili test, cihaz etkileşimi, görsel, erişilebilirlik, güvenlik kanıtı | Başarısız kriterin aşamasına dön |
| Materyal / içerik-yayın uzmanı | Son ürün + hedef → mağaza metin/görsel | Gerçek özellik, doğru dil, lisans, güncel format ve aday eşleşmesi | Ürün sunumunu göster; eski materyali yeniden üret |
| Yayın / yayın sorumlusu | Aday + tam yetki → uzak sonuç | Hesap/app/channel/version readback; gerçek erişilebilirlik ayrı | Ret/eksik bilgiye dön; belirsiz upload'ı tekrarlama |

Bu tablo zorunlu ayrı belgeler istemez. Kabul ölçütü ilgili görevde bir kez yazılır; test/gözlem oraya referans verir. Araştırma artık kararı değiştirmiyorsa uygulamaya geç. Kritik belirsizlik sürüyorsa sonraki deneyin neyi çözeceğini açıkla; aynı analizi tekrar etme.

## Somut UI ve etkileşim kontrolleri

- Seçilen küçük/geniş viewport, uzun metin/locale ve gerekli yönlerde kesilme, örtüşme veya ulaşılamayan ana eylem olmamalı. Beklenen breakpoint ve hedef cihazlar görevde belirtilir; evrensel cihaz matrisi yok.
- Metin ölçeği büyütüldüğünde görev tamamlanabilmeli. Web hedefinde WCAG 2.2 AA için normal metin kontrastı 4.5:1, büyük metin 3:1 ve %200 büyütme ölçütlerini ilgili istisnalarıyla doğrula; bunlar tek başına erişilebilirlik sertifikası değildir. Native ölçütleri platform rehberiyle seç.
- Tipografi/boşluk/radius/renk mevcut ortak tokenlardan gelsin. İstisna gerekçeli olsun; her ekranda bağımsız stil uydurma. Görsel hiyerarşinin görevi anlaşılır kıldığını ekran üzerinden incele.
- Diyalog: amaç belirgin; alan/validasyon anlaşılır; birincil eylem ve iptal ayırt edilir; dar ekran/klavye içeriği kapatmaz; odak açılış/kapanışta doğru; hatada giriş korunur; bekleyen işlemde tekrar tetikleme ele alınır.
- Boş/yükleniyor/hata/başarı durumları gerçek akışta görülmeli. İzin reddi, geri, tekrar deneme, iptal ve varsa geri alma tutarlı olmalı. Uzman seçenekler temel görevi zorlaştırmadan açılmalı.
- Screenshot incelemesi ve etkileşim kontrolü ayrı kanıttır. Ekran okuyucu, klavye, azaltılmış hareket ve dokunma hedefleri hedef platform/ürüne göre denenir. Kaynak okumak görsel kabul değildir.

Resmi dayanaklar: [WCAG metin ölçeği](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html), [kontrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Sürüm/platforma özgü iddiaları uygulamada tekrar doğrula.

## Geri bildirimi uygulama

Görsel tercih → tasarım token/bileşeni; kullanılabilirlik → etkileşim/metin; akış → geçiş/durum; yanlış ihtiyaç → amaç; teknik hata → ortak kök neden; yeni kapsam → ayrı iş ve maliyet/veri etkisi.

Geri bildirim kaydı kısa tutulur: söylenen somut sorun, değişen karar, etkilenen kaynak/test/materyal ve yeniden gereken kanıt. Ayrı feedback veritabanı yok. Kullanıcının sessizliği onay değildir. Önceden yetkili küçük ayrıntılar için çalışma durdurulmaz; bloke kritik tercihin dışındaki işler devam eder.

## Frontend/backend birlikte kabul

İsimlendirme, veri sahipliği, durum geçişi, validasyon ve hata biçimi ortak olmalı. Örneğin “kaydedildi” arayüzü yalnız gerekli kalıcılık gerçekleşince görünür. Çift tıklama, yanıt kaybı veya retry aynı işi çoğaltmamalı; ürünün ihtiyacına göre idempotency/çatışma davranışı seçilir. Offline/senkronizasyon, log gizliliği, silme/export ve migration yalnız ilgiliyse sözleşmeye girer. Mock servisle geçen demo gerçek servis kabulü olarak sunulmaz.
