# Doğrulama ve mimari karar raporu — 2026-10-13

## Sonuç ve kapsam

Yeni sistemin yerel runtime, paket ve referans akışı doğrulandı. Ürün teslimini native host yönetir; Python yardımcıları görev/atama/son kaynak/kanıt/bağımsız inceleme bağını denetler. Tek bir sağlayıcıya ait oturum biçimi, zorunlu Brain/katalog taraması ve büyük factory runner kaldırıldı. Mevcut ProcessTree yardımcısı bağımsız küçük modüle alınarak yeniden kullanıldı. İkinci backend framework, uploader, credential deposu veya dashboard eklenmedi.

Bu rapor hatasızlık veya bütün mağazalarda uçtan uca yayın iddiası değildir. Gerçek cihaz, ekran okuyucu, kullanıcı beğenisi, diğer sağlayıcılarda görev yürütmesi ve üretim yayınları bu denemenin kapsamı dışındadır. Sistem bunlara ait kanıt olmadan kabul vermez. Geçişin gerçek durumu HANDOFF'tadır.

## Gerçek düzeltmeler

| Tetikleyici / kullanıcı etkisi | Ortak kök neden ve düzeltme | Kontrol |
|---|---|---|
| BANANA veya yanlış görev/rol raporu başarı görünüyordu | Ortak allowlist, atama kimliği ve rapor doğrulaması | test_acceptance |
| Başka kaynak/oturum veya kendi incelemesi kabul edilebiliyordu | Input/output ayrı snapshot; task hash, role, actor, attempt ve bağımsız review eşleşmesi | acceptance, receipts, gate testleri |
| Başka klasörde geçen test ödünç alınabiliyordu | Gate check.cwd ve tam güncel source manifestini bağlar | test_identical_files_in_foreign_check_directory_do_not_accept |
| COMPLETED sonucu içinde BLOCKED raporu saklanabiliyordu | Gate ortak validate_report'u yeniden çalıştırır, state çelişkisini reddeder | test_completed_outcome_cannot_hide_blocked_report |
| Windows .env. takma adı gizli dosya sınırını aşıyordu | Yol bileşeni son nokta/boşluk, reserved ad ve bağlı ancestor açılmadan reddedilir | test_private_paths_are_rejected_before_any_hashing |
| Bozuk remote reference/time MATCHED oluyordu | Metin ve timezone datetime doğrulaması; güncellik yönetici sorumluluğu açık | test_verification |
| Timeout sonrası alt süreç yazmaya devam edebilirdi | Mevcut Windows JobObject yaklaşımı tekrar kullanıldı; sahipli child yokluğu gerçek gecikmeli yazıyla sınandı | test_real_timeout_kills_owned_descendant_before_delayed_write |
| Paket linked ancestor üzerinden dış dosya alabiliyordu | Ortak public_path kontrolü yeniden kullanıldı | bağımsız kaynak incelemesi; path regression; standalone test |
| SQLite kilit yanıtı istemci sınırını aşabiliyordu | Yazma busy timeout 0.2s; hata sonrası aynı işlem retry | test_storage_failure_then_retry_preserves_one_note |
| Yanıt kaybında içerik değişikliği sessiz çift kayıt doğuruyordu | Belirsiz isteğin içerik/kimliği korunur, önce readback; kayıt varsa ikinci POST yok | gerçek outage/recovery + Node sentetik committed-response-loss testi |

İnceleme sırasında oluşturulan kısa girinti hatası test tarafından yakalandı; düzeltildikten sonra sunucu yeni süreçte başlatıldı. Önceki açık sunucunun eski kodu yeni kaynak kanıtı sayılmadı.

## Gerçek yürütme

`python -m unittest discover -s tests -v`: 29 kontrol başarılı. Son bağımsız yürütmeler 7.325s ve 7.471s. `node tests/reference-ui-check.cjs`: başarılı; gerçek JS event handler'larını sentetik DOM/network ile sınar. Paket temiz temp dizinde eski kaynağa bağımlı olmadan doctor çalıştırdı; mevcut hedefe overwrite reddedildi ve user.txt korundu.

Gerçek native uzmanlar: /root/reference_product HTTP/SQLite/HTML/JS dilimini üretti; kota hatasında kısmi dosyalar korundu. /root/boundary_review ve /root/product_final_review bulgular üretti, düzeltmeler sonrası ayrı salt okunur görevlerle yeniden inceledi. Model/effort host tarafından bu atamalarda açıklanmadığı için null bırakıldı.

N07-native-final görevi önceden prepare edildi; ayrı native atama sonuçları yönetici tarafından gözlendi. Gate sonucu ACCEPTED yalnız 'Local runtime, package and reference checks only' kapsamındadır. Subject: e7fa10f1fd538d13562a88208fa350ba235c522906e88b65c33bffc820402acd. Yerel acceptance receipt: .store-automation/runs/acceptance-b2277a24b70940b48441f5edb2be9ac6.json. Bu dosyalar aynı OS kullanıcısına karşı kriptografik native authentication değildir; trusted supervisor sınırı açıktır. Taşıma sonrası bunlar eski konumun tarihsel kanıtıdır.

