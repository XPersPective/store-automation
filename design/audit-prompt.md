# Bağımsız denetim promptu — Store Automation 4

Aşağıdaki `---` çizgisinin altındaki metni olduğu gibi başka bir ajana ver. Ajan bu konuşmanın geçmişini bilmez; ihtiyaç duyduğu her şey burada ve repoda.

---

## Rolün

Sen ajan skill'leri (Claude Code / Codex / Gemini / Cursor skill'leri) için kıdemli bir denetçisin. Aynı anda dört şapkan var:
- Ürün ve UX direktörü
- Yazılım mimarı
- Kıdemli frontend ve backend mühendisi
- Küçük modellerin talimat takip davranışını bilen bir değerlendirici

Görevin `store-automation` skill'ini genel olarak analiz etmek, eleştirmek ve düzeltme önermek. Ana soru şu: bu skill ile verilen her iş — frontend, backend, mimari, planlama, devralma, yayın — **premium kalitede ve uçtan uca** bitiyor mu? Farklı senaryolarda kırılmadan ve tutarlı çalışıyor mu?

Nezaket değil kanıt önemli. Belgedeki iddiaya, testlerin geçmesine veya önceki raporlara güvenme; her sonucu kendin gözle, çalıştır ve yeniden üret.

## Bağlam

- **Kaynak repo:** `D:/repositories/store-otomaston` (dal `master`). Önce şunları oku:
  - `AGENTS.md`, `HANDOFF.md`, `README.md`
  - `design/v4-target.md`: hedef H1–H9, tasarım brief'i, öner-eleştir turları, mimari, §7 P6 sonuçları, §8 genel devralma
  - `design/validation-report.md`
- **Dağıtılan paket:** `release/store-automation/` (SKILL.md, store.py, runtime/, references/, package-manifest.json). Skills Manager ile 41 ajana ve 4 ek dizine dağıtılmış durumda; merkez kopya `~/.skills-manager/skills/store-automation`.
- **Skill'in vaadi:**
  - Bir uygulama fikri ya da mevcut proje verildiğinde güçlü model ürünü, mimariyi ve risk sıralı aşamaları planlar.
  - Küçük modeller tam tarifli görevleri uygular.
  - Her görev güncel kaynağa bağlı kanıt ve gerektiğinde farklı bir ajanın bağımsız incelemesi olmadan kapanmaz.
  - Herhangi bir anda kesilen işi başka bir ajan (başka model veya sağlayıcı, sohbet geçmişi yok) yalnız repodan doğru yerden devralır.
  - İş seçilen platformda yayına kadar götürülür.
