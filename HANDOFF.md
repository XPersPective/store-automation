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

Uçtan uca CLI denemesi (task→prepare→check→finish→record→gate ACCEPTED, stale kaynak reddi, handoff, usage) geçti. İki hata düzeltildi: store.py JSON çıktısı Windows pipe'ında cp1254 yazıyordu, Türkçe dışı karakterli proje yolunda doctor bile ERROR veriyordu (stdout artık UTF-8; test_package non-ASCII yolla sınar). package.py manifesti Windows'ta CRLF yazıyordu; artık LF. Ayrıca: gate visual/artifact kanıtında referans dosyaları yeniden hashler (değişmiş ekran görüntüsü artık kabul edilmez); handoff başka görevin atamasını reddeder; olmayan --project traceback yerine JSON ERROR/2 verir. 30 test PASS; yeni üç test eski kodda başarısız. release/store-automation package.py ile yeniden üretildi. Tek seferlik maintenance/promote.ps1 kaldırıldı (git geçmişinde), AGENTS.md güncel bakım akışına indirildi. Push ve Skills Manager dağıtımı bu commit ile yapıldı; kurulum hash sonucu commit mesajında.
