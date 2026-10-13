# Hedef mimari ve kararlar

Durum: Kullanıcının istediği bağımsız mimariye göre hazırlanmış geliştirme tasarımı. Runtime uygulanmadı. İlerleme [HANDOFF](../HANDOFF.md), işler [roadmap](roadmap.md), davranış denemeleri [acceptance-scenarios](acceptance-scenarios.md) içindedir.

## 1. Amaç ve tasarım ölçütü

Kullanıcı uygulama fikri veya mevcut projesini verdiğinde ihtiyaç doğru anlaşılmalı; tutarlı, kullanılabilir, platforma uygun ve doğrulanmış ürün teslim edilmelidir. Başarı kod miktarı, ajan sayısı, doldurulan belge veya PASS sayısı değildir.

Değerlendirme eksenleri: ilk yararlı gösterime kadar süre, gerçek kabul süresi, kullanıcı geri bildirimi sonrası yeniden işleme, gerekli koşulların kanıtı, maliyet sınırları ve başka oturumdan güvenli devam. Ölçülmemiş iyileşme yüzdesi vaat edilmez.

Kapsam dışı: genel ajan platformu, yeni dashboard/daemon/veritabanı, bütün sağlayıcıların otomasyonu, otomatik gelir/sıralama garantisi, izin verilmemiş backend/üretim kurulumu, bütün uygulamaları tek şablona taşıma.

## 2. Alternatifler ve seçim

| Alternatif | Kazanç | Sorun | Karar |
|---|---|---|---|
| Eski skill'e daha çok talimat ekle | Küçük metin değişikliği | Codex/OpenCode kabul uyumsuzluğu, rapor doğrulaması ve geç ürün geri bildirimi sürer | Tek başına yeterli değil |
| Baştan genel orkestrasyon platformu yaz | Tek kontrol düzlemi hayali | Host yeteneklerini tekrarlar; adapter, güvenlik ve bakım maliyetini büyütür | Reddedildi |
| İnce ürün teslim protokolü + mevcut host + küçük ortak kabul sınırı | Gerçek ürün akışına odaklanır; mevcut araçları kullanır | Host kanıtlarının eşdeğerliği kendiliğinden oluşmaz | Seçildi; desteklenmeyen köken açık kalacak |

## 3. Yapı

```text
Kullanıcı amacı + mevcut kaynak/kararlar
              |
Ürün sorumlusu / entegrasyon sahibi
  |           |             |
UX denemesi   Teknik risk   Mevcut akışı yeniden üretme
  +-----------+-------------+
              |
Bir çalışan kullanıcı yolculuğu + erken gösterim
              |
Kriter bazında gözlem / makine kontrolü / bağımsız inceleme
              |
Kapsamı genişletme veya hedef platform yayın hazırlığı
              |
Yetkili işlem -> uzak geri okuma -> ayrı erişilebilirlik doğrulaması
```

Geri bildirim ve başarısızlık yalnız ilgili akış/karara geri döner. Bütün projeyi sıfırlayan aşama makinesi kurulmaz. Süreç sırasını en büyük belirsizlik belirler; UI-first/backend-first evrensel kural değildir.

## 4. Sorumluluklar ve uzmanlar

- **Ürün sorumlusu:** ihtiyacı, kapsamı, önceliği, kabulü ve uzmanlar arası sözleşmeyi yönetir. Bütün uzman işini yeniden yapmaz; kritik bulguyu yeniden üretir ve entegrasyon kanıtını kontrol eder.
- **Uygulayıcı:** küçük uçtan uca dilimin sonuç sahibidir. FE/BE ayrı uzmanlar gerekirse ortak veri/durum/hata sözleşmesine bağlı çalışır.
- **Bağımsız inceleyen:** uygulama oturumundan ayrı olarak ilgili çıktıyı ve gerekli ölçütleri inceler. Host ve kaynak kökeni, araç yetkisi ve bağımsızlık kanıtı ayrıca değerlendirilir.
- **İhtiyaca göre uzmanlık:** ürün/UX, görsel tasarım, platform, frontend, backend, erişilebilirlik, güvenlik, yerelleştirme ve yayın. Bunlar her işte açılacak kadro değildir.

Mekanik düzeltmede mevcut ajan ve deterministik kontrol yeterli olabilir. Önemli davranış, güvenlik/veri, mimari veya yayın riski bağımsız inceleme ister. Küçük diff bu şartı düşürmez.

## 5. Kalıcı bilgi: tek bilgi, tek sahip

Yeni bir plan veritabanı kurulmaz. Seçilen uygulamanın mevcut plan/Brain/docs düzeni korunur. Hafıza şunları taşımalıdır: kullanıcı amacı, kabul edilmiş kararlar, açık işler, kanıt referansları, kalan risk ve sonraki güvenli adım.

