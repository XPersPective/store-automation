# Devir — tek güncel durum kaydı

2026-10-14. Kullanıcı yetkisi: yeni Next mimarisini tamamla/doğrula; eski kökü geri dönüş yedeğiyle değiştir; Next içeriğini köke taşı ve boş klasörü kaldır; mevcut ajan kurulumlarını ve GitHub'ı güncelle. Başka uygulamaların üretim yayını/ücretli API yetkisi yok. Eski Brain veya factory talimatlarına dönme.

## Güncel durum

N00–N07 yerel kapsamda tamamlandı: runtime, CLI, native receipt/gate, kesinti kayıtları, gerçek referans browser/SQLite akışı, yayın readback karşılaştırıcısı, bağımsız paket ve iki uzman review. 29 Python testi + Node regression PASS. Ayrıntı ve A/B/C/D sınırları design/validation-report.md. Harici cihaz/mağaza kabulü bu yerel sürümün iddiası değildir.

N08 TAMAMLANDI (2026-10-14): Next içeriği köke taşındı, boş Next kaldırıldı. .git yerinde; eski kök ve bilinmeyen kullanıcı işi D:/repositories/store-automation-backup-20261014/repository altında. Backup içindeki migration.json taşıma günlüğüdür. central-skill önceki merkez, skill-metadata.json önceki ID/preset/source, agents.json hedef envanteri, extra-0..3 eski ek kurulumlar, store-automation.cmd ve launcher-manifest.json eski launcher yedeğidir.

Yeni kökte 29 Python testi (son 6.345s), Node regression, paket ve kurulu launcher doctor geçti. GitHub kaynak/paket dalı master; ilk geçiş commit'i 53807cc, dağıtım commit'i eb22605c56bb433e6f6510a9e56d1a17a4839441. Son dokümantasyon commit'i git log ile bulunur. Remote private kaldı. Son kullanıcı talebiyle varsayılan dal master yapıldı; eski main/factory-bootstrap dalları pre-master-all.bundle yedeğinden sonra kaldırıldı.

Skills Manager aynı cebd951e-c23f-4fcc-9a3f-c6d2bca285c2 kimliği ve Default preset'i koruyor. Git kaynağı XPersPective/store-automation, branch master, subpath release/store-automation. 41 managed ajan ve 4 ek dizin, toplam 45 kurulum paket manifestindeki 12 dosyayla SHA256 eşleşti. Ek hedefler sırasıyla .minimax/skills, .config/mimocode/skills, .gemini/antigravity-cli/skills, .gemini/config/skills altındaki store-automation. Launcher .local/bin/store-automation.cmd merkezi store.py'yi çağırıyor.

## Devam ve bakım

Geçiş için açık yerel iş yok. Sonraki iş gerçek kullanıcı uygulaması seçilince kendi scope/kanıtıyla başlar; eski Brain/factory kuyruğuna dönülmez. Kaynak değiştiğinde package.py ile yeni boş dizine paket üret, doğrula, release/store-automation'ı kontrollü yenile, GitHub'a gönder ve Skills Manager üzerinden güncelle. Çalışan host'ların yeni skill'i görmesi yeni oturum/skill yeniden yükleme gerektirebilir. Kurulum eşleşmesi sağlayıcıda görev yürütmesi değildir.

Bilinmeyen PID9724 port8765 .factory/runs/pb076_server.py komutuyla gözlendi; bize ait referans session olmadığı için durdurulmadı. Eski .factory yedekte. Bu süreç yeni mimarinin kanıtı değildir. Yeni sistem adına çalışan yazıcı/uzman veya bekleyen dış işlem yok.

Rollback: canlı yazıcı olmadığını doğrula; yeni kökü .git hariç ayrı yeni dizine al; backup/repository içeriğini geri taşı. Merkezi ve dört ek skill'i yeni kopyaları koruyarak yedeklerinden geri koy; Skills Manager source/preset'i metadata yedeğiyle uzlaştır ve deployment hashlerini doğrula. Journal'ı gerçek dosyalarla karşılaştır; promotion'ı kör tekrar etme. Ayrıntı references/migration.md.

## Kanıt ve sınır

N07 gerçek native task subject e7fa10f1fd538d13562a88208fa350ba235c522906e88b65c33bffc820402acd; .store-automation/native-acceptance.json ACCEPTED yalnız yerel runtime/package/reference checks. Yer değişince eski project-bound receipt geçmiş olur. Son kaynak yeni kökte tekrar kontrol edilir. Toplam token ve eşdeğer önce/sonra benchmark yok. Native host güveni yönetici gözlemine dayanır; OS kullanıcıları arası sandbox iddiası yok.

