# Faz yol haritası

Bu yol haritası kurulum kapsamını ve sonraki gerçek app için kapıları ayırır.
Durum ve kanıtlar `report.json` içinde; faz adı tek başına tamamlandı demek değildir.

| Faz / amaç | İş ve dosyalar | Kabul / test | Hata / rollback | Zorluk / sonraki kapı |
|---|---|---|---|---|
| 0 Discovery | sürüm/auth/config/skill/template/Fastlane; architecture.md, skills-inventory.json | gerçek sürümler ve kaynak çağrı akışı | erişim yok → BLOCKED; salt okunur keşif, Git bundle | M; mimari 3 tur |
| 1 Core | opencode.json, üç prompt, contract, factory.py | native discovery + complete contract negative tests + tek worker | invalid config → config revert; eksik kontrat reddi | M; görev gerçek dispatch |
| 2 Handoff | canonical Brain, boot, handoff-prompt | yeni process/model mevcut dosyaları doğrular; duplicate diff yok | stale Brain/dirty/conflict → dur ve reconcile; checkpoint | M; resume kanıtı |
| 3 Persona | kontratta role/expertise/quality/tools/forbidden/failures/acceptance | eksik persona reddi, native sequential child | yanlış scope/capability → replan; kontrat commit revert | L; machine verification |
| 4 Verification | evidence digest/artifact hash + fresh reviewer + gate | missing/stale/failed/same reviewer negative checks; gerçek command/artifact | REWORK_REQUIRED; eski kanıt kullanma; code revert | H; gate PASS |
| 5 Model routing | allowlist, official Codex ChatGPT, bounded availability fallback | paid model reddi, kontrollü quota failover, gerçek free run/login | auth fail retry yok; paid route yok; checkpoint+handoff | H; ücretsiz erişim kanıtı |
| 6 Services | services.md + app-specific ADR | güncel quota/terms/security/offline/test; minimum servis | quota/outage → degraded/BLOCKED; migration ayrı task | M; app gereksinimleri |
| 7 Development | mevcut napp generator/paketler; mode regression | generated free/ads/lifetime/monthly variants analyze/test/APK; version provenance | SDK/network/invalid input → fail; izole generated workspace korunur | H; stable template gate |
| 8 Premium UI | existing themes/pages, actual screenshot suite | light/dark/phone/tablet/landscape/text scaling/48dp/contrast/accessibility | overflow/vision yok → REWORK/BLOCKED; UI revert | H; measured visual reviewer |
| 9 Release | existing AppPublishing + StorePublishMatic/Fastlane | local safe smoke lane + readiness; platform artifact/package/signature checks | account/Xcode/approval yok → BLOCKED; metadata/config backup | H; MVP ve production approval |
| 10 Resilience | timeout/classification/Brain/diff recovery | quota/timeout/auth crash fixtures; fresh resume; no retry duplicate | git conflict/corruption → stop mutation; bundle recovery | M; no silent failures |
| 11 Knowledge | kısa reviewed ADR/procedure güncellemeleri | yeni lesson gerçek test/commit'e bağlı; onaylı procedure diff | stale lesson → withdraw; version revert | L; yalnız kanıtlı bilgi |
| 12 Parallelism | gelecekte disjoint worktree/tasks | sequential pipeline production-grade + conflict/reconcile tests | race/conflict → sequential; no shared writable state | H; kullanıcı parallel karar verir |

## Bu kurulumun MVP uygulama sırası

1. Üç mimari turu ve keşif (tamamlandıktan sonra install).
2. Factory config/kontrat/skill/evidence CLI, deterministik negative test.
3. Gerçek native delegation ve fresh reviewer; resmi CLI Brain handoff.
4. Shared template root-cause fixes; free/banner/rewarded/lifetime/monthly güven kapısı.
5. Generate → analyze/test → Android debug/release artifact → runtime smoke/screenshots.
6. Safe Fastlane smoke ve mevcut yayın prosedürü bağlantısı.
7. Bağımsız whole-diff review, Brain reconcile, local checkpoint ve gerçek durum raporu.

## Dış erişimle açılacak kapılar

- GitHub CLI login/remote doğrulama ve push yetkisi; yerel commitler korunur.
- Monthly store ürünleri, resmi receipt doğrulama backend'i ve sandbox test hesabı.
- macOS/Xcode host + Apple signing/account; Windows iOS build'i tamamlayamaz.
- Android SDK lisansları hukuki kullanıcı kararı; otomatik kabul edilmez.
- Her yeni app package/monetization/backend seçimi; bu fabrikada örnek app üretilmez.
- Gerçek store publish ancak uygulama bazlı ayrı yetki; account varlığı yetki değildir.
