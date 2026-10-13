---
name: store-automation
description: Develop or adopt an application through early user feedback, integrated user journeys, proportionate specialist work, and evidence-based release preparation. Use for app delivery and maintenance; publishing requires the selected destination and existing operation authority.
metadata:
  version: "3.0.0"
---

# Store Automation

Native host üzerinde çalışan ürün teslim rehberi ve küçük Python doğrulama araçları. Zorunlu Project Brain/katalog preflight yoktur. Ürün, cihaz ve uzak yayın kabulü her görevde kendi gerçek kanıtını ister; kurulum bütün sağlayıcılarda çalıştırılmış görev anlamına gelmez.

## Kullanıcının sonucundan başla

Kullanıcının amacı, mevcut proje ve etkilenen gerçek akışı incele. Eksik kullanılabilirlik/hata ayrıntılarını tamamla; istenmemiş büyük özellik, backend, maliyet veya veri işlemi ekleme. Mevcut mimariyi, tasarım dilini, kararları ve çalışan entegrasyonları koruyarak sorunun ortak kök nedenini bul.

Görevi anlamadan katalog taraması, tam ürün anketi veya büyük ekip başlatma. Önce en küçük ilgili kaynak ve çalışan davranış incelemesiyle kapsam/risk belirle. Daha önce cevaplanmış kararları yeniden sorma. Mevcut Brain veya başka proje kaydı varsa bağlam ve devam için kullan; yeni plan sistemine geçişi işin önkoşulu yapma.

## Göreve uygun ilerle

- **Küçük yerel düzeltme:** yeniden üret, ortak kök nedeni düzelt, ilgili kontrolü çalıştır. Güvenlik/veri kaybı küçük diff olsa da yüksek risklidir. Mekanik iş için gereksiz ajan açma.
- **Akış değiştiren özellik:** etkilenen kullanıcı yolculuğunu ve durumları çıkar; pahalı kararları erken göster; önce bir çalışan uçtan uca dilim, sonra kalan kapsam.
- **Yeni ürün veya önemli belirsizlik:** önce en pahalı yanlış varsayımı test et. Bu bir UX prototipi, teknik deneme veya veri/yetki sözleşmesi olabilir. Bütün ekranları ya da backend'i doğrulanmamış varsayımla bitirme.
- **Mevcut projeyi benimseme:** gerçek kaynak, test, tasarım ve yayın düzeninden doğrulanmış başlangıcı çıkar. Çalışır görünen kodu geçmiş PASS ile kabul etme; eski planı sıfırlama.
- **Yayın/bakım:** mevcut üründeki ilgili kanıtı ve seçilmiş hedefi değerlendir; etkilenmeyen ürün kararlarını yeniden açma.

İlgili olduğunda [ürün kalitesi](references/product-quality.md) rehberini oku. Bütün referansları her küçük işte yükleme.

## Erken göster, sonra büyüt

Akış veya görsel yön belirsizse temsilî ekran/etkileşimi erken göster. İlk gerçek çalışan yolculuğu geniş uygulamadan önce, son paketi de yayın öncesinde göster. Gösterim, her küçük teknik işlem için izin istemek değildir. Kritik ürün tercihi gerekiyorsa cevapsızlığı kabul sayma; bağımsız işleri sürdür.

Yeni ürün, belirsiz akış, görsel yön veya mimari kararda ilk fikre kilitlenme: anlamlı biçimde farklı 2–3 yön çıkar, ödünleşimini kısa göster, en riskli varsayımı ucuz denemeyle seç. Koruma kuralları mevcut kararları ve kapsamı korur; yeni çözümün kalitesini veya özgünlüğünü sınırlamaz. Kalite listeleri tabandır, tavan değil.

Geri bildirimi görsel tercih, kullanılabilirlik, iş akışı, yanlış anlaşılmış ihtiyaç, teknik hata veya yeni kapsam olarak değerlendir. Paylaşılan bileşenleri ve bağlı ekran/veri/test/mağaza materyallerini birlikte izle. Yalnız değişiklikten etkilenen kanıtı yeniden üret; etki bilinmiyorsa belirsizliği açıkça tut.