Brain varsa bu bilgiyi almak için kullanılır; belirli PB kimliği veya durum metni runtime çalışmasının önkoşulu olmaz. Brain yoksa var olan proje belgeleri kullanılabilir. Uzun işte gerekli kısa devam kaydı oluşturulur; bütün projeyi yeniden kaydetmek zorunlu değildir.

Görev brief'i kullanıcı gereksiniminin tek kaynağıdır. Ajan başlatılırken brief, ilgili kabul ve izin referanslarının **çözülmüş, değişmez kopyası** deneme kaydına bağlanır. Çalışma sırasında kaynak brief değişirse geçmiş yetki geriye dönük değiştirilmez.

## 6. Küçük ortak yürütme/kabul sınırı

İlk uygulama tek stdlib modülü `runtime/acceptance.py` ve bir test dosyası ile başlar. CLI, adapter sınıf hiyerarşisi veya şema framework'ü N01 için gerekmez. Aşağıdaki kayıtlar kavramsal sözleşmedir; JSON alanları N01'de aynı anlamla kesinleştirilir.

| Kayıt | Zorunlu anlam | Üreten |
|---|---|---|
| Görev | Kimlik, proje, amaç, sınırlı kaynak kapsamı, kapsam dışı, risk, kabul ölçütleri ve izinler | Sorumlu ajan; mevcut planı referans alır |
| Deneme | Görev snapshot hash'i, atanan rol, gerçek host/route, native kimlik varsa kimlik, istenen/uygulanan izin, kaynak referansları, başlangıç/bitiş/durum | Host araç sonucu ve sorumlu ajan; worker kendi kökenini doğrulayamaz |
| Gözlem | Ölçüt kimliği, kaynak/paket kimliği, yöntem/ortam, sonuç, gerçek çıktı referansı/hash'i, zaman ve gözlem sahibi | Test/cihaz/host aracı veya açıkça insan gözlemi |
| İnceleme | Hangi deneme/kaynak/kriter incelendiği, bağımsızlık kökeni, bulgular ve dispositions | Ayrı inceleme oturumu; köken host tarafından ilişkilendirilir |
| Kabul | Hangi kriterlerin hangi güncel kanıtla sağlandığı, açık eksikler ve kapsamı sınırlı karar | Sorumlu ajan + deterministik doğrulama |

İlk durum kümeleri: deneme `PREPARED/RUNNING/COMPLETED/BLOCKED/FAILED/INTERRUPTED/UNVERIFIED`; kriter sonucu `PASS/FAIL/UNVERIFIED/NOT_APPLICABLE`. N/A gerekçe ister ve zorunlu kriteri atlama yetkisi vermez. Kabul sonucu `ACCEPTED/BLOCKED/UNVERIFIED`, **kapsamıyla birlikte** döner; evrensel ürün PASS'i yoktur.

N01 doğrulaması: bilinmeyen durumlar, boş kimlikler, task/project/rol/route uyuşmazlığı, bool yerine sayı karışması, eksik kanıt ve eski ilgili kaynak reddedilir. Serbest worker metni başarı yetkisi değildir. `COMPLETED` yalnız iş raporunun terminal durumudur; ürün kabulü değildir.

Hash bütünlük sağlar, doğruluk veya güvenilir üretici sağlamaz. Aynı yazıcının ürettiği üç JSON dosyası üç bağımsız kanıt sayılmaz. Yerel dosyalar kötü niyetli aynı-OS-kullanıcıya karşı güvenlik sınırı değildir. Host kökeni yoksa otomatik doğrulanmış köken iddiası yapılmaz; kanıtın seviyesi düşer veya gerekli kapı açık kalır.

## 7. Kaynak ve kanıt geçerliliği

Kanıt, gerçekten baktığı kaynak, gereksinim, bağımlılık ve paket girdilerini kapsar. Görsel için ekran/locale/device/capture bilgisi; API için çalışan servis ve yapılandırma; paket için artifact hash ve iç kimlik gerekir.

Atama başlangıcının input snapshot'ı değişmez geçmiş kaydıdır; izinli implementation çıktısı ayrı final-output snapshot'ıdır. Test ve review final-output'a bağlanır. Read-only incelemede input değişimi veya final-output gözleminden sonraki değişim kanıtı eskiltir; izinli edit tek başına teslimi geçersiz yapmaz.

İlk sürümde dependency graph icat etme. Açık girdi listesi + muhafazakâr ilgili proje fingerprint'i yeterli; sınırı belgeleyerek kullan. Sonradan hız optimizasyonu gerçek ölçüm gerektirir. Gizli dosyaları fingerprint uğruna okuma; public kaynak manifesti içinde private/linked/kaçan yol varsa açık hata ver.

Gereksinim/kaynak/paket değişince etkilenen kanıt UNVERIFIED olur. Sadece dosya timestamp'ine güvenme. Prototip onayı uygulama davranışını; kaynak incelemesi cihaz görselliğini; APK kontrolü AAB/IPA'yı kanıtlamaz.