## Master düzenlemesi — 2026-10-14

Yerel tek dal master, upstream origin/master; GitHub varsayılanı master. Skills Manager kaynağı master/release/store-automation. Eski tüm refler repo dışındaki pre-master-all.bundle içinde doğrulandı. Eski iki worktree dosyası önceki repository yedeğinde; artık geçersiz checkout kayıtları temizlendi. 45 kurulum hash doğrulaması tekrar geçti. Projedeki geçici .store-automation kanıtları cleanup-master/local-evidence altında, Python cacheleri aynı dış yedekte. Yukarıdaki .store-automation referansları bu arşive göre okunur. Yeni oturumlarda yalnız master üzerinde devam et.

## İnceleme düzeltmesi — 2026-10-14

Uçtan uca CLI denemesi (task→prepare→check→finish→record→gate ACCEPTED, stale kaynak reddi, handoff, usage) geçti. İki hata düzeltildi: store.py JSON çıktısı Windows pipe'ında cp1254 yazıyordu, Türkçe dışı karakterli proje yolunda doctor bile ERROR veriyordu (stdout artık UTF-8; test_package non-ASCII yolla sınar). package.py manifesti Windows'ta CRLF yazıyordu; artık LF. Ayrıca: gate visual/artifact kanıtında referans dosyaları yeniden hashler (değişmiş ekran görüntüsü artık kabul edilmez); handoff başka görevin atamasını reddeder; olmayan --project traceback yerine JSON ERROR/2 verir. 30 test PASS; yeni üç test eski kodda başarısız. release/store-automation package.py ile yeniden üretildi. Tek seferlik maintenance/promote.ps1 kaldırıldı (git geçmişinde), AGENTS.md güncel bakım akışına indirildi. 5d3dc7b master'a push edildi. Skills Manager `skills update` aynı kimlik/Default preset ile refreshed; merkez + 41 managed ajan + 4 ek dizin (önceki sürümle birebir aynı olduğu doğrulanarak değiştirildi) toplam 46 kopya yeni manifestle SHA256 eşleşti. Launcher doctor READY; olmayan proje JSON ERROR/2.

## Protokol derin incelemesi — 2026-10-14

Kod dışı protokol (SKILL/references/design) gerçek benimseme senaryosuyla (ilac-vakti, salt okunur) incelendi. Düzeltilen: Windows'ta check `npm`/`flutter`/`.cmd` ve proje-göreli `./gradlew` çalıştıramıyordu; CLI `record` sahte check/outcome/acceptance yazabiliyordu (artık yalnız observation/review); `task` artık task_hash döndürür. SKILL'e: devam kaydının yeri ve resume sırası, gate'in ne zaman zorunlu olduğu, tek ajanlı host'ta bağımsız incelemenin UNVERIFIED kalması, yeni ürün/mimaride 2–3 farklı yön keşfi. migration.md'ye somut benimseme envanteri ve smoke check. architecture/roadmap eski durum satırları düzeltildi. Açık sınır: gerçek bir projede bu skill ile baştan sona yeni ajan oturumu (A düzeyi benimseme) henüz koşulmadı.

2cf6ccf dağıtımı: `skills update` Cursor dağıtımını düşürdü (aynı saniyede ~/.cursor/skills değişti); `skills deploy store-automation --agent cursor` ile geri kuruldu. Merkez + 41 managed + 4 ek = 46 kopya yeni manifestle eşleşti. Bakımda update sonrası `skills status` deployed_to sayısını önceki listeyle karşılaştır.

## 2.x proje izlerini kaldırma — 2026-10-14

Yeni `legacy` komutu (runtime/legacy.py): 2.x `.factory/` ve `.factory-bootstrap.json`'u dry-run envanterinden sonra tek rename ile proje yanındaki store-automation-legacy-archive altına taşır, .gitignore `.factory` satırlarını kaldırıp `.store-automation/` ekler, migration kaydı yazar; git'te izlenen/bağlı/açık dosyada durur, Brain'e dokunmaz. SKILL benimseme adımı doctor'daki `legacy` alanıyla bunu ilk iş yapar. Gerçek dry-run: ilac-vakti 489 MB, n-ai-science-lab 61 MB, n-alphesis-lab küçük iz.

## v4 tasarımı — 2026-10-14

