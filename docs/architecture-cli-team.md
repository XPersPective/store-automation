# CLI ajan takımı mimarisi

Durum: HEDEF TASARIM v3 — fresh son eleştiride mimari blocker yok. Tarih: 2026-10-12.
Uygulama ve canlı kabul kapıları aşağıda ayrıca bekliyor; bu bir production-ready ilanı değildir.
Bu belge hedef tasarımdır; yazılmış veya çalışmış özelliklerin listesi değildir.

## Amaç ve sınırlar

Kullanıcı Codex/Antigravity gibi bir arayüzde seçtiği yürütücüyle konuşur. Yürütücü
projeyi tamamlamaya odaklanır; keşfi otomatik yapar, işi en düşük yeterli CLI modeline
verir, kaliteyi ölçer, görünür ajanlarla çalışır ve kota/oturum değişiminde işi kaybetmez.
Telefon bağlantısının kurulumu ikinci plandadır; mevcut uzak konsol kullanılabilir.
Resmi abonelik CLI'leri ve doğrulanmış ücretsiz yerel yollar yetkilidir. Ücretli API,
yeni faturalandırma, hesap rotasyonu ve seçilmemiş mağaza yayını yetkili değildir.

## İncelenen seçenekler

| Seçenek | Kazanç | Sorun | Karar |
|---|---|---|---|
| Project Brain + Store Automation birleşsin | Tek giriş belgesi | Her projeye Flutter/provider/UI bağımlılığı; plan ve çalıştırma yetkisi karışır | Reddedildi |
| İki skill, mevcut ortak yürütme araçları güçlensin | Tek plan, mevcut kurallar ve kod tekrar kullanılır | Skill prose tek başına zorunluluk sağlamaz | Seçildi; çalıştırılabilir kapılar gerekir |
| Üçüncü genel ajan yönetim skill'i | Başka alanlarda kullanılabilir | Şimdi ek sürümleme/bağımlılık/dağıtım ve iki yönetici yaratır | Şimdilik ertelendi; ikinci gerçek tüketici oluşursa çıkarılabilir |
| OmniRoute/OmniRouter zorunlu proxy | Tek API/fallback yüzeyi | CLI izin/oturum/hesap/kota ve abonelik semantiğini koruduğu kanıtlanmış değil | Varsayılan yol değil; mevcut kurulum metadata olarak keşfedilir |

Project Brain: amaç, kurallar, kararlar, görev/kabul ve Resume. Store Automation:
işi tanımlama, yerel keşif, native CLI adaptörleri, dağıtım, ölçüm, görünürlük ve kabul.
İki skill ayrı kalır; uygulama başına **bir** Brain. Çalıştırma kayıtları ikinci plan değildir.
Aktif sohbet tek yürütücüdür; her işte ikinci bir yönetici modeli başlatılmaz.

## Gerçek başlangıç kanıtı

2026-10-12 PATH + bilinen kurulum binleri taraması 13 giriş buldu: Codex, Claude,
AGY, OpenCode, MiMo, MCode, eski MiniMax desktop launcher, Gemini, Kimi, Qwen,
Hermes, LM Studio `lms`, OmniRoute. Skills Manager ayrıca 54 host kaydı/41 kurulu
host ipucu sundu. Host ipucu çalışabilir CLI demek değildir. MiMo'nun 7 model kimliği,
AGY'nin Flash/Pro ve diğer katalog kimlikleri gerçek metadata komutundan alındı.
MCode ACP `configOptions` gerçek M3.1 Flash/M3/M2.7 model varyantlarını ve low..max
eforları, Kimi ACP ise K2.8/K2.7/K3/K3-256k ve low/high/max seçeneklerini verdi.
Eski `minimax.cmd` hedefi bulunmayan daemon dosyasına işaret ediyor; MCode ayrı
çalışan CLI'dir. Bu bozuk shim üzerinden ücretli veya izinli iş başlatılmaz.
Codex CLI model listesi mevcut sohbet model listesiyle aynı değil: native CLI
Luna/Terra/Sol/Astra sunuyor; sohbetin 6.1 Sol seçimi bu CLI'de varmış gibi gösterilmez.
Luna/low gerçek kaynak haritası işi 36.105 giriş/453 çıkış token raporladı; sistem
overhead'i dahil, ucuz model seçimi tek başına az token demek değildir.

