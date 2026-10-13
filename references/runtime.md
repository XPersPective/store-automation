# Çalışan küçük araç seti

Python 3.11+ standart kitaplığı yeterlidir. `<skill>` bu SKILL.md'nin bulunduğu klasördür; çalışma dizini seçilen uygulama olur. Kurulu araç eski depoya, Brain'e veya belirli bir sağlayıcıya import yapmaz.

```powershell
python "<skill>/store.py" --project "<uygulama>" doctor
python "<skill>/store.py" --project "<uygulama>" check --request checks.json
```

`checks.json` örneği: `{"argv":["python","-m","unittest","discover","-s","tests"],"inputs":["app.py","tests/test_app.py"],"timeout":120}`. Windows'ta `npm`/`flutter` gibi .cmd/.bat araçları PATH'ten çözülür; `./gradlew` gibi göreli script proje kökünden çalışır. Argümanlara kabuk metni koyma. Komutu yönetici gerçek projedeki akışı inceleyerek seçer; worker çıktısından komut çalıştırılmaz. Inputs listesi kontrolün etkilediği tüm public kaynak/sözleşme/test/config dosyalarını kapsar. Büyük projede listeyi elle yazma; örn. `git ls-files lib test pubspec.yaml` çıktısından üret, secret/imza dosyalarını çıkar (kalırsa snapshot okumadan reddeder). Bir dosyanın değişmediği kanıtı listelenmeyen dosyalar için geçerli değildir. Secret dosyalarını ekleme. Araç gizli ortam değişkenlerini süzer ama aynı OS kullanıcısına karşı sandbox değildir.

CLI her komutta JSON döndürür: başarılı işlem 0, BLOCKED/UNVERIFIED/başarısız check 1, bozuk istek 2. `doctor` yalnız Python/paket erişimidir; sağlayıcı veya ürün kabulü değildir. Küçük mekanik işlerde bu araç bile zorunlu değildir: mevcut ilgili test ve kısa sonuç yeterlidir.

## Görev ve native ajan

`task` komutuna verilen JSON alanları: `id`, `project` (gerçek uygulama yolu), `objective`, `acceptance_scope`, `scope`/`out_of_scope` metin listeleri, `risk` LOW/MEDIUM/HIGH, `permissions` (`write` boolean, `paid_api:false`, `production:false`), `independent_review` boolean, `criteria` listesi. Her kriter `id`, `description`, `required` boolean ve `kinds` listesine sahiptir. Türler: machine, interaction, visual, accessibility, security, integration, artifact, remote, user_feedback. MEDIUM/HIGH bağımsız inceleme ister. Çıktı `status: VALID`, gözlem/inceleme kayıtlarında kullanılacak `task_hash` ve görevin kendisidir; sonraki isteklere `task` alanını ver, sarmalayıcı nesneyi değil. Dış yayın yetkisi bu yerel görevden türetilmez.

`prepare` isteği: `task` nesnesi, `role`, `actor` (gerçek native atama kimliği), `files` listesi; varsa `provider`, `model`, `effort`, `enforced_scope`. Host kimliği ancak başlatma sonucunda geliyorsa önce görev ve input snapshot'ını kaydet; gelen kimliği bağla ve worker'a başlangıç snapshot'ını doğrulatmadan yazdırma. Kimlik veya model uydurma. `prepare` kendi başına ajan başlatmaz. Mevcut host'un gerçek delegation aracını kullan, sonuç/kimliği araçtan gözle; brief'e görev, izin ve süre sınırını ekle. Host yeteneği yoksa bağımsız inceleme UNVERIFIED kalır.

