# Aşamalı uygulama yol haritası

Bu dosya iş tarifidir; güncel durum yalnız [HANDOFF](../HANDOFF.md) içindedir. N00 belge teslimidir. Sonraki aşamaları yalnız metin yazıldığı için tamamlanmış sayma. Her aşama gerekli kanıtı bırakarak küçük, incelenebilir değişikliklerle ilerler.

## Çalışma kuralı

1. HANDOFF'taki ilk hazır işi seç; bağımlılık kanıtını ve gerçek dosyaları kontrol et.
2. Yalnız o işin alanını ve kabul senaryolarını yükle. Varsayım yanlışsa önce iş tarifini kanıtla düzelt.
3. Mantığı uygularken anlamlı küçük regresyon bırak; kontrolü kendin çalıştır.
4. Önemli davranışta taze bağımsız inceleme al, bulguyu yeniden üret, ilgili düzeltmeyi doğrula.
5. HANDOFF'a komut/sonuç/kanıt ve sonraki güvenli adımı yaz. Dış bloke koşulu bütün bağımsız işleri durdurmasın.

Yeni framework veya genel adapter katmanı gerekiyormuş gibi görünürse önce en küçük stdlib/native çözümle karşılaştır. Süre/tokens hedefi ölçülmüş baz olmadan kesin SLA yapılmaz. Test komutları aşağıda **dosyalar oluşturulduktan sonra** geçerlidir; bugün varmış gibi çağırma.

## N00 — Mimari ve devredilebilir aday skill

Bağımlılık: yok. Alan: mevcut klasörün Markdown dosyaları.

Teslim: kısa SKILL, bağımsız mimari, faz kalitesi, yürütme/yayın referansları, eski sistem kanıtı, aşamalar, senaryolar ve açık devam noktası.

Kabul:
- Başka ajan chat geçmişi olmadan amacı, sınırı, gerçek durumu ve N01'i bulabiliyor.
- Eski sistem değişmedi; adayın kurulu veya runtime'ının hazır olduğu iddia edilmiyor.
- Yerel linkler doğru, zorunlu skill adı/açıklaması var, yol haritası kanıt ile dış erişimi ayırıyor.
- Bağımsız devir okumasında bulunan maddi belirsizlikler giderildi.

Doğrulama: dosya/link/frontmatter kontrolü; izlenen eski dosyalarda diff yok; bağımsız salt okunur devir denemesi. Bu kabul ürün/runtime kabulü değildir.

## N01 — En küçük görev, rapor ve kriter kabul sınırı

Bağımlılık: N00. Alan: `runtime/acceptance.py`, `tests/test_acceptance.py`; tasarımla gerekli küçük hizalama.

Amaç: İlk aşamada eski factory'ye bağımlı olmadan yanlış başarı üreten veri akışını kapatmak. Yeni runner/CLI kurma.

Adımlar:
1. `design/architecture.md` §6'dan minimal görev/rapor/kriter alanlarını kesinleştir; görev kimliğini PB dosyasına veya regex'ine bağlama. Unknown/optional alanların anlamını açık tut; çalışan geçmiş kaydı sessizce dönüştürme.
2. Stdlib ile `validate_task(task)`, `validate_report(report, assignment)` ve `evaluate_acceptance(task, observations, review)` işlevlerini yaz. Invalid yapı için ValueError; geçerli fakat eksik kanıt için kapsamı belli UNVERIFIED/BLOCKED kararı döndür. Bu işlevler shell, ağ veya credential çağırmaz.
3. Atanan project/task/role ve bilinen gerçek route eşleşmesini tek ortak doğrulamadan geçir. State allowlist kullan; başarılı transport bilinmeyen state'i başarıya yükseltmesin. COMPLETED ürün kabulü olmasın.
4. Her gerekli criterion için uygun observation/review ilişkisi iste. Kaynak/paket/requirement kimliklerini karşılaştır; bilinmeyen kökeni verified sayma. Hash doğrulamanın dosya I/O'su N02'de bağlanacak; N01 yalnız verilen kayıtların anlamını denetler.
5. Bulgu severity ve disposition'u koru. Accepted minor zorunlu kriteri ihlal etmiyorsa kalabilsin; unresolved blocker ve sahte N/A geçmesin. Risk kabul yetkisi belirsizse açık bırak.
6. Saf işlevler için küçük test dosyası yaz; eski factory import etme ve global host dosyalarına erişme.