Gerçek browser: Türkçe boş durum, başlık doğrulama, kayıt ve reload ile SQLite kalıcılığı; 390x844 diyalog, Escape ve geri dönen odak; güncel süreçte açık form sırasında sunucunun durması, metnin korunması, servis açılışı ve tek kayıtla toparlanma gözlendi. Görseller: [mobil](evidence/dialog-mobile.png), [ilk kayıt](evidence/journey-desktop.png), [son toparlanma](evidence/recovery-desktop.png). İlk iki görüntü retry düzeltmesinden önce, son görüntü düzeltmeden sonra alındı; görsel düzen değişmedi. Bunlar gerçek cihaz/screen reader kanıtı değildir. Tarayıcı tamamen yenilenir/kapanırsa kaydedilmemiş taslağın korunması bu referansta uygulanmadı.

## Senaryo kapsamı

| Senaryo | Düzey ve kanıt |
|---|---|
| S01 küçük iş | A/C: mekanik README metni düzeltmesi doğrudan yapıldı; PB/katalog/ajan gerekmedi. Risk ayrımı skill'de |
| S02 geçersiz rapor | A+B: gerçek native rapor + negatif validator testleri |
| S03 bağımsızlık | A+B: iki ayrı native görev/sonuç + yanlış aktör/atama testleri |
| S04 eski kanıt | A+B: gerçek source snapshot + dosya/manifest/tahrif/yanlış cwd testleri |
| S05 bulgu | B: minor korunur, required ihlali/blocker geçmez |
| S06 UX kusuru | A+B: bağımsız incelemenin bulduğu belirsiz retry akışı düzeltildi, gerçek browser toparlanma ve sentetik kayıp yanıt |
| S07 yön değişimi | B/C: inceleyenin akış geri bildirimi JS/test/README/son görsele uygulandı; gerçek kullanıcı beğenisi/onayı yok |
| S08 FE/BE | A: gerçek browser+HTTP+SQLite; testte process restart/503/retry/409 |
| S09 kesinti | A+B: gerçek ajan kota kesintisi sonrası dosyalar korundu; OS child cleanup ve owner/pending-upload fixture |
| S10 benimseme | A+B: ayrı uzmanın yarım teslimi kaynak/test/veri korunarak devralındı; unrelated kullanıcı dosyası fixture koruması. Kullanıcının üretim uygulaması denenmedi |
| S11 materyal | A+B: final ekran görüntüsü gözlendi; source/hash/stale kontrolleri. Store listing hazırlanmadı, hedef seçilmedi |
| S12 uzak sonuç | B+D: account/app/channel/version/state negatifleri; gerçek store işlemi yok |
| S13 süre/kota | A+B: gerçek check süreleri, gerçek kota kesintisi, eksik usage toplamı null. Eşdeğer önce/sonra benchmark ve toplam token yok |
| S14 erken dilim | A/C: final sistem bitmeden çalışan küçük ürün kullanıcıya gösterildi; diğer risk sıraları rehberde |
| S15 platform/bakım | C+D: hedefe göre rehber ve resmi kaynaklar; cihaz/CI/store hesapları denenmedi |
| S16 paket/taşıma | A+B: bağımsız temp paket, overwrite reddi, PowerShell gerçek fixture promote+restore. Global sonuç ayrıca migration kaydında |

## Yayın sınırı ve güncel kaynaklar

2026-10-13'te resmi [Fastlane supply](https://docs.fastlane.tools/actions/supply/), [deliver](https://docs.fastlane.tools/actions/deliver/), [Apple review](https://developer.apple.com/app-store/review/guidelines/) ve [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) incelendi. Supply mevcut track sürümlerini okuyabilir; metadata upload ile gerçek kullanıcı erişimi aynı şey değildir. Private repository runner maliyeti ücretsiz varsayılmadı; yeni ücretli CI açılmadı. Mevcut AppPublishing/Fastlane korunur. Bir gerçek uygulama seçildiğinde platform, aday, imza, locale, account/channel ve yetki yeniden somutlaştırılır; yokluğu sahte PASS ile kapatılmaz.

## Ölçüm yorumu

Eski 130 testin 26.230s, yeni 29 testin yaklaşık 7–8s sürmesi eşdeğer kapsam karşılaştırması değildir; hız kazanımı iddiası yok. Yeni sistem küçük işte zorunlu küresel keşfi kaldırır, fakat toplam teslim/analiz/bekleme/rework ve token maliyeti eksiksiz ölçülmedi. Ölçülmeyen değerler null kalır. Dağıtım byte eşleşmesi, o ajan sağlayıcısında gerçek çalıştırma kanıtından ayrı raporlanır.


## 2026-10-14 geçiş sonucu

N08 gerçek repository üzerinde tamamlandı; Next kaldırıldı, eski kaynak repo dışında korundu. Yeni kökte son 29 test 6.345s, Node regression ve doctor başarılı. Merkezi kayıt ID/preset korundu; 41 managed + 4 ek kurulumun 12 paket dosyası SHA256 eşleşti. Launcher merkezi store.py üzerinde READY verdi. GitHub factory-bootstrap eb22605 dağıtım commitini içeriyor; private görünürlük korunuyor. Restore bilgileri HANDOFF içinde. Bu sonuç 45 sağlayıcıda AI görevi çalıştırıldığı iddiası değildir.
