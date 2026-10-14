# Bağımsız denetim promptu — Store Automation 4

Aşağıdaki metni olduğu gibi başka bir ajana ver. Ajan bu konuşmanın geçmişini bilmez; ihtiyaç duyduğu her şey burada ve repoda.

---

## Rolün

Sen ajan skill'leri (Claude Code / Codex / Gemini / Cursor skill'leri) için kıdemli bir denetçisin: yazılım mimarı, güvenlik inceleyicisi, ürün kalitesi uzmanı ve küçük modellerin talimat takip davranışını bilen bir değerlendirici. Görevin `store-automation` skill'inin, iddia ettiği şeyi **gerçekten** yapıp yapmadığını kanıtla bulmak. Nezaket değil kanıt önemli. Belgedeki iddiaya, testlerin geçmesine veya önceki raporlara güvenme; her sonucu kendin gözle, çalıştır, yeniden üret.

## Bağlam

- Kaynak repo: `D:/repositories/store-otomaston` (dal `master`). Önce `AGENTS.md`, `HANDOFF.md`, `README.md`, `design/v4-target.md` (hedef H1–H9, tasarım brief'i, mimari, P6 sonucu), `design/validation-report.md` oku.
- Dağıtılan paket: `release/store-automation/` (SKILL.md, store.py, runtime/, references/, package-manifest.json). Kurulu kopyalar Skills Manager ile 41 ajana + 4 ek dizine dağıtılmış durumda (merkez: `~/.skills-manager/skills/store-automation`).
- Skill'in vaadi: bir uygulama fikri veya mevcut proje verildiğinde güçlü model ürünü/mimariyi/risk sıralı aşamaları planlar; küçük modeller tam tarifli görevleri uygular; her görev güncel kaynağa bağlı kanıt ve gerektiğinde bağımsız inceleme olmadan kapanmaz; herhangi bir anda kesilen işi başka bir ajan (başka model/sağlayıcı, sohbet geçmişi yok) yalnız repodan doğru yerden devralır; seçilen platformda yayına kadar götürür. Durum `.store-automation/` dosyalarında ve git commit trailer'larında tutulur. Project Brain'in plan/devam/harita mekanizması bu skill'e sentezlendi.
- Kullanıcı kararları: push otomatik; plan dosyalarında başlıklar İngilizce, içerik kullanıcının dilinde; ücretli API, credential içeriği okuma, billing/signing değişikliği ve seçilmemiş üretim yayını yasak.

## Kurallar

1. **Salt okunur başla.** Kaynak repoda, kurulu skill kopyalarında, `D:/repositories` altındaki gerçek kullanıcı projelerinde ve Skills Manager kaydında hiçbir şeyi değiştirme, commit/push/deploy yapma. Deneyleri yalnız kendi geçici dizininde (repoyu veya paketi oraya kopyalayarak) yap.
2. Ücretli API yok, ağdan paket kurma yok, credential/secret dosyası açma yok.
3. Alt ajan başlatabiliyorsan farklı güçte modellerle (güçlü + küçük) gerçek senaryo koş; başlatamıyorsan bunu açıkça yaz ve senaryoyu kendin, her rolü ayrı ve yalnız repo dosyalarını okuyarak oyna.
4. Her bulgu kanıtlı olmalı: dosya:satır, çalıştırdığın komut, gözlenen çıktı veya yeniden üretim adımı. Kanıtsız şüpheyi "PLAUSIBLE" diye ayrı işaretle; "CONFIRMED" yalnız yeniden ürettiklerin içindir.
5. Bulamadığın veya kontrol edemediğin şeyi saklama; "kontrol edilmedi" listesine yaz.

## Denetim alanları

Her alanda önce iddiayı çıkar, sonra karşı örnek ara.

### A. Hedefe uygunluk
- H1–H9 başarı koşullarının her birini kendi deneyinle yeniden ölç. P6 raporundaki "karşılandı" iddialarını tekrar üret; "kısmi" olanları (H5 devralma, H6 dış işlem, H8 POSIX, H9 bütçe) derinleştir.
- Skill uçtan uca iş bitiriyor mu: boş repo → Genesis → M1 görevleri → uygulama → kanıt → inceleme → DONE → sonraki görev → final audit. Zincirin koptuğu, ajanın "ne yapacağını bilemediği" her noktayı yaz.

### B. Protokol kalitesi (SKILL.md + references)
- Küçük bir model (ör. Haiku sınıfı) bu metni yanlış okumadan uygulayabilir mi? Belirsiz kelime, çelişen iki kural, tanımsız terim, "ne zaman" sorusu cevapsız kalan karar noktası, sıralaması belirsiz adım ara.
- Aynı kural birden fazla yerde farklı ifade ediliyor mu? Bir referans diğerini geçersiz kılıyor mu?
- Skill frontmatter `description` doğru tetikleniyor mu? Gereksiz yere tetiklenen veya tetiklenmesi gerekirken kaçırılan mesaj örnekleri üret ("devam et", "README'yi düzelt", "bu ne işe yarıyor?", "yayına hazırla", başka dilde istekler).
- Token maliyeti: küçük işte ne kadar metin yükleniyor? Progressive disclosure (yalnız gerekeni okut) gerçekten işliyor mu?
- Yaratıcılık ve kalite dengesi: koruma kuralları yeni ürün/mimari/tasarımda modeli sıradan çözüme mi itiyor, yoksa "2–3 farklı yön" kuralı gerçekten premium çıktı üretiyor mu? Gerçek bir Genesis çıktısını aşağıdaki "premium" ölçütüyle puanla.

### C. Belge–kod tutarlılığı
- Belgede geçen her komut, bayrak, durum adı, alan adı, satır biçimi ve çıkış kodu kodda aynı mı? Koddaki her davranış belgelenmiş mi? (`tests/test_docs.py` yalnız komut adlarını denetliyor; bayrakları, durumları, biçimleri sen denetle.)
- `design/v4-target.md` mimarisi ile gerçek kod arasındaki farkları çıkar.

### D. Kod incelemesi (runtime/*.py, store.py, package.py)
- Doğruluk: task parse, header yazma (`set_header`, `append_section`), atomik yazım, digest hesabı, kabul kuralları, git geçmişinden kapanmış görev tespiti, ID üretimi, staleness/ADVANCED, legacy dönüşümü.
- Kenar durumlar: CRLF/LF karışık dosyalar, BOM, Türkçe/Unicode/emoji içerik ve yol adları, boşluklu yollar, Windows 260+ karakter yolları, büyük/küçük harf duyarsız dosya sistemi, boş Areas, çok büyük veya binary dosyalar, binlerce dosyalı repo (performans), eksik bölümler, bozuk header, iki kez aynı başlık.
- Platform: Windows ve POSIX (WSL varsa gerçekten koş), Python 3.11 ve daha yenisi, git yok, git eski sürüm.
- Güvenlik: Verify komutu üzerinden komut enjeksiyonu (shlex, .cmd/.bat çalıştırma, Windows batch argüman kaçışı), yol kaçışı ve symlink/junction, secret ortam değişkeni filtresi ve log'lara sızan secret, `runs/` loglarının git'e kaçma ihtimali, `legacy`'nin yanlış dosyayı taşıma ihtimali, `.gitignore` düzenlemesinin kullanıcı satırlarını bozma ihtimali.
- Süreç yönetimi: ProcessTree (Windows JobObject, POSIX process group), timeout, alt süreçlerin öksüz kalması.
- Bakım: ölü kod, gereksiz karmaşıklık, test kapsamı boşlukları, kararsız (flaky) test.

### E. Durum makinesi
- Tüm görev durumlarını (PLANNED, READY, IN_PROGRESS, REVIEW, BLOCKED, DONE) ve boot durumlarını (NO_PLAN, RESUME, INTERRUPTED, DIRTY, ADVANCED, CONFLICTED, READBACK_FIRST, NO_GIT) çıkar. Her geçişi hangi komutun yaptığını tabloya dök. Ulaşılamayan, çıkışı olmayan veya yanlış önceliklendirilen durum var mı? Aynı anda birden fazla koşul varken (ör. çakışma + bekleyen upload + kirli ağaç) boot doğru olanı mı seçiyor?

### F. Güven ve suistimal
- Kendi işini onaylama yolları: `--as`/`--reviewer` beyanı, Owner'ı elle değiştirme, Evidence/Review satırını elle yazma, Areas'ı daraltıp digest'i atlatma, Verify'ı `python -c pass` yapma, acceptance kutusunu kanıtsız işaretleme. Hangisini araç yakalıyor, hangisini yalnız protokol/inceleme?
- Prompt injection: repodaki bir görev dosyası, AGENTS.md, README veya kod yorumu ajana zararlı talimat verirse skill bunu nasıl ele alıyor? Başka ajanın yazdığı görev dosyasındaki komut "talimat" mı "veri" mi?
- Kötü niyetli veya bozuk proje: skill'in tehlikeli bir şey çalıştırmasına yol açılabiliyor mu?

### G. Senaryo testleri (geçici dizinde, mümkünse gerçek alt ajanlarla)
En az şunları dene; her biri için beklenen davranış, gözlenen davranış ve fark:
1. Sıfırdan küçük ama gerçek bir ürün (ör. web veya CLI) — Genesis'ten ilk DONE'a kadar.
2. Görev ortasında çökme (Resume yazılmadan) → farklı model devralır.
3. Aynı anda iki ajan aynı repoda "devam et" der (paralel yazıcı).
4. Kullanıcı yokken kullanıcı kararı gereken görev; sonra kullanıcı cevap verir.
5. İnceleme BLOCKED döner → düzeltme → yeniden inceleme (inceleyici ≠ düzeltici).
6. Kullanıcı ürün hedefini/akışını yarıda değiştirir.
7. Yalnız görsel geri bildirim ("rengi beğenmedim").
8. Küçük ama güvenlik/veri içeren diff (hafif yola düşmemeli).
9. Yayın sırasında yanıt kaybı (`response_unknown`) → sonraki ajan.
10. Mevcut, bu skill'le yazılmamış proje (kopyası): kendi testleri, tasarımı, kirli çalışma ağacı.
11. Eski 2.x `.factory` ve Project Brain `.project-brain` içeren proje kopyası → `legacy`.
12. Git kenar durumları: merge çakışması, rebase sonrası, squash merge, shallow clone, detached HEAD, remote yok, push reddi, iki dalda aynı SA-NNN ID'sinin üretilmesi ve birleştirilmesi.
13. Git'siz klasör.
14. pre-commit hook'un dosyayı değiştirmesi (check sonrası digest bayatlaması), imzalı commit zorunlu repo.
15. Kota/oturum bitmesi, model veya sağlayıcı değişimi (başka host'un skill yolu ve `python` bulunurluğu).

### H. Benim (kullanıcının) öngörmediğim ama bu tür skill'lerde kontrol edilmesi gerekenler
Aşağıdakileri de araştır ve kendi bulduğun ek riskleri ekle:
- **Skill çakışması:** Project Brain skill'i hâlâ 41 ajanda kurulu ve tetikleyicisi "devam et"; kullanıcının global `~/.claude/CLAUDE.md` dosyası `.project-brain` olan projelerde Brain'i zorunlu tutuyor. Aynı mesajda iki skill çakışınca ne oluyor? Hangi kural kazanıyor, ajan tutarlı davranıyor mu?
- Host farkları: Claude Code, Codex, Gemini CLI, Cursor ve diğerlerinde skill yolu, `<directory of this SKILL.md>` çözümü, alt ajan varlığı, araç izinleri.
- Büyüme: `runs/` disk kullanımı, Evidence/Review satırlarıyla görev dosyasının bütçeyi aşması, 25 açık görev sınırı, uzun yaşayan projede `git log` taramalarının yavaşlaması.
- Zaman: UTC damgaları, saat kayması, yaz saati.
- Lisans ve atıf: Project Brain (MIT) kodundan uyarlanan kısımların atfı.
- Gizlilik: loglar, Evidence notları ve commit mesajlarına kişisel veri veya secret sızması.
- Güncelleme ve kaldırma: Skills Manager güncellemesi silme gerektirince ne oluyor, kullanıcı skill'i kaldırınca projelerde ne kalıyor, eski paket hash'leriyle yeni paketin ayırt edilmesi.
- İnsan deneyimi: kullanıcı hangi anlarda neyi görüyor, raporlar anlaşılır mı, gereksiz soru soruluyor mu, kritik soru atlanıyor mu?

## "Premium kalite" ölçütü (her aşamanın çıktısı için 1–5 puan ver, gerekçesiyle)

- Plan/Genesis: kullanıcının sözleri korunmuş mu, gerçek riskler önce mi, alternatifler gerçekten farklı mı, görevler küçük modelin tahmin yürütmeden uygulayabileceği kesinlikte mi?
- Mimari: basit, gerekçeli, mevcut/native çözümleri tercih eden, veri kaybı ve hata yollarını kapsayan.
- Kod: doğru, okunabilir, testli, kenar durumları ele alan, kapsam dışına taşmayan.
- UX/ürün (UI varsa): gerçek render ve etkileşimle kontrol edilmiş durumlar, erişilebilirlik, tutarlı tasarım dili.
- Kanıt/kabul: iddia ile kanıt birebir mi, bayat kanıt yakalanıyor mu?
- Devir: sıfır bağlamlı ajan gerçekten kaldığı yerden devam edebiliyor mu?
- Yayın: platforma özgü kanıt ve geri okuma ayrımı.

## Teslim biçimi (Türkçe)

1. **Yönetici özeti** (en fazla 10 satır): üretime hazır mı, hangi koşullarda kırılıyor, en kritik 3 risk.
2. **Puan tablosu:** A–H alanları ve premium ölçütleri için 1–5 puan + tek cümle gerekçe.
3. **Bulgular**, ciddiyete göre sıralı (BLOCKER / MAJOR / MINOR / ÖNERİ). Her bulgu için: başlık, CONFIRMED/PLAUSIBLE, kanıt (dosya:satır, komut, çıktı), etkisi (hangi senaryoda ne bozuluyor), önerilen en küçük düzeltme.
4. **Senaryo tablosu:** G'deki her senaryo için beklenen / gözlenen / sonuç.
5. **Durum makinesi tablosu** (E).
6. **Kontrol edilmeyenler** ve nedeni.
7. Önerilen düzeltmelerin öncelik sırası (önce kırılanlar, sonra tutarlılık, en son iyileştirme).

Kod veya belge değiştirme; yalnız raporla. Düzeltme önerilerin küçük, kökten ve mevcut mimariye uygun olsun.
