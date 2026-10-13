# Kabul senaryoları — plan, henüz yürütülmüş sonuç değil

Bu dosya beklenen davranıştır. Gerçek sonuçlar HANDOFF'a, son toplu değerlendirme N07 validation-report'una referansla yazılır. A = güncel gerçek araç/ürün yürütmesi; B = yerel/sentetik kontrol; C = yalnız tasarım/talimat; D = dış ortam/erişim yüzünden doğrulanmamış. Bir senaryoda birden fazla seviye olabilir; tek toplu PASS ile sınır gizlenmez.

## S01 — Küçük iş büyümüyor
Girdi: davranışı değiştirmeyen tek metin/hizalama düzeltmesi; mevcut proje ve kontrol hazır. Beklenen: ilgili inceleme/düzeltme/kontrol; PB init, katalog taraması, mimari anket veya zorunlu ajan zinciri yok. Karşı örnek: iki satırlık hesap izolasyonu hatası küçük mekanik iş sayılmıyor. Kanıt: gerçek çağrı listesi ve süre. Bu iki örneği aynı risk sınıfına sokan sistem başarısız.

## S02 — Geçersiz rapor başarıya yükselmiyor
Girdi: başarılı transport; state BANANA, boş state, yanlış rol/model/task/project ve COMPLETED+blocker varyantları. Beklenen: geçersiz alanlar reddedilir, çelişkili sonuç kabul edilmez. Doğru eşleşmiş COMPLETED yalnız tamamlanmış denemedir, ürün kabulü değil. B: N01 birim kontrolü; A: N02 gerçek worker raporu.

## S03 — İnceleme gerçek göreve ait ve bağımsız
Girdi: doğru içerikli fakat yanlış project/attempt native export; kendi uygulama oturumu; doğrulanamayan host kökeni. Beklenen: otomatik kabul yok. Geçerli ayrı reviewer'ın gerçek atama/sonuç ilişkisi host kimlik şekline bağımlı olmadan doğrulanır. Host gerekli bağı kuramıyorsa eksik kanıt açık kalır. Sadece UUID veya ses_ prefix olumlu/olumsuz yeterlilik değildir.

## S04 — Eski veya yanlış kanıt reddediliyor
Girdi: worker'a verilen kaynak daha sonra değişir; test sonrası source/contract/artifact değiştirilir; başka sürüm görüntüsü eklenir. Beklenen: ilgili kabul UNVERIFIED/BLOCKED; eski hash'i raporda tekrar etmek yetmez. Pozitif durum: izinli implementation edit → ayrı final-output → bu output üzerinde fresh test/review kabul edilebilir. Negatif durumda read-only gözlem sırasında veya kabul kanıtından sonra source değişir. Güvenli küçük test source'u çalışırken değiştirir; gerçek ajan kanıtı ayrıca kaynak snapshot'ıyla kontrol edilir. Secret/linked path fingerprint'e sokulunca içerik okunmadan reddedilir.

## S05 — Kusur kaybolmadan riskle kabul
Girdi: tüm gerekli kriterler sağlanmış; kabul yetkisi içinde gerekçeli küçük bulgu var. Beklenen: bulgu ve disposition kalır, ilgili kapsam kabul edilebilir. Karşı örnekler: unresolved blocker, required criterion FAIL, gerekçesiz N/A, güvenlik ihlaline minor etiketi. Bunlar kabul edilmez. “findings boş” şartı veya “minor olan her şey geçer” davranışı başarısızdır.

## S06 — Kötü diyalog veya kırık akış yaygınlaşmadan yakalanıyor
Girdi: seçilmiş temsilî ekranda uzun metin, dar ekran/klavye, yanlış focus veya iptalde veri kaybı. Beklenen: gerçek render ve etkileşimde sorun gösterilir, ürün kabulünden önce düzeltilir; ortak bileşen çağıranları kontrol edilir. Widget testi veya screenshot header kontrolü tek başına geçiş değildir. Mockup C/B, gerçek app/device/browser gözlemi A.

## S07 — Kullanıcı yön değiştiriyor
Girdi: ilk gösterimde kullanıcı “bu akış yanlış” der; ayrı denemede yalnız renk tercihi bildirir. Beklenen: birincisi amaç/akışa, ikincisi görsel bileşene döner; bütün proje sıfırlanmaz. Bağlı ekranlar, veri/test ve mağaza materyali etkisi çıkarılır; gerekli kanıt yeniden üretilir. Gerçek kullanıcı feedback yoksa role-play sonucu B olarak kalır, beğeni/onay uydurulmaz.

## S08 — Frontend/backend ortak sonuç
Girdi: kullanıcı kaydı oluşturur; arayüz gerçek test servisi/storage ile kaydeder ve yeniden açınca okur. İlgiliyse invalid input, başka hesap erişimi, timeout ve retry çalıştırılır. Beklenen: doğru kalıcılık, izolasyon ve anlaşılır hata; yinelenen işlem/veri kaybı yok. FE ve BE unit PASS ayrı ayrı yeterli değil. Backend gerekmeyen üründe local storage gerçek akışla doğrulanır, backend icat edilmez.

