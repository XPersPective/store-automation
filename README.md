# AI App Factory

Gerçek kurulum ve doğrulama durumu: [rapor](docs/report.json).
Üç mimari turu/final kararlar: [mimari](docs/architecture.md).
Fazlar, başarısızlık/geri dönüş kapıları: [roadmap](docs/roadmap.md).

```powershell
cd D:\repositories\store-otomaston
.\tool\start-factory.ps1
```

OpenCode içinde `/factory-start <uygulama fikri>` ile başla;
`/factory-resume` devralır, `/factory-audit` config/skill sınırlarını denetler.
Üç rol sıralı çalışır; her ürünün monetization/backend kararı ayrıca alınır.
Bu depo fabrikanın kendisidir, şartnamedeki örnek uygulama değildir.

Factory isolated OpenCode 1.18.0 runtime kullanır. Global 1.17.18 ve ayarları
korunur; free-tier yedek endpoint 1.18.0 istiyordu. Gerekirse yeniden kurulum:

```powershell
npm install --prefix "$env:USERPROFILE\.local\share\ai-app-factory\runtime-1.18.0" opencode-ai@1.18.0 --no-audit --no-fund
python tool/factory.py audit
python tool/factory.py brain boot
python -m unittest discover -s tests -v
```

Tam görev kontratı `contracts/delegation-smoke.json` biçimindedir. Yeni işi
önce `python tool/factory.py brain new . "Görev başlığı"` ile oluştur. Kontratta
gerçek task ID, persona, scope ve doğrulanacak `verification.profile` yer alır.
`python tool/factory.py contract contracts/<gorev>.json` eksik/tehlikeli girdiyi reddeder.

Smoke kontratları bitmiş PB-001 kurulum görevini örnekler; yeni işte kopyalarını
oluşturup `brain new` çıktısındaki gerçek görev ID’sini yaz. Tamamlanmış görevler
yeniden dispatch edilmez.

Model dispatch ücretsiz whitelist'e bağlıdır. Native wrapper worker yazma iznini
yalnız kontrattaki app-source scope için açar; varsayılan deny, shell deny.
Supervisor doğrudan interaktif native task çalıştırdığında worker read-only'dir;
implementation için validated wrapper ile doğru contract scope kullanılır.

```powershell
python tool/factory.py run --provider opencode/space-bunny-free --contract contracts/delegation-smoke.json --prompt-file contracts/delegation-prompt.txt --output .factory/runs/my-run.json
python tool/factory.py run --provider opencode/space-bunny-free --fallback opencode/longcat-2.5-preview-free --contract contracts/delegation-smoke.json --prompt-file contracts/delegation-prompt.txt --output .factory/runs/my-fallback.json
```

Availability fallback checkpoint/diff doğrulamasından sonra yeni session'a geçer;
auth/generic/quality failure'da otomatik paid escalation yok. Official Codex ChatGPT
login ile `--provider codex` source-snapshot handoff/review yapar. Windows bu
oturumda Codex read-only shell'i engellediği için wrapper gerekli kaynakları exact
path/hash/content snapshot olarak verir; bu doğrudan filesystem execution kanıtı
değildir. Claude automatic fallback extra usage belirsizliği nedeniyle kapalı.

Gerçek test logları ve artifact hash'i üreten kapı:

```powershell
python tool/factory.py check --contract contracts/delegation-smoke.json --worker-session <gercek-session> --output .factory/runs/check.json
python tool/factory.py gate --contract contracts/delegation-smoke.json --evidence .factory/runs/check.json --review .factory/runs/review.json
```

Review JSON `task_id/source_digest/contract_sha256/worker_session/reviewer_session/verdict/findings`
taşır. Reviewer yeni session, verdict PASS ve findings boş olmalıdır. Gate gerçek
zorunlu komut/log/hash/artifact/source kontrolü yapar; reviewer kimliğinin güvenilir
native session kaydından gate tarafından doğrulanır. Native reviewer JSON verdict çıktısı zorunludur.
Sıradan elle yazılmış PASS gerçek review yerine geçmez. Dispatch tek process kilidiyle sıralanır; çökmeden kalan kilidi kaldırmadan önce içindeki PID kontrol edilir.

İzole yerel starter denemesi (mevcut proje üzerine yazmaz; generator build/test yapar):

```powershell
python tool/factory.py bootstrap .factory/workspaces/my_probe --name "Factory Probe" --package com.factory.probe --ads no --pro no
python tool/factory.py release-preflight .factory/workspaces/my_probe
```

Starter commit + kit commit `.factory-bootstrap.json` içinde kaydedilir. Yerel kit
override geliştirme içindir; stable source kabulü ve release öncesi verified Git ref'e
sabitleme gerekir. Yeni ürün reposu seçimi app intake sırasında yapılır; şimdilik
workspace factory altında ve kendi Git reposuyla ayrıdır. Monthly sandbox/receipt,
iOS/Xcode ve store production ayrıca kanıt/onay ister.

Release kaynak protokolü `D:/AppPublishing/README.md`; mevcut StorePublishMatic
ve Fastlane korunur. `release-preflight` preparation-only; evrensel Fastlane
dry-run değildir. Yerel smoke için `tests/fastlane` içinden
`fastlane android factory_smoke` çalışır; store/credential işlemi yapmaz.

Yedekler `C:/Users/rubicon/.local/share/ai-app-factory/backups/2026-10-10/` içinde
Git bundle. Rollback owned commit'leri revert veya repo-local factory config'i
devre dışı bırakmaktır; diğer projelerin global skill/ayarları değiştirilmedi.
Secretları repo/prompt/dart-define içine koyma; client define secret storage değildir.