## Başlangıç akışı ve zorunlu kapılar

1. Seçilen proje kökü + Brain boot + deterministik Git durum/changed özeti. Tüm repo okunmaz.
2. Yerel araç keşfi ve metadata yenileme. Kullanıcıdan araç listesini yazması istenmez.
3. Gerekirse hafif CLI'ye yalnız değişen kaynak dilimleriyle resume taraması verilir;
   yürütücü en fazla kısa bulgu, çelişki ve sıradaki kabul maddesini okur.
4. Her iş için complexity + risk + gerekli yetenek + kontrol komutu + izin kapsamı
   tanımlanır. Belirsiz iş önce küçük keşif görevi, sonra uygulanabilir iş olur.
5. Çalıştırma öncesi kalıcı assignment: görev, rol, parent, CLI/model/efor, neden,
   bağlam/çıktı bütçesi, gerçek yetki, kota kanıtı, oturum ve görünür yüzey.
6. Dağıtım kapısı bu kayıt, taze capability/quota/permission ve worker kabulü olmadan
   model çalıştırmaz. Açık bir kapsam içi araç iznini yürütücü verir; kullanıcıya tekrar sormaz.
7. Gerçek CLI worker/patch önerisi -> makine kontrolü -> ayrı fresh reviewer -> yürütücü kabulü.
   Substantive işi yalnız yöneticinin yazıp kendi incelemesi dağıtım olarak sayılmaz.
8. Kanıt, kullanım, artifact ve ilk eksik kabul maddesi kaydedilir; sonraki görev otomatik seçilir.

Deterministik komutlar ajan değildir; sırf üç rol göstermek için inference yapılmaz.
Skill yönergesi tek başına tam erişimli başka bir AI'ı zorlayamaz. Teknik zorunluluk
wrapper üzerinden dispatch/acceptance kapısında uygulanır; wrapper dışı iş doğrulanmış
fabrika işi sayılmaz. Native host doğrudan delegasyonu açık yetki/kanıtla kaydedilir,
CLI başarısızlığında sessiz ve pahalı fallback değildir. Native host yolu da aynı
assignment authority ve kabul kapısına kayıt olur; ayrı gevşek kabul yolu yoktur.

## Keşif ve native adaptör sözleşmesi

Keşif: PATH, bilinen resmi kurulum binleri, paket/binary metadata, Skills Manager
host ipuçları. Diskin veya credential dizinlerinin içerik taraması yapılmaz. Yeni
bilinmeyen executable yalnız adaydır; kimlik ve resmi help doğrulanmadan çalıştırılmaz.
Resmi CLI eksikse kapsamda ihtiyaç varsa resmi imzalı/package-manager yolundan kurulabilir;
54 client'ı birden kurmak amaç değildir. Login/challenge native kullanıcı eylemidir.
Completeness manifesti discovery root/sürüm, taranan entrypoint sayısı, adapter help
kanıtı, timeout/erişim hatası ve kapsam dışı host ipucunu taşır. Bulunan binary path'i
kanonik kimlikle deduplicate edilir; rastgele disk kurulumları için eksiksizlik iddia edilmez.

Her adaptör aynı **kontrol** sözleşmesini sağlar; aynı inference protokolü varsayılmaz:
discover, models, account-mode, quota/reset, permissions, start, observe, intervene,
stop, report, resume. Her alan SUPPORTED / UNSUPPORTED / UNVERIFIED ve kaynağıyla durur.
API anahtarı/session token içerikleri okunmaz veya başka client'a aktarılmaz.