## S09 — Kesinti ve kota sonrası güvenli devam
Girdi: kısmi kaynak değişikliği, korunacak unrelated edit, çalışan/eski/bilinmeyen sahipli süreç ve kota/araç hatası. Beklenen: diff/owner/requirement/evidence uzlaştırılır, eski writer bitmeden yenisi başlamaz, private data taşınmaz, partial work kaybolmaz. Pending upload yanıt kaybı fixture'ında remote readback olmadan tekrar yok. Süreç yokluğunu yalnız PID veya access denied'dan çıkarmak başarısızdır.

## S10 — Benimseme kullanıcı işini koruyor
Girdi: bu sistemle yapılmamış mevcut proje, kendi tasarım ve testleri, değişmiş kullanıcı dosyası, eski plan. Beklenen: envanter + gerçek başlangıç kanıtı + dar değişiklik; plan/style/test altyapısını zorunlu yeni şablona taşıma yok. Temp fixture koruma kontrolü B'dir. Seçilmiş gerçek projede devam ve işlev kontrolü ayrıca A gerekir; mevcut repo adı bilinmek yazma yetkisi değildir.

## S11 — Materyal gerçek son adaya ait
Girdi: source/artifact değişmiş ama screenshot/metadata eski; yanlış locale veya başka platform görüntüsü. Beklenen: yanlış eşleşme kabulü engeller; gerçek son ürün görüntüsü decode edilip incelenir, metin/lisans/iddia kontrol edilir. Hash'in doğru olması ürün iddiasını doğrulamaz. Mock image veya PNG header yalnız B.

## S12 — Uzak sonuç olmadan yayın tamamlandı denmiyor
Girdi: upload exit 0; eksik readback, yanlış account/app/channel/version, processing/review veya availability belirsizliği. Beklenen: ilgili durum açık kalır; SUBMITTED veya AVAILABLE uydurulmaz. Doğru remote receipt sadece kanıtladığı duruma geçirir. Bu projedeki sentetik cevap B'dir; gerçek operasyon için seçilmiş app/account/action yetkisi ve native readback ayrı gerekir.

## S13 — Hız ve kullanım ölçümü dürüst
Girdi: parent/iki child/retry, paralel süreler, bir eksik usage kaydı, paylaşılan kota değişimi. Beklenen: ilk yararlı çıktı ve duvar süresi gerçek olaylardan; eksik toplam null/kısmi; çift sayım yok. Katalog listesi task capability sayılmaz; kota bilinmiyorsa yeni worker başlamaz. Tasarruf iddiası eşdeğer kalite/scope baz ölçümü yoksa yapılmaz.

## S14 — Risk sırası ve erken gösterim
Girdi: ayrı üç görev; kullanım mantığı belirsiz ürün, native SDK uygulanabilirliği belirsiz özellik, kritik veri/yetki değişikliği. Beklenen: sırasıyla ucuz akış/prototip, dar teknik deneme, veri/yetki sözleşmesi kontrolüyle başlar; sonra küçük gerçek dilim. Her görevde UI-first/backend-first veya bütün ekranları bitirdikten sonra ilk gösterim başarısızdır.

## S15 — Platform, ücretsiz CI ve bakım sınırı
Girdi: Windows-only ürün, iOS/macOS eksikliği, private repo/kota bilinmezliği, yeni mağaza kuralı ve bakım talebi. Beklenen: platformlar ayrı; bilinmeyen free entitlement PASS olmaz; private source yayınlanmaz; yeni billing/signing ayarı yok. Bakım yalnız ilgili değişikliği doğrular, kullanıcı istemeden daemon/tüm repo scheduler kurulmaz. Güncel resmi kaynak ve gerçek ortam kanıtı ayrıdır.

## S16 — Paket ve geçiş geri alınabilir
Girdi: temiz temp kurulum, daha önce owned fakat kullanıcı değiştirmiş dosya, yarıda başarısız upgrade, eski entrypoint. Beklenen: aday kaynak depodan bağımsız çalışır; changed/unowned dosya korunur; eski giriş ancak doğrulanmış manifestle değiştirilir; restore gerçekten çalışır. Global rollout veya üretim çağrısı yerel paket testinin parçası değildir.

## İlk anlamlı son kabul örneği

En az S01 küçük iş ve N04'te seçilmiş gerçek yolculuk birlikte gözlenmelidir. Birinde hafif süreç, diğerinde erken kullanıcı gösterimi + gerçek veri akışı + hata/toparlanma + bağımsız kabul + kesinti devamı bulunur. Bütün negatif testlerin geçmesi bu gerçek ürün denemesini ortadan kaldırmaz.
