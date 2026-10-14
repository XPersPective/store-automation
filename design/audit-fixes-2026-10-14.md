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

## İkinci tur (4.1.1): kısmi kalanlar ve küçük öneriler

| Bulgu | Rapor | Düzeltme | Regresyon |
|---|---|---|---|
| `runs/` süresiz büyüyor | A §7 | Her `check` budar: açık görevin andığı log kalır, diğerleri 14 gün sonra, 200'ü aşan en eskiler hemen silinir | `test_runs_stay_bounded_but_cited_logs_survive` |
| Etkileşim kanıtı yalnız notla | A-M4 | `[interaction]` için `--file` ya da `adım -> adım -> sonuç` notu | `test_interaction_needs_a_recording_or_the_steps_and_ids_are_plain` |
| Hook sonrası commit kanıtsız | A-m10 | boot en yeni DONE commit'inin Areas baytlarından digest'i yeniden hesaplar, farkı uyarır | `test_boot_flags_a_commit_that_differs_from_the_accepted_bytes` (temiz commit'te uyarı yok) |
| RA-1 denetimi yalnız uyarı | A-M7 | `validate` FAIL | `test_validate_warns_on_underrated_risk_and_unprobed_assumption` |
| ADR biçim kayması | B-B13 | `validate` Status/Problem/Evidence/Options/Choice/Impact eksikliğini uyarır | `test_adr_shape_is_checked_and_plan_never_imports_legacy` |
| plan↔legacy çift yönlü import | C-M-03 | Yabancı sistem tablosu plan.py'de; legacy tek yönlü kullanır | aynı test |
| `--as`/`--owner`/`--reviewer` gevşek | C-m-07 | Tek satır, en çok 80 karakter, harf/rakam/boşluk ve `. : @ / + - _` | `test_interaction_needs_...` |
| Aynı saniyede arşiv adı | C-m-05 | Arşiv damgası mikro saniyeli | — |
| release-readback alanları | C-m-08 | Metin alanları tek satır, yazdırılabilir, ≤500 karakter | `test_release_exit_success_cannot_replace_exact_remote_readback` |
| Genel build önbelleği | B-B09 | plan.md: Verify güncel kaynağı çalıştırır, bayat `dist/` değil | belge |
| Backend kanıtı eksik | B §5 | Premium bar "Backend proof": aktör/kaynak yetkisi, aynı anahtarla eşzamanlı tekrar, commit sonrası kayıp yanıt, depolama hatası, yeniden başlatma, migration/rollback | belge |
| Tasarım yönü ve sapma | B §5, C-P-7/P-10 | ADR yönü ve token kaynağını adlandırır; render seçilen yönle karşılaştırılır; sapma Notes'ta gerekçeli | belge |
| MEDIUM+ yeni bileşen için seçenekler | C-P-8 | plan.md §6 Directions | belge |
| İnceleme ve izleme örnekleri | C-o-2, C-o-6 | plan.md §8 `review` örneği, §6a izleme satırı örnekleri | belge |
| Büyütülmüş metin / klavye | B §5 | `[accessibility]` maddesi aynı yolculuğu klavye ve büyük metinle ister | belge |
| design §4 boot durumları | A §6 | v4-target.md uygulanan durumlara göre düzeltildi | belge |
| Sürüm/içerik kayması | A-m12, A §I | SKILL.md ve store.py sürümü testle eşit tutulur | `test_version_is_one_number` |
| LICENSE | A-m14 | MIT, © 2026 XPersPective; pakete dahil | `test_standalone_package...` |
| Global talimat kalıntıları | C-o-4 | Doğrulandı: `~/.codex/rules/default.rules`, `~/.codex/v2/default.rules`, `~/.codeium/windsurf/memories/global_rules.md`, `~/.clinerules` hâlâ Project Brain'i yüklüyordu; yedeklenip store-automation kuralına çevrildi (yedek: `store-automation-backup-20261014/brain-residue-*`). CLAUDE/Codex/Gemini/OpenCode/Qwen/Cursor/Kiro/Trae temiz | tarama |

Yeniden kontrol: Windows 54 test + Node, WSL Linux 54 test (4 atlama), 300 görevde boot 1,0 sn, paketlenmiş
CLI ile uçtan uca akış (READY kontrolü → check → kendi incelemesi reddi → bağımsız inceleme → DONE → Task
Master devralma → arşiv silme → temiz boot).

## Bilinçli olarak yapılmayanlar

- **Runtime satır bütçesi (H9 ≈1.400):** kaynak 2.227 satır (store.py dahil). Her ek satır bir karşı örneği
  kapatıyor; bütçeye indirmek davranış kaybı demek. Hedef rakamı güncellenmeli ya da ayrı sadeleştirme işi.
- **Boot özet modu (C-o-5):** boot zaten 25 açık görev ve sınırlı listelerle kesiliyor.
- **`git ls-files` akışla okuma (C-m-10):** binlerce dosyada bile bellek farkı ihmal edilebilir.
- **Tier H için asgari kanıt sayısı (C-P-6):** Tier yürütme zorluğu, kalite değil; kalite kanıtı UI üçlüsü
  ve Premium bar ile isteniyor.
- **READY kontrolünün anlamı (B-B13):** araç `ready by` satırının varlığını denetler, içeriğini değil.
- **Kimlik doğrulama:** `--as`, Owner, reviewer beyandır; kararlı sahteciyi durdurmaz (runtime.md Trust boundary).
- **Bu ortamda yapılamayanlar:** gerçek kullanıcı projesinde koşu, diğer sağlayıcı host'ları, macOS,
  imzalı commit zorunlu repo, A/B premium deneyinin yeniden koşusu.