| Yol | Native mekanizma | Şu anki kanıt / kalan kapı |
|---|---|---|
| Codex | app-server metadata; exec snapshots; hedefte thread/turn kontrolü | Gerçek Luna işi/ölçüm var; wrapper exec canlı sohbet değildir |
| AGY | models, metadata slash, TUI/stream-json | Metadata var; gerçek task/dual transport ve izin kanıtı eksik |
| MCode | exec/TUI/ACP | Gerçek ACP model/efor katalog kanıtı var; account/quota ve Token Plan ücret davranışı doğrulanmalı |
| MiMo | models, serve/attach/HTTP, native sessions | 7 model listelendi; hesap/quota/izin adaptörü ayrı kanıt gerekir |
| Kimi | ACP/TUI/web, provider/session | Gerçek ACP model/efor katalog kanıtı var; usage/plan ve permission doğrulaması gerekir |
| Gemini | model/prompt/plan + native login | Önceki auth-required; native Google login ve effective plan gerekir |
| OpenCode | serve/HTTP/attach | Mesaj/abort/noReply gerçek kanıt var; listelenen ücretsiz model erişimi taze doğrulanır |
| Hermes / LM Studio | kendi CLI/session ve yerel inference | Help var; model/tools/kalite/compute etkisi ve hesap yolu değerlendirilir |
| Claude / Qwen | kendi CLI | Önceki kullanıcı dışlama kuralı geçerli; keşiften silinmez, dağıtılmaz |
| OmniRoute | ayrı proxy | Kurulu; ayar değiştirilmez ve abonelik bypass yolu yapılmaz |

Bir katalogdaki her model, yürütücünün kendi CLI alt modelleri dahil havuzda görünür.
Erişim/uygunluk doğrulanmamış kayıtlar görünür fakat seçilemez. Model adından kalite,
ücretsiz fiyat veya izin çıkarılmaz. Belirli model erişimi gerçek ilk görev sonucu
ile kanıtlanır; her işten önce ücretli "merhaba" propları yapılmaz.

## Model, efor ve toplam maliyet

| İş | Minimum başlangıç | Büyütme gerekçesi |
|---|---|---|
| hash, map, diff, format, kota | deterministik komut | yalnız açıklama/çelişki muhakemesi gerekirse hafif model |
| dar özet, açık küçük düzeltme | doğrulanmış hafif model/low | yeterli bağlamla somut kabul başarısızlığı |
| normal coding/debug | ölçülmüş yeterli model, uygun effort | sınırlar arası belirsizlik veya kanıtlı başarısızlık |
| mimari, güvenlik, veri kaybı | güçlü uzman/uygun yüksek effort | yalnız zor karar dilimi; tüm repo güçlü modele verilmez |
| bağımsız review | işin riskini kontrol edebilen fresh model | bağımsızlık rol değil ayrı oturum/kanıttır |

Complexity ve risk farklıdır: kısa auth değişikliği basit metin ama yüksek risk olabilir.
Seçim yöneticinin modeliyle eşleşmez. Yürütücü düşük modelse güçlü mimara işi verir;
yüksek modelse basit işte kendi pahalı alt ajanını kopyalamaz. Persona ve model ayrı seçimdir.
Karar: gerekli kalite/izin/araç eşiğini sağlayanlar -> taze erişim/billing/quota ->
beklenen **toplam** tüketim -> en düşük yeterli rota. Toplam; worker+review+retry+
bağlam/system/reasoning+handoff overhead'idir. Metadata fiyatı yoksa TL/$ uydurulmaz.

Tam dosya/history yerine satır aralığı ve hash verilir; diff/affected callers kritikse
eklenir. Bağlam bütçesi gerçek serialize payload üzerinde kontrol edilir. Çıktı bütçesi
native destek varsa teknik limit, yoksa talimat + sonuç ölçümü ve aşım kaydıdır; hard cap
diye sunulmaz. Kota yüzdesi token sayısı değildir; şeffaf biçimde UNKNOWN/null kalabilir.
Kümülatif/parent-inclusive native sayaçlar iki kez toplanmaz; bütün retry/child attempt
manifesti olmadan "toplam kullanım" tamamlandı denmez.

Tekrarlanabilir suitability rubric: her task ayrı `required_capabilities`, `risk`,
`complexity`, `verification`, `role` taşır. SIMPLE düşük risk ve açık kabul için L,
STANDARD normal mühendislik için M; COMPLEX/SPECIALIZED veya HIGH risk H floor ister.
Adaptör modelin o sınıfta kaynak okuma/patch/tools/review kabul kanıtını ve native
efor seçeneklerini kaydeder. İsim veya katalog açıklaması yalnız sınıflama adayıdır;
kanıtsız aile yeni eligible route olmaz. Aynı contract+inventory+policy aynı sıralama
verir: sınıf-floor, ölçümlü tüketim bandı, uygun effort, bağımsız kota, kararlı model ID.
Ölçüm yoksa onaylı role bandı kullanılır ve ESTIMATED etiketi taşır. Başarısız kabulde
önce bir bağlam/spec düzeltmesi; tekrar aynı gerekçesiz retry yasak. Sonra kayıtlı
bir eşdeğer rota veya somut risk gerekçeli bir band yükseltme; devam etmeyen döngü
BLOCKED checkpoint olur. Kalite gate'i geçmeyen ucuz yol ekonomik başarı sayılmaz.