`finish` isteği: `assignment_ref` (prepare'in döndürdüğü path/sha256), `report`, `output_files`, `native_reference`, `observed_actor`, `observed_state`, `observer`. Report atamadaki task/project/attempt/role/provider/model/effort ile aynıdır; ayrıca `state`, `changed_files`, `evidence`, `blockers`, `next_action` ve ölçülmüşse `usage` içerir. Hatalı veya kota nedeniyle yarım bitmiş ajan COMPLETED olamaz. Final çıktı input'tan ayrı hashlenir; read-only/reviewer input değişimini kabul etmez.

## Dosyaya bağlı kabul

Kayıtlar `.store-automation/runs/` altında yeni, benzersiz JSON dosyalarıdır. Git'e ekleme. `record` yalnız `observation` veya `review` kategorisinde `{"category":"observation","value":{...}}` kaydı saklar; check/outcome/acceptance yalnız kendi komutlarından (check/finish/gate) doğar; doğruluk veya köken vermez. Yerel dosyayı başka program değiştirebilir; SHA yalnız referansın değişmediğini gösterir.

`gate` isteği `bundle` ve **yönetici tarafından ayrı hazırlanmış** `attestations` içerir. Worker raporundaki attestation/provenance alanlarını güvenilir kabul etme.

- Bundle: `task`, `source` (snapshot sonucu), `implementation` (finish referansı), `observations` referans listesi; gerekliyse `reviewer` finish referansı ve `review` referansı.
- Observation: `id`, `task`, `project`, `task_hash`, `subject`, `criterion`, `kind`, `result` PASS/FAIL/UNVERIFIED/NOT_APPLICABLE, `reference`, `evidence` (hashli public kanıt kaydı), `observer`, `method`, `environment`, `captured_at`. Zorunlu kriter N/A yapılamaz. Makine kanıtında gerçek check kaydı gerekir; ekran için ekranı gerçekten görmüş olma ve dosya hashli gözlem gerekir. Evidence kaydındaki `artifacts` alanı `snapshot` sonucudur (ör. ekran görüntüleri); gate bu dosyaları yeniden hashler. `visual` gözlemde `artifacts` zorunludur.
- Review: `task`, `project`, `task_hash`, `subject`, `attempt`, `criteria`, `verdict` PASS/BLOCKED/UNVERIFIED, `findings`. Her açık bulgu description/severity/violates içerir. Yalnız kriter ihlali olmayan MINOR, accepted disposition, reason ve decision_owner ile kabul edilebilir. Düzeltme sonrası taze inceleme gerekir.
- Yönetici attestation: `record` referansı, `observer`, `method`, `native_reference`, `observed_at`; outcome için araçtan görülen `actor` ve `state`. Yönetici native kaydı gerçekten açar; task/attempt/parent ilişkisi, rol ve son çıktı eşleşmesini kontrol eder. Sahte transcript otomatik doğrulanamaz. Bir host bunu sağlayamıyorsa attestation yazılmaz.

Gate güncel kaynak ve kanıt dosyalarını yeniden hashler, task/atama/sonuç/rapor bağlarını ve kriterleri denetler. ACCEPTED yalnız belirtilen kapsam ve yönetici gözlem güveni içindir. Farklı dosyaya aynı metni yazmak native authentication sağlamaz. Yeni requirement/kod sonrası eski bundle kullanılamaz; yeni snapshot ve etkilenmiş gözlemler gerekir. Referanslar ve alanlar için `runtime/` işlev imzaları tek çalıştırılabilir kaynaktır; `tests/test_gate.py` yalnız sentetik format örneğidir.

## Devam ve yayın

`legacy`: istek dosyası yok. Varsayılan dry-run; `--apply` 2.x `.factory/` ve `.factory-bootstrap.json`'u proje dışı arşive taşır (ayrıntı [geçiş](migration.md)). `doctor` çıktısındaki `legacy` alanı bu izleri gösterir.

`handoff`: `task_ref`, `assignments` referansları, `next_action`, `ownership` (state active/absent/unknown + reference), `pending_external` (state not_started/confirmed/response_unknown + readback), `public_files`, `notes`. `task_ref` ve bütün `assignments` aynı task/task_hash/project kaydına ait olmalıdır. Canlı/bilinmeyen owner önce uzlaştırılır; belirsiz dış işlem önce geri okunur. Handoff hiçbir süreci öldürmez veya upload'ı tekrar etmez. Yer değişikliğinde eski project-bound receipt'i düzenleyerek yeniden kullanma; geçmiş olarak koru, yeni kökte yeni atama/gözlem üret.

`usage`: `attempts` ve `expected_ids`. Yalnız disjoint_last_turn input_tokens/output_tokens sayılır; eksik parent/worker/retry varsa toplam null. Kota değişimi token değildir.

`release-readback`: `expected` ve `observed` nesneleri; platform/account/app/channel/version/artifact_sha256/state eşleşir. Observed ayrıca readback_reference/observed_at/provenance, AVAILABLE için availability_reference ister. Bu komut store'a bağlanmaz; yönetici gerçek native Fastlane/store sonucunu gözler ve güncelliğini kontrol eder. Üretim gönderimini mevcut yetkili yayın düzeni yapar; bu skill ikinci uploader kurmaz.
