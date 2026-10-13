# Store Automation 4 — hedef, tasarım brief'i ve mimari

Durum: TASARIM. Kod yazılmadı. Kullanıcı 2026-10-14'te Project Brain'in gereken kısımlarını store-automation'a sentezlemeyi, plan dosyalarının git'e girmesini ve alt ajanlı devralma denemesini onayladı. Bu belge onaylanınca roadmap'in tek kaynağıdır; ilerleme HANDOFF'tadır.

## 1. Hedef — bittiğinde ne elde etmiş olacağız

**Tek cümle:** Kullanıcı bir uygulama fikri veya mevcut proje verdiğinde store-automation, güçlü modelle doğru ürünü ve mimariyi planlar, işi küçük modellerin de yürütebileceği doğrulanabilir görevlere böler, her görevi gerçek kanıtla kabul eder, herhangi bir anda kesilen işi herhangi bir ajanın yalnız repodan doğru yerden devralmasını sağlar ve seçilen platformda yayına kadar götürür. Tek skill; başka skill'e, servise, daemon'a veya git dışı hafızaya bağımlı değildir.

**Başarı koşulları** (her biri gözlenebilir; P6 denemesi bunları ölçer):

| # | Koşul | Nasıl gözlenir |
|---|---|---|
| H1 | Sıfırdan başlangıç | Boş repo + fikir → Genesis sonunda commit'lenmiş: kullanıcının sözleriyle hedef, kullanıcı/yolculuk/platform, risk sıralı milestone'lar, ilk milestone'un tam tarifli görevleri. Sohbet geçmişi olmayan ajan ilk görevde belirsizlik bulamaz. |
| H2 | Soğuk devralma | Görev ortasında oturum kesilir. Başka (daha küçük) model yalnız "devam et" + repo ile doğru görevi, adımı, kirli dosyaları ve bekleyen dış işlemi bulur; biten işi tekrar etmez, kullanıcı işini bozmaz. |
| H3 | Dürüst "bitti" | Hiçbir görev Acceptance'taki kanıt türleri güncel kaynakla eşleşmeden DONE olmaz. MEDIUM/HIGH görev, uygulayıcıdan farklı ajanın incelemesi olmadan DONE olmaz. Kanıt özeti git'te kalır. |
| H4 | Hafif yol | Davranış değiştirmeyen küçük iş: plan dosyası yok, tek commit, tören yok. |
| H5 | Devralma (adoption) | Planı olmayan, 2.x `.factory` veya `.project-brain` taşıyan proje → kullanıcı işi kaybolmadan harita, doğrulanmış komutlar ve plan. |
| H6 | Dış işlem güvenliği | Yanıtı kaybolan upload/submit, geri okuma yapılmadan asla tekrarlanmaz; boot bunu ilk iş olarak gösterir. |
| H7 | Model ayrımı | Her görev Tier taşır. Tier H iş (mimari, spec, inceleme) küçük modele düşmez; küçük modelin işi REVIEW kuyruğunda güçlü modeli bekler. |
| H8 | Kendine yeterlilik | Yalnız bu skill + Python 3.11 + git. Ağ, ücretli API, ek paket yok. Windows ve POSIX. |
| H9 | Küçüklük | SKILL.md ≤ 90 satır; runtime ≤ ~1.400 satır; her referans yalnız gerektiğinde okunur. |

**Hedef dışı:** genel ajan orkestrasyon platformu, scheduler/daemon/dashboard, her sağlayıcının alt ajan API'sini sürmek, yetkisiz mağaza yayını, ticari başarı garantisi, kriptografik kimlik doğrulama.

## 2. Tasarım brief'i (her aday mimariye verilen prompt)