## Kota, bekleme, eşdeğer fallback ve yönetici değişimi

Kota gözlemci deterministik çalışır; usage için LLM çağrılmaz. Önce dispatch, uzun işin
provider-safe aralığı, tamamlanma/hata/müdahale sonrası kontrol. Ağ yoksa veya quota
bilinmiyorsa UNKNOWN; izinli/free olduğu varsayılmaz. Aynı account bucket'taki sibling
modeller aynı kotayı paylaşır; model adı değişikliği yeni kota yaratmaz.

State: DISCOVERED -> ELIGIBLE -> ASSIGNED -> RUNNING -> VERIFYING -> REVIEWING ->
ACCEPTED. Yan yollar: WAITING_QUOTA, WAITING_LOGIN, WAITING_TRANSPORT, INTERRUPTED,
NEEDS_RECONCILIATION, FAILED. Process exit0 ayrı, worker COMPLETED ayrı, kabul ayrıdır.

Kalan ortak pencere <=%10 ise yeni iş başlamaz. Eski %10/%0 kaydı kalıcı yasak değildir:
native reset_at + bounded backoff ile yalnız metadata yenilenir; reset saati geçti diye
erişim açılmaz, yeni native ölçüm gerekir. Reset bilinmiyorsa seyrek bounded metadata
yenileme; pahalı auth/model propları tekrarlanmaz. UI'da zaman/eskime/sonraki ölçüm gösterilir.

Yarım iş: önce worker stop/idle ve owned process-tree kanıtı -> gerçek diff/untracked
sahipliği + unchecked kabul + test/artifact + pending report -> kalıcı handoff ->
taze eşdeğer CLI seçimi -> ilk eksik kabulden devam. Önce aynı yeterlilik/maliyet bandı,
sonra gerekçeli küçük yükseltme. Bilinmeyen permission veya kapasite "eşdeğer" değildir.
Mutator timeout ve çıktı yoksa kör replay yapılmaz; tek app writer kilidi serbest kalmaz.
İdempotent read-only iş ancak kaydedilmiş başarısız attempt sonrası sınırlı tekrarlanabilir.

| Gözlem | İzin verilen karar |
|---|---|
| account-mode/billing UNKNOWN veya overage belirsiz | start çağrılmaz; WAITING_LOGIN/BILLING doğrulaması |
| quota UNKNOWN/stale | yeni included-subscription inference başlamaz; metadata yenile/WAITING_QUOTA |
| free local model, account quota uygulanamaz | yalnız doğrulanmış local compute/tools/kalite profili; quota NOT_APPLICABLE |
| fresh kota reserve üstünde ve permission/billing/capability geçerli | ELIGIBLE; ilk actual task erişim kanıtı olarak ayrı tutulur |
| reset_at geçti fakat yeni ölçüm yok | WAITING_QUOTA devam eder |
| provider/network hata | backoff; izinleri veya hesap politikasını gevşetme |

Watcher inference yapmaz; provider'ın minimum sorgu aralığı korunur. Reset zamanı
biliniyorsa ona kadar gereksiz polling yok; yoksa başlangıç60s ve üst sınır15min
backoff, jitter, tek outstanding request ve max30s metadata deadline. Bekleyen task
başına değil shared provider bucket başına bir observer. Provider farklı cadence
gerektiriyorsa onun değeri baskındır. Sürekli watcher yalnız gerçek owned service
çalışıyorsa "izleniyor" gösterilir; skill sohbeti kapalıyken kendiliğinden uyanmaz.