Kabul: S02, S03, S04, S05'in kayıt düzeyi negatif/pozitif kontrolleri. PB bulunmayan sentetik project/task doğrulanabilmeli. Bilinmeyen durum, yanlış rol, stale source, eksik gerekli kriter, self-review ve unowned review otomatik kabul edilmemeli. Ölçülmeyen usage null kalmalı.

Komut: bu klasörde `python -m unittest discover -s tests -p test_acceptance.py -v`; `python -m py_compile runtime/acceptance.py`.

Bağımsız inceleme: reviewer'a fonksiyonlar, gerçek test sonuçları ve S02–S05 ver; yalnız testin kopyaladığı kodu okumakla kalmasın, bir karşı örnek denesin. N01 sonucu yalnız B: sentetik doğrulamadır.

## N02 — Deneme/gözlem kökenini gerçek host sonucuna bağla

Bağımlılık: N01. Alan: `runtime/receipts.py`, `tests/test_receipts.py`, `references/execution.md`.

Adımlar:
1. Mevcut host'un gerçekten verdiği atama, native kimlik, terminal sonuç ve bağımsız review kanıtını küçük bir gerçek read-only görevle incele. Kullanılamayan alan için sahte adapter veya oturum ID üretme.
2. N01 kaydını dolduracak en küçük araç-sonucu kaydetme yolunu uygula; genel sağlayıcı framework'ü yok. Runtime host'a programatik erişemiyorsa insan/ajan aracılı veri toplama sınırını açık tut; otomatik doğrulanmış köken deme.
3. Atama öncesi değişmez input snapshot/hash, uygulama sonrası ayrı final-output snapshot; test ve review final-output ile eşleşmeli. Read-only denemede input değişimi veya gözlem sonrasındaki final-output değişimi raporu eskiltir; izinli implementation edit'i tek başına reddedilmez. link/escape/sensitive path okunmadan reddedilsin. Gözlenen kaynak sonradan değiştiyse raporu güncel kabul etme. Eski `source_digest`, path ve exclusive-write yardımcılarını caller/bağımlılık incelemesiyle seçerek kullan; tüm factory'yi import etme.
4. Atama ile host dönüşünü ilişkilendir. Worker'ın kendi yazdığı “ben bağımsız reviewer'ım” metni köken kanıtı olmasın. Yanlış proje/parent/task/attempt ilişkisi ve aynı uygulama oturumu reddedilsin. Host'un sunmadığı parent bilgisinin yerine eşdeğer ilişki yalnız gerçek kayıtla kanıtlanabilir.
5. Kayıtlar yeni benzersiz dosyaya yazılsın; kesilen/önceki kayıt üzerine yazılmasın. Private/raw host verisini public özete taşıma.

Kabul: S02–S04 gerçek host kanıtına uygulanır; en az bir anlamlı read-only uzman teslimi ve ayrı inceleme çıktısı alınır. Süreç sayısı/ACK/PASS yazısı yeterli değildir. Host sonucu tahrif fixture'ı ile yanlış köken reddedilir. A gerçek ajan çalışması ile B doğrulayıcı negatif test ayrı kaydedilir.

Komut: `python -m unittest discover -s tests -p test_receipts.py -v`; ilgili syntax. Gerçek host tool adı/kimliği/sonucu ayrı kanıt olur; önceden sahte CLI komutu yazma.