## Uzmanlık ve yürütme

Karar, uygulama ve bağımsız kabul sorumluluklarını ayır; sabit büyük ekip kurma. Uzman; amacı, kesin kapsamı, kaynakları, somut teslimi, kabul ölçütünü, hata durumlarını ve gerçek izinlerini bilsin. Model/efor seçimi uzmanlık isminden ayrıdır. Mevcut host'un doğrulanmış araçlarını tercih et; başka CLI somut bir eksik yeteneği karşılıyorsa kullan.

Uzman görevlendirme, kota, rapor ve kesinti için [yürütme](references/execution.md) rehberine bak. Talimatla verilmiş kapsamı teknik sandbox garantisi sayma. Aynı çalışma alanındaki yazıcıları çakıştırma; bağımsız salt okunur işler veya izole alanlar paralel ilerleyebilir.

## Kabul

Komutun bitmesi, ajanın COMPLETED raporu, makine kontrolleri, kullanıcı yolculuğu ve yayın birbirinden ayrı sonuçlardır. Her gerekli kabul ölçütünü ilgili güncel gözleme bağla. Kaynak incelemesi görsel/cihaz davranışını, ekran görüntüsü gerçek etkileşimi, yerel test de uzak yayını tek başına kanıtlamaz.

Önemli davranış/veri/güvenlik değişikliği ve yayın adayında taze bağımsız inceleme kullan. Çözülmemiş zorunlu ölçüt veya engelleyici bulgu varken kabul etme. Gerekçeli, yetki içindeki küçük sınırlamalar açık kalabilir; etiket değiştirerek güvenlik veya veri kaybını küçültme. Yeni kanıt üretmeyen aynı inceleme/deneme döngüsünü tekrarlama.

Host ayrı inceleyici başlatamıyorsa bağımsız inceleme UNVERIFIED kalır; aynı oturumu başka adla inceleyici yapma. Kayıtlı `gate` akışı MEDIUM/HIGH risk, güvenlik/veri, yayın adayı veya başka oturuma devredilecek kabul içindir; küçük işte ilgili kontrol çıktısı ve kısa sonuç yeterlidir.

## Yayın ve devam

[Yayın rehberi](references/release.md) ile mevcut AppPublishing/Fastlane düzenini kullan. Yerel hazırlık, yükleme, incelemeye gönderim, kabul ve gerçek erişilebilirliği ayır. Var olan tam yetkiyi yeniden sorma; eksik dış işlem yetkisini ancak hazırlanan somut aday üzerinden tamamla. Ücretli API, credential içeriği okuma/aktarma ve otomatik billing/signing değişikliği yok.

Kesintide gerçek kaynak/diff, sahiplik, açık işlem, geçerli kanıt ve sonraki güvenli adımı koru. Devam kaydını projenin mevcut plan/Brain/docs düzenine yaz; yoksa `handoff` komutunu kullan. `.store-automation/runs/` yerel ve git dışıdır: başka makine veya bulut oturumu için kısa özeti projede görünür yere (mevcut notlar, PR açıklaması) de bırak. Yeni oturum önce git durumu/diff'i, sonra en yeni handoff kaydının `resume` alanını (RECONCILE_OWNER → READBACK_FIRST → INSPECT_DIFF) gerçek durumla uzlaştırarak sürdürür. Kalan dış engelleri ve neyin doğrulanmadığını somut bildir.


## Yerel araçlar ve sürüm geçişi

Çalışan komutlar, kayıt şemaları ve güven sınırı için [runtime rehberi](references/runtime.md); mevcut projeyi bozmadan sürüm yükseltmek için [geçiş rehberi](references/migration.md). Ana giriş mevcut host içindeki `$store-automation` çağrısıdır. `python "<skill>/store.py" --project "<uygulama>" doctor` yalnız yerel araç kontrolüdür. Native ajanları mevcut host başlatır; CLI ajan başlattığını veya bütün sağlayıcıları desteklediğini iddia etmez.