Admission bucket bazında atomiktir: aynı resmi hesap context'i ve paylaşılan bucket
için bir host-level exclusive owned lock; bu global proje/Brain kaydı değil geçici
çalıştırma kilididir. Aynı provider içindeki hesap bağının bilinmediği yollar muhafazakâr
aynı bucket sayılır; quota-driven account rotation yapılmaz. Token->quota dönüşümü
native kanıtla bilinmiyorsa o bucket'ta factory işi max1 outstanding (review dahil).
Yalnız farklı kanıtlı bağımsız bucket'lar paralel olabilir. Commit edilen admission
assignment/estimate/review rezerv ihtiyacını taşır; ölçülmüş dönüşüm varsa outstanding
commitment'ler hesaba katılır. %10 soft güvenlik eşiğidir, native harcamaya hard cap
değildir: mevcut GUI, başka proses veya beklenenden uzun reasoning kotayı tüketebilir.
Fresh ölçüm iş sırasında reserve altına düşerse new admission kapanır; native stop/
checkpoint ilk güvenli fırsatta yapılır. Gerçek bu takip/stop yeteneği yoksa o adapter
long-running unattended eligible değildir. Dış oturumların admission'a uyduğu varsayılmaz.

Yönetici reserve'e gelmeden Brain Resume ve assignment/usage/evidence referanslarını
kaydeder. Kullanıcı başka assistant/provider'a geçince yeni yönetici aynı proje boot'u,
eski process/lock uzlaştırması, fresh inventory ve küçük resume worker ile devralır.
Eski yöneticinin yetkisi sessiz aktarılamaz; kullanıcı model değiştirmesi geçerli devirdir.
Resume paketi version/project/task/contract hashes, first_unchecked, owned-session/PID
identity, diff/evidence/artifact/attempt references, pending reports ve next_action'dan
oluşur; source/chat payload taşımaz. Serialize özet max12.000 karakter, max500 token
worker sonuç hedefi. Büyük diff dosyada kalır ve ilgili slice yeni worker'a gider;
paket sessiz kesilmez, oversized alan referansa dönüştürülür. Ek system overhead ayrı ölçülür.

## Görünürlük, müdahale ve artifacts

GUI'den skill çağrılması terminalden başlatma zorunluluğu doğurmaz. Supervisor mevcut
sohbette kalır; actual CLI'leri owned console'da açar. Tercih mevcut native terminal/TUI;
WT activity/director/worker alanları task-dependent bölünür. Codex terminal split veya
CLI-to-sidebar binding API yoksa varmış gibi gösterilmez; desteklenen browser/panel
üzerinden seçilmiş yerel konsol açılır. Log ekranı canlı konuşma kabulü değildir.

Her kart/pane: rol, gerçek görev/CLI/model/efor, parent, durum, son olay ve timestamp,
ölçülmüş usage, ortak quota/reset, kullanıcı sorusu, son rapor ve kontrol yeteneği.
İstediği kadar uzman ancak gerçek görev/bağımsız alan/kota kadar; boş pane uğruna ajan açılmaz.
Tek app writer; read-only/disjoint isolated incelemeler sınırlı concurrency ile paralel.
Müdahale transport native TUI / Codex turn-steer / ACP / owned HTTP olur. Mesaj ack
ile ajan uyguladı ayrı olaylar; director receive/reconcile ack gerekir. Aktif yazara yön
değiştirme stop-checkpoint-contract-reconcile sonrası resume; yeni ikinci writer açılmaz.
Desteksiz transport açık gösterilir; sonradan desteklenebilir fakat tüm kontrol var denmez.

Screenshot/build/emulator artifact manifesti: proje-relative dosya, source/contract/build
hash, platform/device/run timestamp, provenance, boyut/tür. Kullanıcıya preview ve aç/download
yüzeyi; repo dışı/link/sensitive veya manifest dışı dosya servis edilmez. Android canlı
emulator ve iOS hosted screenshot ayrı evidence yolları; screenshot kaynak incelemesinin
yerine geçmez. Accessibility/device kabulü actual render ile doğrulanır.
Telefon kurulumu ertelendi; aynı console seçilmiş private remote transport üzerinden
kullanılır. Yeni public listener/funnel yok; credential metni/loglar/sınırsız shell sunulmaz.

## Yetki ve kurtarma

