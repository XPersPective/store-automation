# Store Automation 4

Uygulama fikrini veya mevcut projeyi, herhangi bir ajanın yalnız repodan devralabileceği git tabanlı bir planla ürüne ve yayına götüren skill. Güçlü model ürünü, mimariyi ve risk sıralı aşamaları kurar; küçük modeller tam tarifli görevleri uygular; her görev güncel kaynağa bağlı kanıt ve gerektiğinde bağımsız inceleme olmadan kapanmaz. Project Brain'in plan/devam/harita mekanizması bu skill'e alındı; başka skill'e bağımlılık yoktur.

Güncel durum: [HANDOFF.md](HANDOFF.md). Hedef ve mimari: [design/v4-target.md](design/v4-target.md). Kanıtlar: [design/validation-report.md](design/validation-report.md).

## Kullanım

Kurulu host'ta `$store-automation` ile uygulama fikrini veya mevcut projeyi belirt; "devam et" kalınan yerden sürdürür. Ajanlar ilk iş `store.py boot` çalıştırır. Projedeki durum `.store-automation/` altında git'e girer (product, current, tasks, decisions); yalnız `runs/` logları git dışıdır.

```powershell
python store.py --project "D:/path/to/app" doctor
python store.py --project "D:/path/to/app" boot
python -m unittest discover -s tests -v
node tests/reference-ui-check.cjs
```

Son iki komut bu kaynak deponun kontrolleridir; uygulama kabulünün yerine geçmez. Komutlar ve dosya biçimi: [runtime](references/runtime.md); protokol: [SKILL.md](SKILL.md) ve [plan](references/plan.md). [Referans demo](examples/reference/README.md) HTTP/SQLite ve browser akışını sentetik veriyle gösterir.

## Başka yapay zekaya devir

> Bu klasördeki AGENTS.md ve HANDOFF.md'yi oku. HANDOFF'taki ilk açık işi gerçek dosya ve design/v4-target.md kabul ölçütleriyle sürdür. Eski Brain veya factory talimatlarını bu deponun yönetim kuralı sayma. Bilinmeyen kullanıcı işi, Git geçmişi ve geri dönüş yedeğini koru. Tamamlanmış işi tekrar kurma, bilinmeyen kanıtı PASS yapma. Üretim mağaza yayını ve ücretli API bu yetkinin parçası değildir.

Kaynak: SKILL.md, references/, runtime/, store.py. Geliştirme: design/, tests/, examples/, package.py. Paket `python package.py <yeni-boş-hedef>` ile üretilir. release/store-automation yayımlanmış pakettir; elle düzenlenmez. [Sürüm geçişi](references/migration.md) 2.x/3.x ve Project Brain projelerinin devralınmasını açıklar.

Kurulu kopyaların byte eşleşmesi gerçek sağlayıcı görevi çalıştığını kanıtlamaz. Android/iOS/Windows/web yayını her ürünün seçilmiş hedefinde ayrıca doğrulanır.

## Lisans

MIT, telif © 2026 XPersPective ([LICENSE](LICENSE)); dağıtılan pakete de dahildir.

## Kaynak ve dağıtım düzeni

Tek aktif geliştirme ve GitHub varsayılan dalı **master**. Skills Manager güncellemeleri master dalındaki release/store-automation paketinden alır. Kurulu skill yalnız SKILL.md, store.py, LICENSE, runtime/, references/ ve paket hash manifestini içerir. design/, examples/ ve tests/ kaynak deponun geliştirme/doğrulama belgeleridir; ajanlara dağıtılmaz. Eski sistem, dallar ve geçici kanıtlar repo dışında D:/repositories/store-automation-backup-20261014 altında korunur.