> Sen bir skill mimarısın. Aşağıdaki hedefi (§1) karşılayan store-automation 4 mimarisini öner. Önerin şu brief'e göre eleştirilecek; karşılamadığın her madde bir sonraki turda düzeltilecek.
>
> **Aktörler:** (1) Kullanıcı: amacı ve kritik ürün kararlarını verir, çoğu zaman yoktur. (2) Güçlü model: Genesis, mimari, spec yazımı, inceleme, plan değişikliği. (3) Küçük model: tam tarifli görevi uygular, tasarım uydurmaz. (4) Bağımsız inceleyici: uygulayıcıdan farklı oturum. Hepsi farklı sağlayıcılardan olabilir ve sohbet geçmişi paylaşmaz.
>
> **Sert kısıtlar:** Durum yalnız repodaki dosyalar ve commit'lerdedir; sohbet ve git dışı yerel dosya hafıza değildir. Python stdlib + git. Bilinmeyen kullanıcı işi korunur; force-push, reset, clean yok. Credential okunmaz/aktarılmaz; ücretli API yok. Her yazım çökmeye dayanıklıdır (yarım dosya tek kaynak olmaz). Windows ve POSIX.
>
> **Kalite öncelik sırası:** 1) devralmanın doğruluğu, 2) "bitti"nin dürüstlüğü, 3) küçük işte düşük tören, 4) küçük modelin yürütebilmesi, 5) ürün kalitesi (erken gösterim, yolculuk, platform kanıtı), 6) bakım kolaylığı ve küçüklük.
>
> **Karşılanacak senaryolar:** sıfırdan ürün; görev ortasında kesinti; model/sağlayıcı değişimi; kota bitmesi; kirli çalışma ağacı ve başkasının değişikliği; merge çakışması; kullanıcı yok ve karar bekleniyor; kullanıcı akışı/hedefi değiştiriyor; yalnız görsel geri bildirim; küçük düzeltme; güvenlik/veri içeren küçük diff; yayın sırasında yanıt kaybı; paralel ajanlar; git'siz klasör; mevcut projeyi devralma; tek ajanlı host'ta bağımsız inceleme.
>
> **Yasak kalıplar:** iki ayrı hafıza; worker'ın kendi PASS/köken beyanını kabul; yalnız sohbette kalan karar; her küçük işe tören; runtime'ın belirli ID formatına/başka skill'e bağlanması; model tarafında yapılabilecek mekanik muhasebeyi modele bırakmak.
>
> **Teslim:** dosya şeması, görev yaşam döngüsü, komutlar, kanıt bağlama yöntemi, devralma algoritması, model ayrımının mekanizması, eski sistemden geçiş ve her senaryonun nasıl karşılandığı. Bilinen sınırları açık yaz.

## 3. Öner → eleştir döngüsü

### Tur 1 — "Brain olduğu gibi + mevcut store katmanı"

Öneri: `.store-automation/` altında Brain'in dosyaları (current/target/tasks/decisions/config); mevcut runtime (task/prepare/finish/record/gate/handoff JSON akışı) aynen kalır.

Eleştiri:
- **İki hafıza kalıyor:** görev dosyasındaki Resume ile `runs/handoff-*.json` aynı şeyi iki yerde tutar; yasak kalıp.
- **Kanıt yerel kalıyor:** gate kayıtları git dışında; H3'ün "git'te kalır" şartı tutmaz.
- **Tören:** gate için 6 JSON isteği ve elle `task_hash` kopyalama gerekir; küçük model bunu yapamaz (bu oturumda 60 satırlık script gerekti). Pratikte hiç kullanılmaz.
- **Çift sözlük:** JSON `criteria/kinds` ile görevdeki Acceptance kutuları ve iki ayrı risk alanı aynı bilgiyi tekrarlar.

Sonuç: reddedildi.

### Tur 2 — "Görev dosyası tek birimdir"

Öneri: Bir iş hakkında her şey tek görev markdown'ında: amaç, Tier, risk, adımlar, türlü Acceptance (`- [ ] [interaction] …`), Verify, Evidence, Resume. JSON görev/atama akışı kalkar. Kanıt satırları görev dosyasına yazılır, commit ile git'e girer. `runs/` yalnız ham log (git dışı).