Supervisor açık scope içindeki read/test/build ve exact app source izinlerini sözleşmeden
verir. Global yolo/skip-permissions yerine native denied-by-default scope. Native tool
exact scope'u teknik uygulayamıyorsa worker read-only patch önerir; supervisor izinli
scope'u kontrol edip uygular. Prompt kuralı tam erişime karşı sandbox değildir.
Yazma/başlatma/stop/relay sahipliği proje ve actual session/PID identity ile bağlıdır.
Crash, stale lock, PID reuse, aynı repo iki yönetici, kapanmış/reordered panes ve quota
değişimi kontrol kaydıyla uzlaştırılır. User/unknown edits korunur; reset/stash yok.
Reviewden sonra kaynak değişirse evidence invalid olur ve etkilenen check yeniden gerekir.

Tek `.factory/` controller tüm start/write/stop/accept authority'sidir; yeni kalıcı
task DB yok. Mevcut exclusive dispatch lock monotonic generation+random ownership nonce
ve actual process identity ile genişletilir; kaydı atomik replace edilir. Her attempt
immutable sözleşme/hash/owner generation taşır. Yeni director eski controller hâlâ
yaşıyorsa yeni writer açmaz; user-steering veya kontrollü owned stop bekler. Crash'te
process tree öldüğü ve diff uzlaştırıldığı kanıtlanmadan lock devralınmaz. Eski generation
raporu yeni task acceptance'ını ilerletemez. Brain'de lease/journal/session veritabanı
kurulmaz; yalnız task Resume ve ignored control kayıtlarının referansları tutulur.
Native kapsam dışı yazmayı önleyemeyen adapter write eligible değildir; yalnız patch.

Launch handshake: immutable PREPARED attempt ve containment kimliği fsync edilmeden
spawn yok. Windows child suspended yaratılır, kill-on-close/no-breakaway JobObject'e
alınır, process birth identity durable olarak yazılır ve sonra resume edilir. Mevcut
ProcessTree suspended containment kısmını sağlar; resume-before-durable-identity sırası
bu yeni protokolde ayrılmalıdır. Resume öncesi crash'te job handle kapanır; orphan
suspended child varsa dead owner/birth/containment evidence olmadan yeni writer açılmaz.
POSIX yalnız process group parent's death için garanti değildir: supervised launch
handshake ve parent-death/session containment gerçek kanıt yoksa autonomous write yok,
read-only patch mode. Protokol öncesi/sonrası spawn-crash ve detached descendant
testsiz adapter autonomous mutator olmaz. Normal stop tüm descendants'ın bittiğini
kanıtlar; timeout/belirsizlik lock'u ve NEEDS_RECONCILIATION state'ini korur.

API yetkileri role/scope bazlıdır: worker yalnız kendi attempt'ına bounded report/
checkpoint isteği gönderir; start/write/accept/takeover yapamaz. UI yalnız seçilen
owned session'a message/abort ve izinli artifacts read sağlar; gerçek kabul/patch
uygulaması controller'ın scope/hash/generation kontrolünden geçer. Controller'ın
privileged capability ve yerel HTTP password'u worker env'e aktarılmaz. Native CLI
kendi hesabının credentials'ını kendi yönetir; runner başka araca aktarmaz. İstenen
write permission native contract'tan geçer; worker self-report veya API request'i
authority değildir. Same-user API capability ayrımı hatalı/forged istemcileri engeller;
tam erişimli aynı OS kullanıcıya karşı gizlilik/sandbox garantisi değildir. Bunun için
ayrı OS kimliği/broker gerekir (mevcut PB011); kanıtsız strict isolation iddiası yok.

Yeni model enrollment deadlock yaratmaz: DISCOVERED -> METADATA_READY -> CALIBRATING
-> ELIGIBLE. CALIBRATING yalnız zaten geçerli billing/quota/permission gate'i ardından
izinli, kısa read-only veya isolated synthetic representative task çağırabilir; üretim
acceptance yetkisi yoktur. Profile class/role/capability/effective permission/model/
version/dated source/evidence ile yazılır; eşdeğer görevlerde önceki bağımsız kanıt
varsa tekrar benchmark yapılmaz. Kaynak/model/adapter değişimi veya failure capability
kanıtını stale yapar. Sürekli full benchmark ve her görevde tool-free merhaba yok.
Model family etiketi/reklam tek başına promosyona yetmez. Yanlış/objeli report schema,
yanlış task/model/effort ve measured output-budget aşımı kayıt altına alınır; model
COMPLETED demiş olsa bile doğrulanmış rapor/kabul yerine geçmez. Native output schema
mevcutsa runner kullanır; soft budget metadata'da soft etiketi taşır.

