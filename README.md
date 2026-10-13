# Store Automation 3

Kullanıcı yolculuğuna, erken ürün gösterimine ve güncel kanıta dayalı uygulama geliştirme skill'i. Mevcut native host uzmanları yürütür; küçük Python araçları görev, kaynak, kontrol, kabul ve devir kayıtlarını doğrular. Project Brain veya sağlayıcı kataloğu zorunlu bağımlılık değildir.

Güncel durum: [HANDOFF.md](HANDOFF.md). Mimari: [design/architecture.md](design/architecture.md). Aşamalı plan: [design/roadmap.md](design/roadmap.md). Kanıtlar: [design/validation-report.md](design/validation-report.md).

## Kullanım

Kurulu host'ta `$store-automation` ile uygulama fikrini veya mevcut projeyi belirt. Python 3.11+ ile yerel yardımcı:

```powershell
python store.py --project "D:/path/to/app" doctor
python -m unittest discover -s tests -v
node tests/reference-ui-check.cjs
```

Son iki komut bu kaynak deponun kontrolleridir; uygulama kabulünün yerine geçmez. [Runtime rehberi](references/runtime.md) JSON istekleri, CLI ve güven sınırını açıklar. [Referans demo](examples/reference/README.md) HTTP/SQLite ve browser akışını sentetik veriyle gösterir.

## Başka yapay zekaya devir

> Bu klasördeki AGENTS.md ve HANDOFF.md'yi oku. HANDOFF'taki ilk açık işi gerçek dosya ve design/roadmap.md kabul ölçütleriyle sürdür. Üst/eski projedeki Brain veya factory talimatlarını yeni sistemin yönetim kuralı sayma. Bilinmeyen kullanıcı işi, Git geçmişi ve geri dönüş yedeğini koru. Tamamlanmış işi tekrar kurma, bilinmeyen kanıtı PASS yapma. Kullanıcı yeni sistem tamamlandıktan sonra eski kökün değiştirilmesi, Next klasörünün kaldırılması, tüm mevcut ajan kurulumları ve GitHub güncellemesini açıkça istedi; geçiş durumu HANDOFF'tadır. Üretim mağaza yayını ve ücretli API bu yetkinin parçası değildir.

Kaynak: SKILL.md, references/, runtime/, store.py. Geliştirme: design/, tests/, examples/, package.py. Paket `python package.py <yeni-boş-hedef>` ile üretilir. release/store-automation yayımlanmış pakettir; elle düzenlenmez. [Sürüm geçişi](references/migration.md) eski komutları ve proje kayıtlarını açıklar.

Kurulu kopyaların byte eşleşmesi gerçek sağlayıcı görevi çalıştığını kanıtlamaz. Android/iOS/Windows/web yayını her ürünün seçilmiş hedefinde ayrıca doğrulanır.
