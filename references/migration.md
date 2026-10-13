# Sürüm yükseltme ve proje devralma

3.0.0, eski 2.x factory komutlarıyla uyumlu bir drop-in runner değildir. Skill adı store-automation kalır; yönetici mevcut native host'tur. Eski factory.py/providers/Brain-first zinciri kaldırılmıştır. Yeni deterministik giriş store.py; [komutlar](runtime.md). Eski start komutunu sessizce başka iş yapan komuta yönlendirme.

## Var olan uygulamayı devralma

1. Seçilmiş uygulamanın git durumu, ilgili kaynak/çağıran, test, tasarım ve yayın düzenini incele. Kısa envanter: çalıştırma/build/test komutları ve gerçek sonuçları, hedef platformlar, veri depoları ve şemalar, tasarım token/bileşen kaynağı, yayın lane'leri, mevcut plan/devam kayıtları. Secret içeriği değil yalnız varlığı/konumu not edilir. Çalışan hiçbir kontrol yoksa değişiklikten önce en küçük gerçek smoke check'i kur ve sonucunu kaydet. Bilinmeyen diff'i koru. Mevcut plan ve Brain kayıtları varsa tarihçedir; yeniden init veya plan sıfırlama yapma.
2. Son kullanıcı ihtiyacı ve ilk tamamlanmamış kriteri çıkar. 2.x izi varsa önce kaldır: `store.py --project <app> legacy` envanteri (dosya/boyut, eski handoff adları, .gitignore satırları, arşiv yolu) gösterir; eski handoff'larda açık iş varsa özetini yeni devam kaydına al, sonra `legacy --apply`. Komut `.factory/` ve `.factory-bootstrap.json`'u tek rename ile proje yanındaki `store-automation-legacy-archive/<proje>-<zaman>` altına taşır, `.factory` ignore satırlarını kaldırıp `.store-automation/` ekler, `migration` kaydı yazar. Git'te izlenen eski dosya, bağlı yol veya açık dosya/çalışan süreç varsa hiçbir şey taşımadan durur. Project Brain dosyaları ayrı skill'e aittir, dokunulmaz. Eski receipt'ler yeni şemaya PASS olarak taşınmaz; arşiv artık gerekmediğinde silinebilir. Yeni görev ve public kaynak snapshot'ı oluştur.
3. Ajan sahipliğini host'tan uzlaştır. Durdurulduğu bilinmeyen yazıcıyı yenisiyle çakıştırma. Belirsiz upload varsa mevcut yayın aracından readback yapmadan replay etme.
4. En küçük gerçek akışı tekrar çalıştır. Uyumlu kaynak, napp/Fastlane, tasarım ve testler korunur. Yeni klasör veya backend sırf şablon için uygulanmaz.
5. Devir kaydına durum, source/evidence, owner, pending effects ve sonraki güvenli işi yaz. Yer değişikliği project kimliğini değiştirir; eski receipt'i düzenlemek yerine yeni konum için taze kanıt üret.

## Skill paketini yükseltme

Kaynak ile kurulu paket ayrıdır. package.py yalnız SKILL.md, store.py, runtime Python ve reference Markdown dosyalarını yeni boş hedefe kopyalar; hash manifesti bırakır. Eski hedef üzerine yazmayı reddeder. Paket bağımsız dizinde doctor ve ilgili kontrollerle sınanır. Python 3.11+ gerekir; Node yalnız JS regresyon testi içindir.

Skills Manager kaydı varsa aynı id/tags/preset/deployment korunarak kaynak güncellenir. Bu repository'nin release/store-automation paketi kullanılır. Git URL/branch/subpath değişimi kaydedilir. Mevcut kaydı remove+install yapma. Yönetilmeyen kopyaların yalnız bu skill'e ait olduğu manifestle kontrol edilir. Kullanıcı özel içeriği önce yedeklenir; sessizce kaybolmaz.

Sıra: çalışan işleri bitir → envanter → repo dışında yedek → restore denemesi → aday kabulü → kaynak geçişi → merkez/ajan dağıtımı → manifest hashleri → launcher/doctor → GitHub readback. Kesilirse migration kaydı yeni/eski/unknown hedefleri tutar; rename/commit/upload kör tekrar edilmez.

Rollback: yeni kaynak ve kurulumları ayrı yere al, yedekteki dosyaları geri koy. Git geçmişi, bilinmeyen diff ve Skills Manager metadata yedeğini koru. Canlı yazıcı veya değişmiş hedef varsa önce sahipliği/diff'i çöz. Başka uygulamanın veri şemasına otomatik migration yapma.