GUI capability manifest: Codex native terminal binding UNKNOWN; browser-panel opening
host tool tarafından acknowledged ve rendered olursa SUPPORTED. WT executable mevcut,
structural split mevcut fakat actual rendered/intervention testi bekler. Her yüzey
attach request/ack/visible/user-send/agent-ack/director-reconcile ayrı evidence taşır.
Artifact/control HTTP gerekirse yalnız loopback authenticated ephemeral random session
secret, exact project/session/contract binding, same-origin+Host kontrolü, bounded input,
no redirects, no generic shell/files route, no sensitive/link/path traversal. Secret process
env'de kalır; URL query/log/Brain'e yazılmaz. Transcript ve image opt-in local `.factory/`
ignored; dış dağıtımda yalnız sanitize structural evidence. Kullanıcı stop/cleanup mevcut
owned runtime'ı kapatır; orijinal kaynak ve artifacts otomatik silinmez.

## İstek -> kabul matrisi

| İstek | Tasarım / gözlenebilir kabul |
|---|---|
| Zorunlu alt ajan | assignment+dispatch+acceptance gate; worker/fresh reviewer olmadan substantive kabul reddedilir |
| Bütün CLI keşfi | PATH+bin+host registry; her tespit executable/model/docs/control/gap kaydı taşır |
| Kendi modelleri havuzda | native katalogların union'u; sohbet katalog yetkisi CLI entitlement sayılmaz |
| En düşük yeterli model | simple işte uygun hafif rota; pahalı seçim yalnız başarısız kabul/risk gerekçesiyle |
| Zayıf yönetici/güçlü mimar | architecture capability floor altında director kararı specialist'e devreder |
| Düşük token resume | boot/changed deterministic + sınırlı worker özeti; full-history reload yapılmaz |
| Kota/reset/fallback | shared bucket reserve+fresh reset ölçümü+durable equivalent handoff; paralel writer reddedilir |
| Yürütücü değişimi | başka provider aynı Brain/Resume/owned process uzlaştırmasıyla ilk unchecked kabulden devam |
| GUI başlangıç + split | mevcut sohbet korunur; actual native sessions owned console'da görünür; attachment sonucu doğrulanır |
| Ajana konuşma | user send/ack/agent+director reconcile kanıtı; logs veya queue receipt tek başına yetmez |
| Görsel/emulator | gerçek artifact manifest/preview + actual desktop/mobile/render kontrolü |
| Remote | mevcut kullanıcı remote konsol; ayrı telefon kurulumu sonraki aşama |
| Otomatik kurulum/izin | ihtiyaç resmi CLI install + contract-scoped izin; login/billing güven sınırı korunur |
| Kalite/bitirme | machine+fresh review; hata bağlamı düzeltilir, kontrollü gerekçeli yükseltme ve checkpoint |
| Brain birleşimi | iki skill, tek Brain, tek sohbet director; runnable dispatch gates |
| OmniRouter | keşfedilir, proxy opsiyoneldir; native CLI izin/kota/oturum kanıtı yerini almaz |

## Uygulama sırası (tasarımdır; tamamlanma iddiası değildir)

1. PB027: başlanmış metadata/context-range bütçe düzeltmeleri ve discovery kapsamı;
   PB031: tek assignment authority/risk/enrollment/permission/report gates.
2. PB032: gerçek MCode/Kimi ACP metadata ve account/quota capability adaptörleri;
   PB035: Codex native canlı kontrol; PB036: ikinci CLI'nin verified live transport'u.
3. PB033: shared quota metadata observer/admission/reset; PB034: launch/stop/checkpoint/
   equivalent worker handoff + başka director takeover crash senaryoları.
4. PB028: task-aware console/WT+native conversation+artifact previews; rendered QA.
5. PB029: ilgili tüm installed skill hedeflerinde hash-verified dağıtım; mevcut remote
   console uyumu. Telefon pairing/server kurulumuna şimdi zaman harcanmaz.

Son kapı: iki farklı native CLI ile gerçek app task/inceleme, cheap model, shared quota
yenilemesi, controlled interruption/half-work takeover, kullanıcı sorusu, actual artifact
gösterimi ve yeni provider director resume. Mock test veya mimari belgesi bu kapıyı kapatmaz.
