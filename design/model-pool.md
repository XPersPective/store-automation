# Model havuzu kararı — 4.2.0

Kullanıcı hedefi: "bunu da ekle ve güncelle ... kontrolleri iyi yap ... versiyonu yükselt ... GitHub hem yerel".
İlerleme yalnız HANDOFF.md içindedir; bu belge tasarım ve kanıt sınırlarını tutar.

## Karar

Üç seçenek karşılaştırıldı: (1) her boot'ta web tarama ve sağlayıcı çağrıları: token, credential ve offline
kısıtlarını ihlal eder; (2) skill paketine sabit H/M/L listesi: kişisel erişimi karıştırır, güncellemede
kayıp ve bayatlık yaratır; (3) kullanıcı dizininde sürümlü kanıt/erişim kaydı + ajanın hedefli araştırması:
seçildi. Runtime stdlib ile offline kalır; yeni bağımlılık, daemon, sağlayıcı SDK veya gizli dosya taraması yok.

Kayıt modeli: benchmark/version/harness/effort + açık dış referans ve eşikler; modelin aynı effort'taki
sonuçları; ortak hesap havuzları; ayrı host erişimleri; kullanıcı istisnası; araştırma hata/backoff;
karşılaştırılabilir kabul edilmiş iş tüketimi ve ayrı benchmark ön tahmini. Proje planı kullanıcı
envanterini kopyalamaz. Paket güncellemeleri kullanıcı kaydına dokunmaz.

Varsayılan öneri modu; açık `enforce: true` paylaşılan start/review/accept fonksiyonlarında rol denetimi
yapar. Üçüncü aşama uygulanmıştır fakat kullanıcının gerçek projelerinde henüz gözlenmemiş veriyle
zorunlu yapılmamıştır. Kurulu ajan sayısı model erişimi değildir. Düşük modelle gizli geri dönüş yok.

## Araştırmada düzeltilen varsayımlar

- Terminal-Bench 2.x sabitlenmedi: [güncel 4.0 sayfası](https://www.tbench.ai/?version=4) var.
- [SWE-bench](https://www.swebench.com/) aynı mini-SWE-agent ortamındaki Verified sonuçlarını sunuyor.
  Modelin üretici sistemindeki skoru farklı bir harness ile eşit kabul edilmez.
- İlk yerel dört profil için [AA high karşılaştırması](https://artificialanalysis.ai/models/comparisons/gpt-6-1-sol-high-vs-gpt-6-astra-high)
  ve [5.6 karşılaştırması](https://artificialanalysis.ai/models/comparisons/gpt-5-6-sol-high-vs-gpt-5-6-terra-high)
  okundu. Intelligence Index 4.3.2 ve AA'nın Terminal-Bench 4.0 değerlendirmesi ayrı ölçeklerde tutuldu.
  Dış güçlü referans Astra-high; başlangıç H/M sınırı referansın %90/%70'i. Bu bilimsel sertifika veya
  tüm dünya lideri iddiası değildir; ilk konservatif politika tahminidir. İki boyut aynı değerlendirme
  ailesinden gelebilir, istatistiksel bağımsızlık iddiası yoktur; `independent` üreticiden bağımsız demektir.
- Benchmark görev maliyeti yerel kabul edilmiş görev maliyeti değildir. Yerel ölçüm yoksa null.
- Abonelik pencereleri ortak kota; güncel fiyat ve sıfır token fiyatı kota garantisi değildir.

## Kontrol kapsamı

tests/test_models.py: dış referans/rol ayrımı, bayat/manufacturer/effort kanıtı, yetki/araç/bağlam/kota/fiyat,
tam ve karşılaştırılabilir tüketim, atomik revizyonlu birleştirme, başarısız importta byte koruma,
bozuk skaler/NaN/dev sayı/duplicate JSON/derin JSON/boş dosya/linked temp, backoff ve açık istisna,
shared runtime start/review/accept, alias bağımsızlığı, CLI ilk kullanım→merge→select→boot.
Mevcut 54 test korunur; Node referans kontrolü ve paketli CLI ayrıca çalıştırılır.

Bağımsız salt okunur inceleme boş dosyada fail-open, alias ile kendi incelemesi, malformed timestamp/id,
dev sayı, normalize edilmemiş ID ve derin JSON hatalarını yakaladı; hepsine aynı ortak sınırda düzeltme
ve regresyon kontrolü eklendi. İnceleyici kaynak yazmadı.

## Açık sınırlar

Kimlik, kaynak kontrolü ve kullanıcı istisnası beyana dayanır; aynı OS kullanıcısına karşı güvenlik sınırı
değildir. H tahmini onayın metnini değerlendirmez. Araç prose görevden bağlam/araç çıkarmaz; ajan parametre
geçer. Gerçek projelerden tam token/yeniden deneme verisi henüz yok; ekonomi sıralaması için ölçüm gerekir.
Mevcut kotayı göstermeyen sağlayıcılar otomatik seçimde UNKNOWN kalır. Başka host'ta model değiştirme
yeteneği yoksa öneri kullanıcıya iletilir. Yeni ücretsiz sağlayıcı modellerinin sadece katalogda görünmesi
doğrulanmış erişim sayılmaz. Runtime satır bütçesi daha da aşılmıştır; korumalar silinerek küçültülmedi.