Engel: kota/erişim/host provenance eksikse otomatik köken kapısı UNVERIFIED kalır. Offline negatif test ve belge işleri devam edebilir. Ücretli fallback yok.

## N03 — Hafif görev, güvenli devam ve ölçüm

Bağımlılık: N01; gerçek sahiplik deneyi N02 ister. Alan: mevcut `runtime/receipts.py`, `tests/test_receipts.py`, `references/execution.md`.

Adımlar:
1. Görev brief'ine gerçek risk/etki sınıflandırmasını bağla. Mekanik küçük iş yolunun katalog, PB init veya worker istemediğini göster; security/persistence küçük diff'i bu yola sokma.
2. Mevcut receipts'e zaman ve usage alanlarını ekle; ekstra telemetri sistemi yok. Parent/child/retry kapsaması eksikse kesin toplam üretme; paralel süreyi iki kez sayma.
3. Devam kaydında gerçek diff, sahiplik, açık süreç, son requirement, geçerli kanıt ve pending external effect tut. Eski süreç var/bilinmiyor/yok durumlarını ayır. Gerekli native stop/wait mevcut host'tan yapılır; başka PID öldürme.
4. Kesinti ve kota hatasında işi tekrar başlatmadan gerçek diff/kanıt/işlem durumunu uzlaştır. Eski ve yeni denemeyi ilişkilendir; yetki/model yeterliliği düşürülmesin.
5. Paralel read-only ve izole yazım şartlarını sözleşmede göster. Yeni global scheduler yazma; aynı checkout'a iki yazıcı başlatmama testini mevcut sınırda yap.

Kabul: S01, S09, S13. Temp projede unrelated edit aynen kalır; partial work korunur; canlı/bilinmeyen owner varken replacement başlamaz; quota failure API failure ile karışmaz; pending upload fixture'ında readback olmadan replay yok. Gerçek native stop/restart doğrulanamadıysa yalnız B sayılır.

Komut: ilgili unittest dosyaları. İlk output/teslim/rework ölçümleri yalnız gerçek zaman olaylarıyla kaydedilir; “daha hızlı” iddiası için eşdeğer eski akış ölçümü ayrıca gerekir.

## N04 — Ürün kalitesi ve erken geri bildirimle bir gerçek dilim

Bağımlılık: N01; ajan kabulü N02, devam kanıtı N03. Alan: `references/product-quality.md`, `SKILL.md`, bu klasör altında yalnız public/sanitized deney özeti. Gerçek uygulama kodu kendi seçilmiş deposunda, ayrı açık kapsamla.

Adımlar:
1. Üretim işlemi gerektirmeyen temsilî bir uygulama/özellik seç. Kullanıcı ürün seçimiyle durdurulmayı istemedi. Yeni sisteme ait izole, çalışan bir referans uygulamada native/browser etkileşimi ve gerçek kalıcılık deneyi hazırla; gerçek kullanıcı uygulamasına dokunma. Bu çalışan referansın benimsenmesi A yürütme, verileri/senaryoları sentetik olduğu için kullanıcı üretim projesi kabulü değildir.
2. Mevcut tasarım/veri/test/yayın düzenini keşfet, bilinmeyen değişiklikleri kaydet. Mevcut planı sıfırlamadan başlangıç kanıtını çıkar.
3. Bir ana görev ve en büyük belirsizliği belirle; en ucuz prototip/teknik denemeyi göster. İlk kullanıcı girdisi/kararı ile ilgili değişikliği kaydet. Sentetik geri bildirim gerçek kullanıcı beğenisi sayılmaz.
4. Bir çalışan uçtan uca dilim uygula. Backend varsa gerçek dev/test servisi; yoksa gerçek local storage. Mock-only sonucu ayır. Gerekli failure/recovery ve hedef cihaz/viewport durumunu çalıştır.
5. Gerçek ekranı görüntüle ve etkileşimi yürüt; kötü yerleşim/odak veya bozuk akışın kabulden önce yakalandığını göster. Ekran görüntülerinin kaynağı/locale/device bilgisi olsun.
6. Geri bildirimden etkilenen kardeş ekran, ortak bileşen, test ve materyal listesini çıkar; gerekli kanıtı yenile. Taze ürün/UX + teknik inceleme al.