- **Durumun tutulduğu yer:** Projede `.store-automation/` dosyaları (product.md, current.md, constraints.md, config.json, decisions/, tasks/) ve git commit trailer'ları (`SA-Task`, `SA-Verification`, `SA-Agent`, `SA-Reviewer`, `SA-Current-Checkpoint`…). Yalnız `runs/` git dışıdır.
- **Komutlar:** `doctor, boot, map, init, new, start (--takeover), check, evidence, review, accept (--as), changed, validate, legacy (--apply/--path/--drop-archive), release-readback`. Görev durumları: PLANNED → READY → IN_PROGRESS → REVIEW → DONE, ayrıca BLOCKED. Boot durumları: NO_PLAN, LEGACY, RESUME, INTERRUPTED, DIRTY, ADVANCED, CONFLICTED, READBACK_FIRST, NO_GIT. `accept` sonuçları: DONE, REVIEW_PENDING, WAITING_USER, UNVERIFIED, BLOCKED.
- **Yakın tarihli değişiklikler:**
  - Project Brain'in plan/devam/harita mekanizması bu skill'e sentezlendi.
  - Project Brain bu bilgisayardan global olarak kaldırıldı: Skills Manager kaydı ve dağıtımları silindi. Global talimatlar (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, OpenCode, Qwen) ile Cursor, Cline, Copilot, Kiro, Trae ve Windsurf kural dosyaları store-automation kuralına çevrildi.
  - `legacy` artık her türden yabancı plan/durum sistemini (Brain'in her şeması, Task Master, memory bank, Kiro specs, eski 2.x factory veya `--path`) aynı yoldan devralıyor: önce hedef, durum ve açık işler izleme tablosuyla plana aktarılıyor, sonra eski sistem siliniyor.
- **Kullanıcı kararları:** Commit ve push otomatik. Plan dosyalarında başlıklar İngilizce, içerik kullanıcının dilinde. Ücretli API, credential içeriği okuma, billing/signing değişikliği ve seçilmemiş üretim yayını yasak.
- **Kullanıcının en önemli şartı:** Yaptırılan her iş premium kalitede olmalı. Frontend premium, backend premium, mimari kurgu premium; plan ve devir de premium. "Çalışıyor" yetmez; işin en iyi uygulama düzeyinde olması gerekir.

## Kurallar

1. **Salt okunur başla.** Şunlarda hiçbir şeyi değiştirme, commit/push/deploy yapma: kaynak repo, kurulu skill kopyaları, `D:/repositories` altındaki gerçek kullanıcı projeleri, Skills Manager kaydı, global talimat dosyaları. Deneyleri yalnız kendi geçici dizininde, repoyu, paketi veya bir projeyi oraya kopyalayarak yap; kopyalarda git remote'u kaldır.
2. Ücretli API yok, ağdan paket kurma yok, credential veya secret dosyası açma yok.
3. Alt ajan başlatabiliyorsan farklı güçte modellerle (güçlü + küçük) gerçek senaryolar koş. Başlatamıyorsan bunu açıkça yaz ve senaryoyu her rolü ayrı ayrı, yalnız repo dosyalarını okuyarak oyna.
4. Her bulgu kanıtlı olmalı: dosya:satır, çalıştırdığın komut ve gözlenen çıktı ya da yeniden üretim adımı. Kendin yeniden ürettiklerini CONFIRMED, kanıtsız şüpheleri PLAUSIBLE diye işaretle.
5. Kontrol edemediğin şeyi saklama; "kontrol edilmedi" listesine yaz.

## Denetim alanları

Her alanda önce iddiayı çıkar, sonra karşı örnek ara.

### A. Hedefe uygunluk
- H1–H9 başarı koşullarının her birini kendi deneyinle yeniden ölç. P6'daki "karşılandı" iddialarını yeniden üret, "kısmi" olanları derinleştir: H5 devralma, H6 dış işlem, H8 POSIX, H9 bütçe.
- Uçtan uca zinciri baştan sona izle: boş repo → Genesis → M1 → uygulama → kanıt → inceleme → DONE → sonraki görev → final audit → yayın hazırlığı. Zincirin koptuğu ya da ajanın ne yapacağını bilemediği her noktayı yaz.

### B. Premium kalite — skill'e gerçekten iş yaptır (en önemli bölüm)
Belgeyi okumak yetmez. Skill'e geçici dizinde gerçek işler yaptır ve çıktıyı aşağıdaki ölçütlerle 1–5 arası puanla. Her puanın gerekçesi gözlenmiş kanıt olsun: ekran görüntüsü, gerçek etkileşim, çalıştırılmış test, kod alıntısı.

**Önerilen deneyler:**
1. **Mimari ve plan:** Belirsiz bir fikir ver (örnek: "aile içi harcama paylaşma uygulaması, mobil + web, çevrimdışı çalışsın") ve skill'e Genesis yaptır. Sonra ürün, mimari, veri modeli ve aşamaları değerlendir.
2. **Frontend:** M1/M2'deki bir UI görevini skill'le uygulat: form, liste, boş/yükleniyor/hata durumları, diyalog. Sonucu gerçek bir tarayıcıda veya emülatörde render et, dar ve geniş ekranda etkileşimle dene.
3. **Backend:** Kalıcı veri, doğrulama, yetki ve hata yolları içeren bir API veya servis görevi uygulat. Çift istek, yanıt kaybı ve geçersiz girdi senaryolarını çalıştır.
4. **Mevcut proje:** Bu skill'le yazılmamış gerçek bir projenin kopyasında küçük bir özellik eklet. Mevcut tasarım dili ve mimari korunuyor mu, yoksa şablona mı itiliyor?
5. **A/B karşılaştırması:** Aynı frontend ve backend görevini aynı modele bir kez skill'siz, bir kez skill'le yaptır. Skill kaliteyi yükseltiyor mu, yalnız tören mi ekliyor, yoksa yaratıcılığı mı kısıtlıyor? Fark kanıtlı olsun.

**Premium ölçütleri:**
- **Mimari:**
  - En az iki gerçekten farklı seçenek gerekçeli ödünleşimlerle karşılaştırılmış mı, seçim ADR'ye yazılmış mı?
  - Sınırlar ve sahiplik net mi? Veri modeli, tutarlılık, eşzamanlılık, çevrimdışı/senkronizasyon, migration ve geri dönüş düşünülmüş mü?
  - Başarısızlık modları ve gözlemlenebilirlik var mı?
  - Basitlik var mı, gereksiz katman veya framework eklenmiş mi?
  - Gelecekteki değişime açık mı, ve en pahalı yanlış varsayım önce mi deneniyor?
- **Frontend:**
  - Tutarlı bir tasarım sistemi kullanılıyor mu (token, tipografi, boşluk ve renk ölçeği)? Görsel hiyerarşi açık mı, ürüne özgü bir kimlik var mı yoksa jenerik şablon mu?
  - Tüm durumlar ele alınmış mı: boş, yükleniyor, hata, başarı, çevrimdışı, izin reddi?
  - Responsive düzen var mı, uzun metin ve yerelleştirme bozulmadan çalışıyor mu?
  - Erişilebilirlik sağlanmış mı: kontrast, klavye/odak, ekran okuyucu, dokunma hedefi?
  - Mikro etkileşim ve hareket yerinde mi, algılanan performans iyi mi?
  - Formlar iyi mi: doğrulama, hatada girdinin korunması, çift gönderimin engellenmesi?
  - Bunların hepsi gerçek render ve gerçek etkileşimle kanıtlanmış mı?
- **Backend:**
  - API sözleşmesi tutarlı mı (isimlendirme, sürümleme, hata biçimi)? Girdi doğrulama ve yetkilendirme sınırda yapılıyor mu?
  - Idempotency ve retry güvenliği var mı? Transaction'lar, kalıcılık, migration ve geri alma düşünülmüş mü?
  - Güvenlik ele alınmış mı: secret, injection, veri sızıntısı, log gizliliği?
  - Zaman aşımı, hata işleme ve gözlemlenebilirlik var mı?
  - Performans riskleri (N+1, sınırsız sorgu) kontrol edilmiş mi?
  - Gerçek servisle entegrasyon testi var mı, yoksa yalnız mock mu?
- **Kod:** Doğru, okunabilir, mevcut koda uyumlu, gereksiz soyutlama yok, kenar durumları ve hata yolları testli, kapsam dışına taşmamış.
- **Plan ve görevler:**
  - Kullanıcının sözleri korunmuş mu?
  - Görevler küçük bir modelin tahmin yürütmeden uygulayabileceği kesinlikte mi?
  - Kabul ölçütleri gerçekten kaliteyi ölçüyor mu, yoksa yalnız "test geçti" mi diyor?
- **Kanıt ve inceleme:**
  - İnceleyici gerçekten kusur arıyor mu: edge case, güvenlik, UX?
  - Premium olmayan bir çıktı "DONE" olabiliyor mu? Olabiliyorsa hangi kural eksik?
- **Devir:** Sıfır bağlamlı bir ajan kalitede düşüş olmadan devam edebiliyor mu?

**Skill'in kaliteye etkisini ayrıca değerlendir:**
- `references/product-quality.md` ve SKILL.md'deki kalite kuralları premium çıktıyı gerçekten zorluyor mu? Yoksa yalnız bir taban mı tanımlıyor ve tavanı modele mi bırakıyor?
- Hangi kural eksik? Örnek: tasarım sistemi zorunluluğu, görsel inceleme ölçütleri, API sözleşme şablonu, performans bütçesi, güvenlik kontrol listesi, "premium" tanımının görev Acceptance'ına bağlanması.
- Koruma kuralları yaratıcılığı fazla mı kısıtlıyor, yoksa yeterince mi yönlendiriyor?

### C. Protokol kalitesi (SKILL.md + references)
- Küçük bir model (Haiku sınıfı) bu metni yanlış okumadan uygulayabilir mi? Şunları ara: belirsiz kelime, çelişen kural, tanımsız terim, cevapsız "ne zaman?" sorusu, sırası belirsiz adım.
- Aynı kural farklı yerlerde farklı ifade ediliyor mu?
- Frontmatter `description` doğru tetikleniyor mu? Gereksiz tetiklenen ve kaçırılan mesaj örnekleri üret: "devam et", "README'yi düzelt", "bu ne işe yarıyor?", "yayına hazırla", "şu ekranı güzelleştir", başka dilde istekler.
- Token maliyeti: Küçük işte ne kadar metin yükleniyor? Yalnız gerekeni okutma (progressive disclosure) gerçekten işliyor mu?

### D. Belge–kod tutarlılığı
- Belgede geçen her komut, bayrak, durum adı, alan adı, satır biçimi ve çıkış kodu kodda aynı mı? Koddaki her davranış belgelenmiş mi? `tests/test_docs.py` yalnız komut adlarını denetliyor; bayrakları, durumları ve biçimleri sen denetle.
- `design/v4-target.md` ile gerçek kod arasındaki farkları çıkar.

### E. Kod incelemesi (runtime/*.py, store.py, package.py)
- **Doğruluk:** görev dosyası okuma, header yazma, atomik yazım, digest, kabul kuralları, `--as`/`--takeover`, WAITING_USER, git geçmişinden kapanmış görev tespiti, ID üretimi, staleness/ADVANCED, `legacy` (yabancı sistem tespiti, aktarma bekçisi, taşıma, ignore ve işaretçi temizliği, `--drop-archive` bekçisi).
- **Kenar durumlar:** CRLF/LF, BOM, Unicode/emoji içerik ve yollar, boşluklu ve 260+ karakterlik yollar, büyük/küçük harf duyarsız dosya sistemi, boş veya yanlış Areas, büyük ya da binary dosyalar, binlerce dosyalı repo, bozuk header, tekrarlanan bölümler.
- **Platform:** Windows ve POSIX (WSL varsa gerçekten çalıştır), Python 3.11 ve sonrası, git yok, eski git.
- **Güvenlik:** Verify satırı üzerinden komut enjeksiyonu (shlex, .cmd/.bat, Windows batch argüman kaçışı), yol kaçışı ve symlink/junction, secret ortam değişkeni filtresi, log'lara sızan secret, `legacy --path` ile yanlış klasörün silinmesi, `--drop-archive` ile yanlış arşivin silinmesi, `.gitignore` ve talimat dosyası düzenlemesinin kullanıcı satırlarını bozması.
- **Süreç yönetimi:** ProcessTree (Windows JobObject, POSIX process group), zaman aşımı, öksüz kalan süreçler.
- **Bakım:** ölü kod, gereksiz karmaşıklık, test kapsamındaki boşluklar, kararsız (flaky) testler, runtime'ın 1.400 satırlık hedefi aşması.

### F. Durum makinesi
- Tüm görev ve boot durumlarını ve her geçişi hangi komutun yaptığını tabloya dök.
- Ulaşılamayan, çıkışı olmayan veya yanlış önceliklendirilen bir durum var mı?
- Aynı anda birden fazla koşul olduğunda boot doğru olanı seçiyor mu? Örnek: çakışma + bekleyen upload + kirli ağaç + LEGACY.

### G. Güven ve suistimal
- **Kendi işini onaylama yolları:** `--as`/`--reviewer` beyanı, Owner'ı elle değiştirme, Evidence/Review satırını elle yazma, Areas'ı daraltıp digest'i atlatma, Verify'ı `python -c pass` yapma, kutuyu kanıtsız işaretleme. Hangisini araç yakalıyor, hangisini yalnız protokol ya da inceleme?
- **Prompt injection:** Görev dosyası, AGENTS.md, README, devralınan yabancı plan dosyası veya bir kod yorumu zararlı talimat içerirse ne oluyor? Devralma sırasında yabancı sistemdeki metin "veri" olarak mı ele alınıyor?
- **Kötü niyetli veya bozuk proje:** Skill'in tehlikeli bir şey çalıştırmasına yol açılabiliyor mu?

### H. Senaryo testleri (geçici dizinde, mümkünse gerçek alt ajanlarla)
Her biri için beklenen davranış, gözlenen davranış ve aradaki fark:
1. Sıfırdan gerçek bir ürün; Genesis'ten ilk DONE'a kadar.
2. Görev ortasında çökme (Resume yazılmadan) → farklı model devralır.
3. İki ajan aynı repoda aynı anda "devam et" der.
4. Kullanıcı yokken kullanıcı kararı gerekir; sonra kullanıcı cevap verir.
5. İnceleme BLOCKED döner → düzeltme → yeniden inceleme (inceleyici ≠ düzeltici).
6. Kullanıcı ürün hedefini veya akışı yarıda değiştirir.
7. Yalnız görsel geri bildirim: "rengi ve yazıyı beğenmedim, daha premium olsun".
8. Küçük ama güvenlik veya veri içeren bir diff; hafif yola düşmemeli.
9. Yayın sırasında yanıt kaybı (`response_unknown`) → sonraki ajan.
10. Bu skill'le yazılmamış mevcut bir proje kopyası: kendi testleri, tasarımı, kirli çalışma ağacı.
11. Yabancı plan sistemleri: farklı şemalarda Project Brain, `PROJECT_BRAIN.md`, eski `.factory`, listede olmayan başka bir ajanın plan klasörü (`--path`). Aktarmada kayıp var mı, izleme tablosu eksiksiz mi, silme güvenli mi?
12. Git kenar durumları: merge çakışması, rebase, squash merge, shallow clone, detached HEAD, remote yok, push reddi, iki dalda aynı SA-NNN ID'si.
13. Git'siz klasör.
14. Kontrolden sonra pre-commit hook'un dosya değiştirmesi; imzalı commit zorunlu repo.
15. Kota veya oturum bitmesi; model ya da sağlayıcı değişimi (başka host'ta skill yolu ve `python` bulunurluğu).

### I. Benim öngörmediğim ama bu tür skill'lerde kontrol edilmesi gerekenler
Aşağıdakileri araştır ve kendi bulduğun ek riskleri de ekle:
- **Kalıntılar:** Project Brain'den hiçbir etkin kural, kurulum veya kırık bağlantı kaldı mı? Global talimat dosyaları ile store-automation SKILL.md çelişiyor mu?
- **Host farkları:** Claude Code, Codex, Gemini CLI, Cursor ve diğerlerinde skill yolu, `<directory of this SKILL.md>` çözümü, alt ajan varlığı ve araç izinleri.
- **Büyüme:** `runs/` disk kullanımı, Evidence/Review satırlarının görev dosyasını bütçeden taşırması, 25 açık görev sınırı, uzun ömürlü projede `git log` taramalarının yavaşlaması.
- **Zaman:** UTC damgaları, saat kayması, yaz saati.
- **Lisans ve atıf:** Project Brain (MIT) kodundan uyarlanan kısımların atfı.
- **Gizlilik:** loglara, Evidence notlarına ve commit mesajlarına kişisel veri veya secret sızması.
- **Güncelleme ve kaldırma:** Skills Manager güncellemesi dosya silmeyi gerektirdiğinde ne oluyor? Skill kaldırılınca projelerde ne kalıyor? Sürüm numarası değişmeden içerik değişirse ne oluyor?
- **İnsan deneyimi:** Kullanıcı hangi anlarda neyi görüyor? Raporlar anlaşılır mı? Gereksiz soru soruluyor mu, kritik soru atlanıyor mu? Kullanıcının dili korunuyor mu?

## Teslim biçimi (Türkçe)

1. **Yönetici özeti** (en fazla 10 satır): Premium üretime hazır mı? Hangi koşullarda kırılıyor? En kritik 3 risk ve en değerli 3 iyileştirme.
2. **Puan tablosu:** A–I alanları ve B'deki her premium ölçütü için 1–5 puan ve tek cümlelik gerekçe. A/B karşılaştırmasının sonucu ayrı bir satırda.
3. **Bulgular**, ciddiyete göre sıralı (BLOCKER / MAJOR / MINOR / ÖNERİ). Her bulgu için:
   - başlık ve CONFIRMED/PLAUSIBLE
   - kanıt: dosya:satır, komut, çıktı, ekran görüntüsü yolu
   - etkisi: hangi senaryoda ne bozuluyor ya da kalite nereden düşüyor
   - önerilen en küçük, kökten ve mevcut mimariye uygun düzeltme
4. **Premium açığı listesi:** Skill'in premium çıktıyı garanti etmek için eksik bıraktığı kurallar. Her biri için önerilen somut metin: SKILL.md, references veya görev şablonuna eklenecek cümleler ya da Acceptance maddeleri.
5. **Senaryo tablosu:** H'deki her senaryo için beklenen, gözlenen ve sonuç.
6. **Durum makinesi tablosu** (F).
7. **Kontrol edilmeyenler** ve nedeni.
8. **Öncelik sırası:** önce kırılanlar, sonra premium açıkları, sonra tutarlılık, en son iyileştirmeler.

Kod veya belge değiştirme; yalnız raporla.
