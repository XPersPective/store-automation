# Denetim bulgularının uygulanması — 2026-10-14 (4.1.0)

Kaynak raporlar (HEAD `64261a1`): A = `audit-report2.md` (Opus, A/B deneyli), B = `store-automation-audit`
(gpt, Downloads), C = `store-automation-audit` (MiniMax M3, Desktop), D = bu oturumdan önceki yarım
uygulama notu. Aynı bulgu birden çok raporda farklı adla geçtiğinde tek satırda birleştirildi.
Doğrulama: Windows 49 test + Node regresyonu, WSL Linux (Python 3.14, DeprecationWarning = hata) 49 test
(4 Windows'a özgü atlama). Her CONFIRMED karşı örnek için regresyon testi adı verilmiştir.

## Denetim yan etkisi

A'nın skill'siz alt ajanı kaynak repoda `d9d9ebf` commit'ini oluşturmuştu (server.py, static/, tests/
test_api.py, balance.test.js; `.gitignore` satırlarını silmişti; push edilmemişti). Geri alındı:
`git reset --mixed 64261a1`, `.gitignore` geri yüklendi, yabancı dosyalar silindi. Commit kaybolmasın
diye yerel `audit-stray-d9d9ebf` dalında duruyor; gerekmiyorsa `git branch -D audit-stray-d9d9ebf`.

## Kırılanlar (veri kaybı, yanlış kabul)