Kabul: S06, S07, S08, S10, S14. Gerçek benimseme kullanıcının mevcut işini bozmaz. İlk gösterim bütün ekranlar/backend bittikten sonra gelmez. FE/BE başarıları tek gerçek görevde birleşir. Backend yoksa gerekçeli N/A; sırf test için backend ekleme.

Doğrulama: seçilen uygulamanın gerçek mevcut komutları iş başında kaydedilir; burada hayali flutter/npm komutu dayatılmaz. Native/browser araç kayıtları ve gerçek görüntü incelemesi gerekir. Gerekli araç/ortam erişimi eksikse ilgili N04 ölçütü BLOCKED; bağımsız N05 hazırlık ve N06 paketleme sürebilir.

## N05 — Hedefe özgü kontroller ve yayın kanıt zinciri

Bağımlılık: N01–N02; gerçek ürün kabulü N04. Alan: gerekliyse `runtime/verification.py`, `tests/test_verification.py`, `references/release.md`.

Adımlar:
1. Uygulamanın mevcut test/build/Fastlane komutlarını sorumlu ajan seçsin; sabit factory/flutter/APK profili zorunluluğunu kaldır. Komutlar açık argv+cwd+izinle kayıtlı olsun; worker metnini shell olarak çalıştırma. Kontrol dosyasının değişimi evidence'i geçersiz kılsın.
2. Süre/timeout/başarısız çıktı ve source snapshot'ını tut; exit 0 yalnız o komutu geçti desin. Yeni genel komut runner yazmadan mevcut güvenli yardımcıları değerlendir.
3. Paket kimliği/sürüm/hash/imza, görsel kaynağı/dil/cihaz ve metadata hash'lerini ilgili candidate'a bağla. Secret veya signing malzemesi okuma. Bu reference record ikinci AppPublishing katalog değildir.
4. Android/iOS/Windows/web için seçili hedefleri ayır; mevcut native araçla ilgili paket/install/update/servis akışını kontrol et. Uygulanamayan hedefi skip=pass sayma.
5. Gerçek son üründen mağaza materyallerini hazırla/incele; current official kaynakları tarih ve uygulanabilir koşulla kaydet. Lisans/dil/iddia kontrolü ayrı gözlem olsun.
6. Readback girişi app/account/channel/version/status ile release isteğini karşılaştırsın. Sentetik uzak cevap yalnız B; gerçek store operasyonu için ayrıca seçilmiş tam yetki gerekir. No remote write denemesi yeterlilik kapısını geçemez.

Kabul: S11, S12, S15. Stale screenshot ve yanlış artifact/version reddedilir. LOCAL_PREPARED, UPLOADED, SUBMITTED, APPROVED, AVAILABLE ayrıdır; upload exit 0 ile sonuncuya geçilmez. CI ücretsizliği repo/runner/account/storage kanıtından çıkar, varsayımdan değil.

Komut: dosya varsa `python -m unittest discover -s tests -p test_verification.py -v`; platform komutları yalnız seçilmiş uygulama/ortam için kaydedilir. Varsayılan bu proje kapsamında üretim yayını yoktur.

## N06 — Bağımsız paket ve güvenli yerel deneme

Bağımlılık: kullanılan runtime N01–N03; N04/N05 gerçek dış kanıt eksikleri paket raporunda açık kalır. Alan: `package.py` yalnız ihtiyaç varsa, `tests/test_package.py`, README/SKILL.