Eleştiri:
- **Bağımsızlık kayboldu:** eski sistem atama/çıktı/inceleyici bağını tutuyordu; yeni öneride "kim uyguladı, kim inceledi" yok → kendi işini onaylama açığı.
- **Eskimiş kanıt:** eski sistem dosya hash snapshot'ı tutuyordu; yeni öneride kanıtın hangi kaynağa ait olduğu yok.
- **Dış işlem serbest metinde:** Resume'daki "upload belirsiz" cümlesini boot makine olarak göremez; H6 tutmaz.
- **Ürün katmanı yok:** yolculuk, platform, en riskli varsayım nereye yazılıyor belirsiz.
- **Markdown kırılganlığı:** küçük model satır formatını bozarsa veri sessizce kaybolur.

Sonuç: yön doğru, beş açık var.

### Tur 3 — açıkları kapat

Öneri:
- **Kim yaptı/kim inceledi:** görev başlığında `Owner:` (uygulayan ajan/model). Uygulama commit'inde `SA-Agent`, inceleme commit'inde `SA-Reviewer` trailer'ı. Yeni durum **REVIEW**: MEDIUM/HIGH görev uygulandıktan sonra DONE'a değil REVIEW'a geçer; ancak `Owner`'dan farklı bir ajanın `## Review` bölümü PASS verince DONE olabilir.
- **Kanıt bağlama:** `check` komutu görevin Verify komutlarını çalıştırır; görevin `Areas` glob'larına ve proje manifestlerine uyan dosyaların içerik özetini (areas digest) hesaplar ve Evidence'a tek satır olarak **kendisi** yazar. `accept` özeti yeniden hesaplar; farklıysa kanıt eskidir. Elle `inputs` listesi gerekmez.
- **Dış işlem yapısal:** görevde `## External` bölümü, sabit satır biçimi `- <işlem> | <durum: not_started/sent/confirmed/response_unknown> | readback: <nasıl>`. Boot `response_unknown` görürse durumu `READBACK_FIRST` yapar.
- **Ürün katmanı:** `product.md` (Brain target'ının yerine): Goal (kullanıcının sözleri), Status DRAFT/CONFIRMED, kullanıcılar, ana yolculuklar, platformlar, gözlenebilir başarı koşulları (kanıt türüyle), en riskli varsayımlar, hedef dışı, açık kararlar.
- **Kırılganlık:** küçük ve katı gramer; `validate` her commit öncesi; mekanik satırları (Evidence, durum geçişleri) araç yazar, model değil.

Eleştiri:
- **REVIEW tek ajanlı host'ta kilitlenir mi?** Hayır, iş kaybolmaz: görev REVIEW'da bekler, boot onu "güçlü model incelemesi bekleyen" diye gösterir. Kullanıcı güçlü bir modelle oturum açınca ilk iş bu kuyruktur. Bu, model ayrımının doğal mekanizmasıdır (H7). Kabul.
- **Areas digest yanlış kapsam:** test Areas dışında kalırsa kanıt eksik bağlanır. Önlem: Verify'ın dokunduğu test yolları Areas'a eklenmeli; `validate` Verify'da geçen proje yolu Areas'ta değilse uyarır. Sınır belgelenir.
- **Commit zamanlaması:** check, commit'ten önce çalışır; digest çalışma ağacından hesaplanır, commit aynı içeriği taşır. Accept, commit sonrası da aynı digest'i hesaplayabilir. Git'siz klasörde aynı digest dosya okumasıyla çalışır; checkpoint yoktur, uyarı verilir.
- **Kimlik beyanı:** `Owner/SA-Agent/SA-Reviewer` ajanın kendi beyanıdır; kriptografik değildir. Eski JSON attestation sistemi de aynı güven düzeyindeydi (yönetici beyanı). Dürüst sınır olarak yazılır; ek tören eklenmez.
- **Eski JSON çekirdeği ne olacak?** `task/prepare/finish/record/snapshot/gate/handoff/usage` görev dosyası modeli içinde tekrardır. Değerli kuralları `accept` içine taşınır (zorunlu kriter N/A olamaz, FAIL engeller, bulgu severity kuralları, inceleyici ≠ uygulayıcı, eskimiş kanıt). Komutlar kaldırılır. `check` (ProcessTree ile), `release-readback`, `legacy`, `doctor` kalır.

### Tur 4 — son baskı testi (senaryo bazında)

| Senaryo | Karşılayan mekanizma | Kalan risk |
|---|---|---|
| Sıfırdan ürün | Genesis: map → init → product.md görüşmesi → risk sıralı milestone'lar (M1 en riskli varsayım + erken gösterim, M2 uçtan uca yolculuk, M3 genişletme, M4 platform yayını) → ilk milestone tam tarif → yürütülebilirlik denemesi | Görüşme kalitesi modele bağlı; soru listesi şablonla sınırlanır |
| Görev ortasında kesinti | `Status: IN_PROGRESS` + `## Resume` (Next/Failing/Dirty) + boot INTERRUPTED; "Bitirmeden önce Resume yaz ve WIP commit" kuralı | Model Resume yazamadan çökerse boot diff'ten ve işaretsiz Acceptance'tan başlar |
| Model/sağlayıcı değişimi | Durum dosyada; Tier; boot çıktısı yüklenecek dosyaları listeler | — |
| Kota bitmesi | Kesinti ile aynı; aynı başarısız denemeyi kanıtsız tekrar yasağı | — |
| Kirli ağaç / başkasının işi | Boot DIRTY: mine/user/generated/unknown sınıflandırması; çakışan dosyada BLOCKED | — |
| Merge çakışması | Boot CONFLICTED; anlaşılmayan çakışmada BLOCKED | — |
| Kullanıcı yok, karar lazım | product.md DRAFT + Open Decisions; yalnız karardan bağımsız görevler READY | — |
| Akış/hedef değişimi | Hedef değişikliği kapısı: Goal yalnız kullanıcının sözüyle değişir; ADR + açık görevlerin etki geçişi | — |
| Yalnız görsel geri bildirim | Görev düzeyinde düzeltme; ilgili `[visual]` kanıtı yeniden üretilir | — |
| Küçük düzeltme | Görevsiz yol: ≤1 dosya, ≤20 satır, davranış değişmiyor → yap, doğrula, `[SA]` commit | Model sınırı yanlış değerlendirebilir; güvenlik/veri her zaman görev ister |
| Güvenlik/veri içeren küçük diff | Risk HIGH → REVIEW zorunlu, `global` doğrulama | — |
| Yayında yanıt kaybı | External `response_unknown` → READBACK_FIRST; `release-readback` beklenen/gözlenen karşılaştırması | Readback'i mevcut Fastlane yapar; araç mağazaya bağlanmaz |
| Paralel ajanlar | Ayrık Areas, ayrı worktree; IN_PROGRESS kilit değildir; entegrasyon sahibi birleştirir | Kilit yok; protokol disiplinine dayanır |
| Git'siz klasör | Dosya içerik digest'i; checkpoint/trailer yok; boot NO_GIT uyarısı; `git init` asla kendiliğinden yapılmaz | Devralma zayıflar; açıkça uyarılır |
| Mevcut projeyi devralma | `legacy`: 2.x `.factory` arşivi + `.project-brain` → `.store-automation` dönüşümü (önizleme, sonra uygulama); sonra Genesis/adoption | Brain'in eski şemaları desteklenmez; yalnız güncel şema |
| Tek ajanlı host'ta inceleme | REVIEW kuyruğu; aynı oturum başka adla inceleyici olamaz (Owner ≠ Reviewer kontrolü + protokol) | Beyan dürüstlüğüne dayanır |

Son eleştiri ve karar:
- REVIEW kuyruğu, areas digest ve yapısal External satırı, Brain'de olmayan ve store-automation 3'ün JSON töreniyle sağlamaya çalıştığı üç garantiyi git-native ve düşük törenle verir. Kabul.
- En zayıf halka model disiplinidir (Resume yazmak, Tier'e uymak). Araç her durumu boot'ta görünür kılar ve mekanik satırları kendisi yazar; bunun ötesi kriptografi veya daemon gerektirir, hedef dışıdır.

## 4. Son mimari

### Dosyalar

```text
.store-automation/            (git'e girer)
  product.md                  hedef: Goal, Status, kullanıcılar, yolculuklar, platformlar,
                              başarı koşulları [kind], riskli varsayımlar, hedef dışı, açık kararlar
  current.md                  doğrulanmış mimari + Map (≤40 satır path — rol) + Domains
                              (VERIFIED/OBSERVED/INFERRED/UNKNOWN)
  constraints.md              karar değiştiren kalıcı kurallar
  config.json                 komutlar (test/lint/build/run), git.commit auto|ask, git.push ask
  decisions/ADR-NNN.md        git'in tutamadığı gerekçe
  tasks/SA-NNN.md             yalnız bitmemiş işler
  runs/                       (git DIŞI) ham check logları; Evidence satırı hash ile referans verir
```

### Görev biçimi

```markdown
# SA-007 — Kayıt formunda çevrimdışı taslak
Status: READY            PLANNED | READY | IN_PROGRESS | REVIEW | BLOCKED | DONE
Priority: P1  Tier: M  Risk: MEDIUM  Milestone: M2  Depends: SA-004
Owner:                   uygulayan ajan/model (IN_PROGRESS'te yazılır)
Areas: `lib/form/**`, `test/form_test.dart`
## Objective     kullanıcının sözü + amaç
## Steps         numaralı, kesin yol/sembol/komut
## Acceptance    - [ ] [interaction] ... / [visual] / [machine] / [accessibility] / [security] / [remote] ...
## Verify        komutlar (config.json'dan)
## Escalate if
## External      - upload aab 3.1.0 | response_unknown | readback: fastlane supply track list
## Evidence      (araç yazar) check: <cmd> PASS digest=<…> log=<sha>
## Review        (inceleyici) Reviewer: … | Verdict: PASS/BLOCKED | Findings: severity/kriter/disposition
## Resume        Next: … / Failing: … / Dirty: …
## Notes
```

### Yaşam döngüsü

```text
PLANNED → READY → IN_PROGRESS → (LOW) DONE
                               → (MEDIUM/HIGH) REVIEW → DONE      (Reviewer ≠ Owner, Verdict PASS)
               ↘ BLOCKED (Blocked: ne, kimden)                     (dış karar/erişim/kullanıcı işi)
DONE + Evidence → checkpoint commit (SA-Task, SA-Verification, SA-Agent[, SA-Reviewer])
                → commit başarılıysa görev dosyası silinir; spec/kanıt git geçmişinde kalır
```

### Komutlar (`python store.py --project <app> <komut>`)

| Komut | Görev | Kaynak |
|---|---|---|
| `boot` | Durum: NO_PLAN/RESUME/INTERRUPTED/REVIEW_PENDING/READBACK_FIRST/DIRTY/ADVANCED/CONFLICTED/NO_GIT/INVALID; hedef, odak, sıradaki görev ve Tier'i, yüklenecek dosyalar, komutlar | Brain `cmd_boot` uyarlaması |
| `map`, `init` | Repo özeti + komut keşfi; iskelet (üzerine yazmaz), AGENTS.md işaretçisi | Brain |
| `new` | Görev iskeleti (tek yol) | Brain |
| `changed` | Son checkpoint'ten beri değişen alanlar | Brain |
| `validate` | Gramer, durum geçişi, REVIEW/Owner, Verify yolu Areas'ta mı, bütçeler | Brain + yeni kurallar |
| `check SA-NNN` | Verify komutlarını ProcessTree ile çalıştırır, digest + log hash'ini Evidence'a yazar | store 3 `run_check` |
| `accept SA-NNN` | Kabul kuralları → DONE'a geçirir ya da eksikleri listeler | store 3 `evaluate_acceptance` |
| `release-readback` | Beklenen/gözlenen yayın karşılaştırması | store 3 |
| `legacy` | 2.x `.factory` arşivi; `.project-brain` → `.store-automation` dönüşümü | store 3 + yeni |
| `doctor` | Python/git/proje durumu | store 3 |

Kaldırılan: `task`, `snapshot`, `prepare`, `finish`, `record`, `gate`, `handoff`, `usage` (görev dosyası modeli bunları kapsar; değerli kuralları `accept`'e taşınır).

### Model ayrımı mekanizması
- Güçlü model: Genesis, product.md, milestone ve tam tarifli görev yazımı, Tier H görevler, REVIEW kuyruğu, plan değişikliği ve ADR.
- Küçük model: READY Tier L/M görevler. Görev tasarım uydurmadan yürütülemiyorsa READY değildir; spec'i düzeltilir veya Tier H'ye çıkar.
- Boot sıradaki görevin Tier'ini ve REVIEW kuyruğunu basar; oturum kendi modeline uygun işi seçer. Model kendini beyan eder (`Owner`, `SA-Agent`).

### Protokol yerleşimi
- `SKILL.md` (≤90 satır): ne zaman plan, hafif yol, boot ile başla, yaşam döngüsü özeti, öncelik sırası, referans haritası.
- `references/plan.md`: Genesis, görev yazımı, yaşam döngüsü, devralma, plan değişikliği, denetim (Brain sentezi).
- `references/edge-cases.md`: git kenar durumları (Brain REFERENCE uyarlaması).
- Mevcut: `product-quality.md`, `execution.md` (sadeleşir), `release.md`, `migration.md`, `runtime.md` (yeni komutlar).

### Bilinen sınırlar
Kimlik ve inceleyici bağımsızlığı beyana dayanır. Kilit yoktur; paralel iş protokol disiplinidir. Areas kapsamı eksikse kanıt bağı eksik kalır (validate uyarır). Git'siz klasörde devralma zayıftır. Mağaza durumu gerçek araçla okunur; skill mağazaya bağlanmaz.

## 5. Yol haritası (v4)

| Aşama | Teslim | Kabul |
|---|---|---|
| P0 | Bu belge | Kullanıcı hedef ve mimariyi onaylar |
| P1 | Şema: dosya/görev grameri, durumlar, trailer'lar; `runtime/plan.py` parse + `validate` | Geçerli/geçersiz örnek görevler; testler |
| P2 | `boot`, `map`, `init`, `new`, `changed` (Brain'den uyarlama) + testleri | Geçici git repolarında her boot durumu üretilir |
| P3 | `check` (digest + Evidence yazımı) ve `accept` (kabul kuralları, REVIEW, Owner ≠ Reviewer) | Eskimiş kanıt, kendi incelemesi, eksik tür, zorunlu N/A reddedilir |
| P4 | Protokol: SKILL.md, plan.md, edge-cases.md, diğer referansların sadeleşmesi; eski JSON komutlarının kaldırılması | Belge-kod tutarlılık kontrolü; H9 bütçeleri |
| P5 | `legacy`: `.project-brain` dönüşümü | Örnek Brain projesi önizleme/uygulama, kullanıcı dosyası korunur |
| P6 | Gerçek alt ajanlı deneme: güçlü model Genesis → küçük model görevi yarıda keser → temiz ajan devralır → REVIEW → DONE; ayrıca küçük iş yolu | H1–H4, H6, H7 gözlemi; transcript ve commit'ler |
| P7 | Paket, push, Skills Manager dağıtımı, 46 kopya doğrulaması | Hash eşleşmesi, doctor |

## 6. Kullanıcıya açık kararlar
1. Eski JSON komutlarının (`task/prepare/finish/record/snapshot/gate/handoff/usage`) kaldırılması — öneri: kaldır.
2. Checkpoint commit varsayılanı — öneri: `git.commit: auto` (yetki içinde), `git.push: ask`.
3. Plan dosyalarının dili — öneri: bölüm başlıkları ve alan adları sabit İngilizce (parser için), içerik kullanıcının dilinde.