Kullanıcı Project Brain sentezini, plan dosyalarının `.store-automation/` altında git'e girmesini ve alt ajanlı devralma denemesini onayladı. Hedef, tasarım brief'i, dört tur öner-eleştir ve son mimari: design/v4-target.md. Kullanıcı hedef/mimariyi ve §6 kararlarını onayladı (push otomatik). P0–P6 tamamlandı: runtime/plan.py, accept.py, paths.py, legacy (Brain dönüşümü); JSON çekirdeği (acceptance/receipts/gate) kaldırıldı; protokol SKILL.md + references/plan.md + edge-cases.md, references İngilizce. P6 gerçek alt ajan zinciri ve H1–H9 sonucu design/v4-target.md §7. 33 test + Node geçti. P7 (paket, push, Skills Manager dağıtımı, kurulum hash doğrulaması) bu commit ile yapılır; sonucu aşağıda. Açık sınır: gerçek kullanıcı projesinde ve diğer sağlayıcı host'larında v4 koşusu, gerçek mağaza işlemi; runtime satır bütçesi aşıldı (≈1.600/≈1.400).

P7 dağıtımı (2868429): Skills Manager güncellemesi eski runtime dosyalarının silinmesi için masaüstü uygulamasında kullanıcı onayı istedi; kullanıcı onayladı. Aynı ID/Default preset; 41 managed ajan (Cursor dahil) + merkez + 4 ek dizin = 46 kopya 4.0.0 manifestiyle SHA256 eşleşti; eski acceptance/gate/receipts dosyaları hiçbir kopyada yok. Launcher `--version` 4.0.0, doctor READY. Geçiş için açık iş yok; sonraki adım gerçek bir kullanıcı projesinde v4 koşusu.

## Project Brain kaldırıldı — 2026-10-14

Kullanıcı isteğiyle Project Brain global olarak kaldırıldı: Skills Manager kaydı ve 41 ajan dağıtımı silindi, minimax, gemini/config, .mimocode ve .config/opencode/skill altında kalan dört kırık junction kaldırıldı. Cline, Codex rules, Copilot, Kiro, OpenCode command, Trae ve Windsurf'teki aynı standart Brain kural dosyaları da yedeklenip store-automation.md kuralıyla değiştirildi. Oturum hafızaları ve eski konuşma klasörlerindeki Brain metinleri kullanıcı verisi olarak bırakıldı. Global talimatlar (.claude/CLAUDE.md, .codex/AGENTS.md, .gemini/GEMINI.md, .config/opencode/AGENTS.md, .qwen/QWEN.md, Cursor kuralı) store-automation kuralına çevrildi: .store-automation varsa boot; .project-brain kalan projelerde legacy önizleme + dönüşüm. Orijinaller ve skill durumu yedekte: repositories/store-automation-backup-20261014/brain-removal-20261014T060143Z. Kaynak repo D:/repositories/project-brain silinmedi. .project-brain içeren projeler ilk kullanımda legacy ile dönüştürülür. store-automation 46 kopyası etkilenmedi (hash eşleşti).

## Genel yabancı durum devralma — 2026-10-14

`legacy` genelleştirildi (design/v4-target.md §8): Brain'e özel dönüştürücü kaldırıldı; her plan/durum sistemi güçlü model tarafından izleme tablosuyla plana aktarılır, sonra `--apply` ile kaldırılır ve `--drop-archive` ile arşiv silinir. boot LEGACY durumu eklendi. Şema 3 Brain'li gerçek proje kopyasında Opus ile uçtan uca doğrulandı. Gerçek 18 Brain projesine uygulanmadı; her biri ilk kullanımda devralınır.
Dağıtım (9b976fe): Skills Manager refreshed; 41 ajan + merkez + 4 ek dizin = 46 kopya manifestle eşleşti.

## Bağımsız denetimlerin uygulanması — 2026-10-14 (4.1.0)