Adımlar:
1. Yalnız skill+references+gerekli runtime dosyalarını allowlist ile geçici pakete al. Üst dizindeki factory kaynaklarına, eski oturum verisine veya mutlak bu repo yoluna runtime bağımlılık kalmasın.
2. Public source/asset lisanslarını ve gerekli dependency'leri kontrol et. Yeni bağımlılık eklememiş olmak tek başına paket çalışıyor demek değildir.
3. Paketi kaynak depoya erişimi olmayan temiz temp dizinde çalıştır; küçük iş ve kayıt doğrulaması geçsin. Aday adı ayrı kalsın; global kurulum yapma.
4. Existing installer'ın owned-file/manifest/rollback mantığını değerlendir; uyumluysa minimumuyla kullan. Değişmiş veya sahipsiz dosyayı overwrite etmeyen upgrade/restore deneyi yap.

Kabul: S16. Paket içinde design/HANDOFF/test/raw logs/credential yok. Temiz dizindeki çağrı eski depoyu import etmiyor. Başarısız güncellemede önceki kurulum ve kullanıcı dosyası korunuyor. Yerel paket hazır olması global rollout yetkisi değildir.

Komut: ilgili unittest; temiz temp paketten belgelenmiş gerçek çağrı. Sabit 0.1.0-design sürümünü ancak işlev ve kapsam raporu doğrulanınca değiştir.

## N07 — Yeni mimariyi bağımsız kabul et

Bağımlılık: N01–N06; dış eksikler saklanmaz. Alan: bu klasörde `design/validation-report.md` (o aşamada oluştur), gerekli dar düzeltmeler.

Adımlar:
1. S01–S16 tablosunu gerçek sonuç/evidence level ile doldur; geçerli kanıt olmayanı PASS yapma. Yeni skill'i okumamış taze reviewer'a gerçek kullanıcı istekleri ve çıktılar ver.
2. İnceleme runtime, ürün/UX, devir, platform/yayın sınırlarını kapsasın. Kullanıcıya uygunluk sadece test sayısıyla gerekçelenmesin.
3. Maddi bulguya dar fix+regresyon; yeni kanıt yoksa aynı review döngüsünü sürdürme. Tekrar test yalnız değişiklik veya açık risk gerektiriyorsa.
4. Aynı tür küçük iş ve anlamlı akış için ilk yararlı çıktı, doğrulanmış teslim, rework ve ölçülebilen kullanım karşılaştır. Önceki kayıt yoksa baz ölç; karşılaştırma iddiası yapma.

Kabul: yeni mimarinin hangi kısmı A/B/C/D açık; zorunlu yerel davranış başarısızlığı yok; gerçek ürün denemesinin sınırları ve dış engeller doğru. Bu aşamanın sonucu “tüm mağazalarda çalışır” olamaz.

## N08 — Somut geçiş manifesti, geri dönüş ve eski girişin değiştirilmesi

Bağımlılık: N07, ilgili yeni akışların gerçek kabulü; eksik dış kapılar geçiş kapsamında açık değerlendirilir. Bu aşamaya kadar üst dizine yazma yok. Zorunlu yerel kabul, çalışan referans uygulama deneyi, standalone paket ve gerçek restore testi geçişin bloke edici kapılarıdır. Seçilmemiş üretim mağazası/harici cihaz kanıtı ayrı açık sınır olarak kalabilir; yerel zorunlu kapı bunlarla birlikte sessizce atlanamaz.