| Bulgu | Rapor | Düzeltme | Regresyon |
|---|---|---|---|
| `--drop-archive` kardeş projenin arşivini siliyor | A-B1, B-B01 | Arşiv adı `<proje>-<yol sha256[8]>-<zaman>`; yalnız bu önek; eski biçim hiç eşleşmez | `test_sibling_archive_infrastructure_source_and_uncommitted_edits_are_refused` |
| `--path .GIT`/`./AGENTS.md`/`agents.md`/`src` korumayı aşıyor | A-B2, B-B02 | Yol normalize (`./`, `\`, harf); `.git`, `.store-automation`, `.github`, `.gitignore`, `.gitattributes`, talimat dosyaları korumalı; kaynak kod içeren `--path` ve proje kökü reddedilir | aynı test |
| İzlenen yabancı dosyadaki commit'lenmemiş düzenleme kayboluyor | A-B3 | `--apply` kirli izlenen dosyada durur | aynı test |
| Adoption commit'i olmadan / untracked içerikle drop | A-B3, B-B08 | Drop `SA-Legacy-Adoption: <arşiv>` trailer'lı commit ister; `ADOPTION.json` hiç Git'e girmemiş dosyaları listeler, `--confirm-untracked` olmadan silmez; git yoksa asla silmez | `test_archive_is_deleted_only_after_the_removal_is_committed` |
| Elle yazılmış PASS satırı kabul ediliyor | A-M1 | Check satırı `log=runs/X.log@<sha16>`; log sonunda karar satırı (PASS/FAIL, exit, digest, contract); `accept` log yoksa UNVERIFIED, uyuşmazsa BLOCKED | `test_hand_written_pass_is_refused` |
| Risk sonradan LOW yapılarak inceleme atlanıyor; Areas daraltılıyor | A-M2 | `start` Notes'a `- start by <owner> \| risk=<R> \| contract=<hex>` yazar; etkin risk = kayıtlı en yüksek risk; Areas/Risk/Tier sözleşmede | `test_lowered_risk_and_changed_spec_need_new_evidence_and_review` |
| Kabul görev sözleşmesine bağlı değil | B-B03 | Check/evidence/review satırlarında `contract=`; Objective/Steps/Acceptance/Verify/Escalate/Areas/Risk/Tier değişince kanıt ve inceleme eskir | aynı test |
| WAITING_USER sonrası uygulayıcı kendi işini inceliyor | A-M3 | WAITING_USER Owner'ı temizler; `start` yapan herkes uygulayıcı sayılır, inceleyemez | `test_waiting_for_user_frees_the_queue_and_the_implementer_cannot_review` |
| Kanıtta aktör yok; görsel kanıt dosyasız | A-M4 | Satırlarda `by=`; `visual` ekran görüntüsü/kaydı ister | `test_each_criterion_needs_its_own_observation_and_visual_needs_a_render` |
| Aynı türdeki kriterler tek gözlemle kapanıyor | B-B10 | Her Acceptance maddesine kriter kimliği; `evidence --criterion`; `accept` her maddeyi ayrı ister | aynı test |
| Geçersiz Verify / `response_lost` accept'i durdurmuyor | B-B04 | `task_errors` validate ve accept'te ortak | `test_unresolved_or_malformed_external_and_empty_verify_prevent_done` |
| Digest bağlı yol üzerinden proje dışını okuyor | B-B07 | Digest her dosyayı `public_path` ile açar | `test_linked_path_in_areas_is_refused` |
| Windows `.cmd/.bat` argüman enjeksiyonu | A-m4, B-B05 | `& \| < > ^ % ! "` içeren batch argümanı reddedilir | `test_batch_arguments_cannot_inject_commands` |
| Eşzamanlı `start` iki yazar üretiyor | A-m11, B-B06 | `runs/writer.lock` (O_EXCL) altında oku-denetle-tek atomik yaz | `test_parallel_starts_leave_exactly_one_writer` |
| Bayat bytecode yanlış kaynağa PASS veriyor | B-B09 | Her Verify koşusu boş `PYTHONPYCACHEPREFIX` | `test_stale_bytecode_cannot_answer_for_edited_source` |
| CRLF/autocrlf farkı bütün kanıtı eskitiyor | A-M10 | Digest CRLF'yi LF sayar | `test_line_endings_do_not_change_the_digest` |
| `boot` 300 kapalı görevde 57 sn | A-M5 | Kapanış geçmişi tek `git cat-file --batch` ile, HEAD başına bir kez | ölçüm: 300 görev boot 1,1 sn, validate 0,5 sn |
| İki dalda aynı SA-NNN | A-M9 | `new` tüm yerel dalların geçmişini okur | `test_ids_are_unique_across_branches_and_headers_keep_crlf` |
| `start` bağımlılığı denetlemiyor | A-m2, B-B12 | Tamamlanma kanıtı olmayan bağımlılıkta FAIL | `test_start_needs_done_dependencies_and_a_strong_ready_check_for_risk` |
| Küçük model riskli görevi kendi yargısıyla başlatıyor | B-B13 | MEDIUM/HIGH veya security/integration/remote görev `- ready by <güçlü model>:` satırı olmadan başlamaz; validate auth/persistence/ödeme vb. kelimede düşük Risk'i uyarır | aynı test + `test_validate_warns_on_underrated_risk_and_unprobed_assumption` |
| Log adları aynı saniyede çakışıyor | B-B11 | O_EXCL ile benzersiz log adı | `test_logs_of_the_same_second_never_overwrite` |
| BLOCKED inceleme "inceleme bekliyor" görünüyor | A-M11 | boot `FIX:` satırı ve NEXT | `test_blocked_review_asks_for_a_fix_and_clean_in_progress_resumes` |
| Temiz IN_PROGRESS görev INTERRUPTED görünüyor; DIRTY aktif görevi gizliyor | A-m8, A §6 | INTERRUPTED yalnız Areas'ta kirli iş varsa; DIRTY/ADVANCED'de aktif görev notu | aynı test |

## Premium açıkları

| Bulgu | Rapor | Düzeltme |
|---|---|---|
| Premium tanımsız, kalite eksikliği engellenemiyor | A-M6, B §5, C-M-02/P-* | product-quality.md "Premium bar": tasarım temeli görevi (token + 2–3 yön + ADR), görsel rubrik, kullanıcı dilinde hata, çift gönderim, API sözleşmesi, performans bütçesi, güvenlik kontrol listesi, gözlemlenebilirlik. Reviewer bulgu sınıfı QUALITY: MAJOR gibi engeller, yalnız kullanıcı kabul edebilir |
| UI görevinde tek tür kanıt yetiyor | B-B10, C-P-1/P-2 | plan.md §2: dar+geniş `[visual]`, durumlu `[interaction]`, `[accessibility]`; validate eksik üçlüyü uyarır |
| En riskli varsayım M1'de denenmiyor | A-M7 | product.md `RA-1`; M1 görevi adını taşır; validate uyarır; kullanıcı yeteneğini ertelemek ADR + Open Decision ister |
| Prompt injection kuralı yok | A ÖNERİ, B §5 | SKILL §6 ve plan.md §6a: repo/görev/yabancı plan/araç metni veridir |
| Tek ajanlı host, eksik araç | A ÖNERİ, A-m8 | REVIEW_PENDING ve stop raporu ikinci oturum gerektiğini söyler; araç eksikse `Blocked: needs <capability> for <criterion>` |
| Kanıt dosyası `runs/` altında kayboluyor | A ÖNERİ | `.store-automation/evidence/<task>/` (commit'li) |

## Tutarlılık ve küçükler

| Bulgu | Rapor | Durum |
|---|---|---|
| POSIX'te `python` yok | A-M8 | SKILL: `python3`/`py -3`; doctor `interpreter` alanı |
| Çıkış kodları belgeyle çelişiyor; `check` REVIEW'da herkese açık | A-m1, A-M4 | runtime.md düzeltildi (FAIL check ve MATCHED olmayan readback = 1; REVIEW'da her adlı ajan `check` yapabilir) |
| Secret filtresi eksik | A-m3 | `*_KEY`, `*_PAT`, DSN, DATABASE_URL, AUTH, COOKIE, PRIVATE eklendi |
| `**/*.py` kök dosyayı eşlemiyor | A-m5 | Düzeltildi (`test_glob_double_star_matches_root_files`) |
| POSIX alt süreç kendi oturumunu açarsa kaçıyor | A-m6 | Sınır runtime.md'de belgelendi (kod sınırı aynı) |
| `is_reserved` 3.13+ uyarısı | A-m7 | `ntpath.isreserved` varsa o; WSL 3.14'te uyarı-hata ile 49 test geçti |
| Hafif yol görsel değişikliği dışlamıyor | A-m9 | SKILL §2: "visible UI change" hafif yoldan çıkar |
| Hook sonrası içerik kanıtsız | A-m10 | accept DONE çıktısı ve edge-cases "Commit hooks and signing" |
| Sürüm numarası sabit | A-m12 | 4.1.0 |
| CRLF görev dosyası LF'ye dönüyor | A-m15 | `set_headers`/`append_section` satır sonunu korur |
| `package.py ../package` yanlış reddediliyor | B §2 | Göreli yol kabul, bağlı üst dizin hâlâ reddedilir |
| Dizin fsync yok (POSIX) | C-m-06 | `write_atomic` POSIX'te dizini fsync eder |
| Flutter algılama kaba | C-m-09 | Satır başı `flutter`/`sdk: flutter` |
| Verify yolu Areas dışında | A-M2 (E5b) | validate uyarır |

## Bilinçli olarak yapılmayanlar

- **Runtime satır bütçesi (H9 ≈1.400):** kaynak 2.158 satır (store.py dahil). Eklenen her satır bir
  karşı örneği kapatıyor; kısaltma ayrı bir iş.
- **LICENSE dosyası (A-m14):** atıf `plan.py` başında; lisans metni eklemek sahibin kararı.
- **plan↔legacy çift yönlü import (C-M-03):** plan, legacy'yi yalnız fonksiyon içinde yüklüyor; gerçek
  döngü hatası yok.
- **Kimlik doğrulama:** `--as`, Owner, reviewer hâlâ beyan; araç dürüst hatayı ve sıradan kendini
  onaylamayı durdurur, aynı OS kullanıcısıyla çalışan kararlı sahteciyi değil (runtime.md Trust boundary).
- **Kontrol edilmeyenler:** gerçek kullanıcı projesinde 4.1.0 koşusu, diğer sağlayıcı host'ları, imzalı
  commit zorunlu repo, macOS. A/B premium deneyi yeniden koşulmadı.