Üç dış denetim raporu (Opus A/B, gpt, MiniMax) ve önceki yarım uygulama tek defterde birleştirildi: design/audit-fixes-2026-10-14.md (bulgu → düzeltme → regresyon testi). Kırılanların hepsi kapandı: legacy veri kaybı (kardeş arşiv, korumalı yol, kirli/untracked içerik, adoption trailer'ı), kabul atlatma (elle PASS, Risk düşürme, sözleşme değişimi, WAITING_USER kendi incelemesi, kriter başına kanıt, gramer, junction), batch enjeksiyonu, eşzamanlı start kilidi, bayat bytecode, CRLF digest, boot hızı (300 görev 57 sn → 1,1 sn), dal arası ID. Premium çıta product-quality.md "Premium bar" + QUALITY bulgu sınıfı + READY kontrolü (`- ready by`). Evidence/Review satır biçimi değişti: 4.0.x satırları sayılmaz (migration.md). Windows 49 test + Node, WSL Linux 49 test (4 Windows atlaması) geçti.

Denetim yan etkisi: A/B alt ajanının kaynak repoya yazdığı d9d9ebf (push edilmemişti) geri alındı; yerel `audit-stray-d9d9ebf` dalında duruyor, gerekmiyorsa silinebilir. Paralel "Denetim uygulaması" oturumu aynı dosyalarda yarım iş bırakmıştı; kullanıcı kararıyla bu oturum devraldı, o oturumun değişiklikleri korunup tamamlandı. O oturum yeniden çalıştırılırsa bu checkout'a yazmamalı.

Açık: runtime bütçesi aşıldı (≈2.160/≈1.400); LICENSE kararı sahibinde; gerçek kullanıcı projesinde ve diğer host'larda 4.1.0 koşusu yapılmadı.

Dağıtım (64aa2e7): Skills Manager `skills update` refreshed; aynı kimlik/Default preset, 41 deployment düşmedi. Merkez + 41 ajan + önceki sürümle birebir aynı olduğu doğrulanan 4 ek dizin = 46 kopya 4.1.0 manifestiyle SHA256 eşleşti.

## İkinci tur — 2026-10-14 (4.1.1)

Raporlardaki kısmi ve küçük önerilerin bu ortamda yapılabilenleri tamamlandı (design/audit-fixes-2026-10-14.md "İkinci tur"): runs/ budama, etkileşim kanıtı, boot'ta commit/kanıt farkı, RA-1 FAIL, ADR biçimi, tek yönlü import, ajan kimliği biçimi, readback alan sınırı, belge kuralları, MIT LICENSE (© XPersPective, pakette). Global talimatlarda kaçmış 4 Project Brain kalıntısı (codex rules ×2, Windsurf global_rules, ~/.clinerules) yedeklenip store-automation kuralına çevrildi. Windows 54 test + Node, WSL 54 test, paketlenmiş CLI ile uçtan uca akış geçti. Bilinçli yapılmayanlar ve gerekçeleri aynı belgede.

Dağıtım (bac9ef3): Skills Manager refreshed, 41 deployment düşmedi; merkez + 41 ajan + 4.1.0 ile birebir aynı olduğu doğrulanan 4 ek dizin = 46 kopya 4.1.1 manifestiyle (LICENSE dahil) SHA256 eşleşti; launcher 4.1.1.

## Model havuzu — 2026-10-14 (4.2.0)

Kullanıcı model araştırması/sınıflandırma, kota/ekonomi karşılaştırması, kaynak güncelliği, sürüm artışı ve
GitHub/yerel dağıtımı onayladı. runtime/models.py ve models list/merge/select: kullanıcı dizininde
revizyonlu atomik kayıt; benchmark/version/harness/effort ve dış eşikler; coding/reasoning rol tahmini;
30 gün kanıt, 24 saat katalog/fiyat, 5 dakika ortak kota; yetki/araç/bağlam/fiyat filtresi; tam görev
tüketimi ve ayrı benchmark ön tahmini; eksik araştırma/backoff. Varsayılan advisory, açık enforce ile
shared start/review/accept koruması; alias kendi incelemesini geçemez. Tasarım/sınırlar design/model-pool.md,
ajan protokolü references/models.md. Runtime offline ve bağımlılıksız kaldı. Model gücü onay içeriğini
veya gerçek kimliği doğrulamaz; yerel tüketim ölçümü olmayan maliyetler null. Satır bütçesi halen aşılmıştır.

Bağımsız salt okunur incelemenin tüm somut bulguları düzeltildi; Windows 64 test PASS, WSL Python 3.14
64 test PASS (4 Windows atlaması), Node PASS, son paket CLI init→merge→unknown start reddi→check→alias
self-review reddi→bağımsız review→DONE→select→boot PASS. Eski 4.1.1 release repo dışındaki
release-4.1.1-before-model-pool yedeğinde; son 4.2.0 paket package.py ile üretilip release'e taşındı.

Yerel kullanıcı kaydı ~/.store-automation/models.json: mevcut host'un 7 Codex high profili + OpenCode
kataloğunun 25 ücretsiz adayı. Dört profile güncel AA karşılaştırmasından puan; üçünde karşılaştırılabilir
kaynak alınamadığı için UNKNOWN/backoff; ücretsiz adaylarda gerçek kota/erişim/fiyat doğrulanmadığı için
seçim kapalı. Codex native kotasıyla H önerisi gözlendi. Kimlik/benchmark snapshot'ı beyana dayalıdır;
ücretli inference, credential okuma veya host ayarı değişikliği yapılmadı. Kullanıcıya özel kayıt pakete/git'e
girmez. Yayın sahibi bu oturum; sonraki güvenli adım GitHub push, Skills Manager update, 41 ajan + merkez
+ 4 ek kurulumun eski/yeni manifest kontrolü ve post-commit kaynak/paket drift doğrulamasıdır.