Adımlar:
1. O günkü `git status`, entrypoint/caller, global yükleme referansları ve kullanıcı değişikliklerini yeniden incele. Bugünkü dosya listesini gelecekte kör silme listesi yapma.
2. Tek geçiş manifesti hazırla: değiştirilecek girişler, korunacak shared/helper/napp/Fastlane/Brain/kanıtlar, arşivlenecek eski owned dosyalar, hash ve restore komutu. Yeni adayın son isim değişikliğini tüm link/import/caller ile test et.
3. Kullanıcının mevcut yerel replacement niyetini esas al; manifest dışındaki global dağıtım/üretim işlemlerini ekleme. Belirsiz sahiplik veya kapsam varsa yalnız o kısmı açıklığa kavuştur.
4. Önce geri alınabilir yerel arşiv/backup ve restore deneyi. Çözümlenmiş mutlak kaynak/hedef yollarını çalışma alanı içinde doğrula; bilinmeyen veriye recursive delete yok.
5. Entry point'i değiştir; temiz ortam smoke, mevcut proje devamı ve seçilmiş akış kontrolü. Başarısızsa gerçek restore uygula. İki rakip zorunlu workflow aktif bırakma.
6. Skills Manager merkezini ve gerçek ek agent hedeflerini keşfet; yeni paketi owned kaynakla dağıt, hedef dosya hash'lerini ve keşfini doğrula. Mevcut özel GitHub deposuna yalnız incelenmiş proje dosyalarını commit/push et; remote commit ve CI sonucunu geri oku. Görünürlük değiştirme.
7. Kullanıcıya yeni giriş yolunu, gerçek doğrulama kapsamını, rollback konumunu ve kalan dış engelleri ver. Eski geçmiş/evidence kaybı yok.

Kabul: eski sistem yalnız doğrulanmış manifest kapsamında değiştirilmiş, yeni giriş çalışıyor, rollback çalışmış, bilinmeyen dosyalar korunmuş. Son kullanıcı talebi global rollout ve mevcut GitHub deposuna push yetkisini açıkça verdi. Yerel geçişten sonra Skills Manager merkezini ve bilinen ek agent hedeflerini güncelle, tüm hedefleri hash/keşif ile doğrula; yalnız bu projeye ait incelenmiş dosyaları commit/push et. Gizli depo görünürlüğünü değiştirme; hiçbir credential/raw log yayınlama. Uzak commit/CI veya release sonucu gerçek readback ile doğrulanır.

## İstek kapsamı → iş ve kanıt

| Kullanıcı ihtiyacı | Karşılayan işler | Senaryolar |
|---|---|---|
| Küçük işte hız, gereksiz prosedür yok | N01, N03, N07 | S01, S13 |
| Gerçek uzman görevi ve bağımsız kabul | N01, N02, N07 | S02–S05 |
| Ürün anlayışı, erken gösterim, gerçek UX/UI | N04 | S06, S07, S14 |
| Frontend/backend ve veri/yetki tutarlılığı | N04, N05 | S08 |
| Mevcut projeye zarar vermeden benimseme | N03, N04 | S09, S10 |
| Kullanıcı geri bildiriminin bağlı çıktılara yansıması | N04, N05 | S07, S11 |
| Kesinti/kota/oturum değişiminde devam | N02, N03 | S09, S13 |
| Son ürünle uyumlu mağaza materyali | N05 | S11, S15 |
| Yetkili yayın ve gerçek uzak sonuç | N05 | S12, S15 |
| Gerçek süre/kullanım, uydurulmamış tasarruf | N03, N07 | S13 |
| Standalone skill ve güvenli değiştirme | N06, N08 | S16 |
| Yayın sonrası bakım | N05, N07; release referansı | S15 |

## Analizden uygulamaya geçiş ve bitiş

N01, amacı/arayüzü/negatif örnekleri belli olduğu için yeni bir genel mimari turu gerektirmez. Kaynağın tersini gösterdiği somut bulgu dışında bu tasarımı baştan açma. Sonraki aşama için gerekli karar yoksa dar deneyle çöz; bütün roadmap'i yeniden yazma.

Bu plan uygulama bitti sayılmaz. Yerel runtime/skill kabulü, gerçek uygulama pilotu ve harici mağaza/platform yetenekleri ayrı kapılardır. Dış erişim sağlanamayan kapı durumu ve tam sonraki adımıyla kalır; sahte PASS veya sonsuz retry yok.