Küçük bulgular `fixed/accepted/deferred` gerekçesi ve karar sahibiyle saklanabilir. Zorunlu kabul ihlali etiketle küçültülemez. Kullanıcı kararını gerektiren ödünleşme, ajan tarafından kullanıcı kabulü gibi kaydedilemez.

## 8. Host, model, kota ve paralellik

Önce mevcut host'un görev için gerçekten sunduğu başlat/izle/sonuç/durdur yeteneklerine bak. Başka CLI ancak eksik yetenek için eklenir. Model envanteri veya login, o modelin görevi/yazma yetkisini kanıtlamaz. Statik model adı kalite benchmark'ı değildir.

Bilinen yeterli route ile başla; yeterlilik başarısız kabul ve gerçek görev çıktılarıyla değerlendirilir. Ayrı bir sürekli benchmark platformu kurma. Mevcut kota aracını kullan; yeni iş için bilinmeyen veya koruma eşiğinin altındaki kota halinde aynı paylaşılan hesapta yeni ajan başlatma. Başka aboneliğin kota verisini bu route'a aktarma. Eksik model/efor/kullanım alanları null + açıklama olarak kalır.

Tek ortak checkout'a eşzamanlı yazıcı yok. Salt okunur işler paralel olabilir. Yazma paralelliği yalnız izole worktree/alan, açık dosya sahipliği, ortak sözleşme ve entegrasyon kontrolü olduğunda açılır. İki işin API/veri değişiklikleri çakışıyorsa dosyaları ayrı olsa bile bağımsız sayılmaz. Mevcut global bucket kilidini ilk günden yeni scheduler ile değiştirme; host'un gerçek eşzamanlılık ve kota kanıtına göre N03'te değerlendir.

## 9. Kesinti ve tekrar

Devam noktası: actual diff + sahiplik + son geçerli gereksinim + denemeler + geçerli kanıt + bekleyen dış etki + sonraki güvenli adım. Process ID tek başına sahiplik değildir; yeniden kullanılan PID ve erişim reddi dikkate alınır. Eski ajan durmadan aynı işi yeni yazıcıya verme.

“Upload çağrıldı, yanıt kayıp” ile “upload başlamadı” ayrılır. Dış işlem tekrarından önce remote readback yapılır. Yerel değişiklikte gerçek diff korunur; kör replay yok. Bilinmeyen kullanıcı dosyasını geri alma/temizleme yok.

## 10. Yayın ve bakım

AppPublishing/Fastlane korunur. Platform özel paket/metadata/cihaz kanıtı ortak kabul sınırına referans olur; yeni universal uploader yapılmaz. Android, iOS, Windows ve web hedefleri ayrı; desteklenmeyen hedef açık kalır.

Ürün konumlandırma, ikon, gerçek screenshot, lokalizasyon, açıklamalar, sürüm notları, gizlilik ve destek bilgisi aynı son adayı anlatmalıdır. Güncel mağaza şartları resmi kaynaktan ve hedef sürüm için yeniden kontrol edilir. Web SEO ile ASO aynı kontrol listesi değildir. Yayın sonrası bakım, gerçek sorun ve seçilmiş periyodik izleme talebinden doğar; otomatik bütün repo taraması yok.

## 11. Koruma, kaldırma, geçiş

**Koru:** çalıştığı gösterilmiş süreç containment/ownership yardımcıları, private path sınırları, exclusive kanıt yazımı, kaynak hash kontrolleri, güvenli kurulum mantığı, mevcut uygulama testleri, napp ve Fastlane entegrasyonları. Kod yalnız caller ve bağımlılık incelemesinden sonra seçilerek alınır.

**Değiştir:** sağlayıcıya bağlı kabul, tekrarlanan kontrat alanları, global PASS, sabit factory/Flutter/Android kontrol profili, geç kullanıcı gösterimi, sıfır-bulgu zorunluluğu ve Brain'e bağlı execution kimliği.

**Kaldırılacak zorunluluk:** her küçük işten önce tam katalog/ekip/kontrat merasimi. Eski runtime'ın faydalı yeteneklerini kanıtsız silmek veya ince katmanın arkasında aynı zorunlu yolları tutmak kabul edilmez.

Geçiş önce aday klasörde tek akış ve küçük iş ile kanıtlanır. Sonra standalone paket/geri dönüş testi; en son eski giriş noktasının değiştirilmesi. Kullanıcının “üsttekileri silip bunu koyacağız” hedefi korunur: tam silme kapsamı N08 manifestinden çıkar, bilinmeyen dosyalar silinmez, geri alınabilir arşiv ve doğrulama olmadan geçilmez. Son kullanıcı mesajı final replacement, tüm yerel ajanlara dağıtım ve mevcut GitHub deposuna gönderimi açıkça yetkilendirdi. N08 bunları içerir. Uygulama üretim mağaza yayını bu yetkiye dahil değildir.
