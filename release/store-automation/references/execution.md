# Uzman yürütmesi, kanıt ve devam

## Görevlendirme

Uzman ancak net teslim veya bağımsız inceleme ihtiyacı varsa açılır. Brief şunları içerir: kullanıcı amacı/bağlamı, uzmanlık, kesin görev/kapsam, ilgili kaynak ve çağıranlar, teslim, ölçülebilir kabul, beklenen hatalar, bağımlılık/sözleşme, gerçek araç/yazma yetkileri, zaman/bağlam/çıktı bütçesi ve engelde sonraki adım. Genel “dünya çapında uzman” persona yerine işe özgü yetkinlik ve kontrol ver.

Uzmanlık, model ve effort ayrı kararlardır. Açıklanan budget gerçek kullanım değildir; bilinmeyen kullanım null'dır. Mevcut host gerçek model/eforu açıklamıyorsa inherited/unknown de, isim uydurma. Başlatmadan önce rol, iş, seçimin gerekçesi ve önemli sınırı kullanıcıya kısa anlat; sonucu ve engeli de bildir.

Mevcut resmi abonelik/host araçlarını kullan. Katalog erişimi, login, model entitlement, görev yeteneği, kota ve izin farklıdır. Sırf kurulu/listeleniyor diye çalışır sayma. Kota bilgisi mevcut araçtan tazelenir; bilinmeyen/koruma eşiğinin altındaki paylaşılan kotayla yeni worker açma. Ücretli API veya sessiz kalite düşürme yok. Katalog keşfi işin önünde zorunlu küresel ritüel değildir.

## İzin ve sahiplik

Prompt'taki “yalnız şu dosyayı yaz” gerçek erişim denetimi değildir. Requested scope ve enforced scope ayrı kaydedilir. Host dar yazma sınırı uygulayamıyorsa güvenli seçenek read-only öneri/patch veya incelenmiş izole checkout'tur. Aynı kullanıcıya ait worktree, credential erişimine karşı güvenlik sandbox'ı değildir.

Ortak checkout'ta tek yazıcı. İzole ayrık işler paralel olabilir; veri/API sözleşmesi çakışıyorsa bağımsız kabul edilmez. Entegrasyon sahibi difflere ve birleşmiş davranışa bakar. Bilinmeyen kullanıcı düzenlemesi korunur.

## Sonuç ve kabul ayrımı

- Süreç bitti: yalnız transport/process sonucu.
- Uzman COMPLETED dedi: doğrulanacak rapor.
- Makine kontrolleri geçti: belirtilen kaynak/ortamda belirtilen komutların sonucu.
- Yolculuk kabulü: gerekli davranış/görsel/erişilebilirlik ölçütlerinin uygun gözlemi.
- Yayın sonucu: hedef uzak sistemin geri okuması; kullanılabilirlik ayrıca gözlenir.

Rapor atanan task/project/rol ve bilinen gerçek route ile eşleşmeli; bilinmeyen durum başarı sayılmaz. Bağımsız inceleme kökeni sağlayıcıya özel kimlik regex'iyle evrenselleştirilmez. Atama ile native sonuç ilişkilendirilir. Mevcut host bunu kanıtlayamıyorsa otomatik köken onayı verilmez.

Her kriterin kanıtı kendi kapsamıyla tutulur. Eksik kanıt `UNVERIFIED`, başarısız kriter `FAIL` olur. Güncel hash bile sahte/yanlış gözlemi doğru yapmaz. Ekran ve servis kanıtı uygun araçla gerçekten incelenir. Kabul edilmesi yetki içinde olan küçük bulgu gerekçesiyle kalabilir; zorunlu şartın ihlali minor diye geçemez.

## Kesinti, başarısızlık ve tekrar

Önce gerçek çalışan süreç/atama ve sahipliği incele. Erişim reddi süreç öldü demek değildir. Yalnız sahip olunan süreç durdurulur; eski yazıcı bitmeden yerine yenisi açılmaz. Kısmi diff, rapor, kanıt ve bilinmeyen kullanıcı işi korunur.

Devam kaydı: görev ve son gereksinim, gerçek dosya/diff, çalışan veya durumu bilinmeyen sahipli süreç, son geçerli kanıt, ilk başarısız/eksik kriter, bekleyen dış etki ve **sonraki güvenli eylem**. Sadece sonraki checkbox yeterli değildir. Yeni oturum bunları yeniden uzlaştırır.

Kota/erişim/model/araç hatasını birbirine karıştırma. Yeni kanıt üretmeyen aynı çağrıyı tekrarlama. Kısmi işlemden sonra kör fallback/replay yok. Dış çağrıda yanıt kayıpsa tekrar önce uzak durum sorgulanır. Eşdeğer izin ve yeterlilik yoksa iş bloke kalır; ilgili olmayan yetkili işler sürer.

## Ölçüm

Yeni telemetri servisi kurma; mevcut deneme kayıtlarına zaman damgaları ekle: ihtiyaç alındı, ilk yararlı çıktı, worker başlangıç/bitiş, kontrol, geri bildirim, rework ve kabul. Analiz/yürütme/bekleme/yeniden işleme sürelerini yalnız gözlenen olaylardan çıkar; paralel süreleri toplam duvar süresi diye toplama.

Parent/worker/retry kullanımını ancak kapsama ve authoritative counter yeterliyse topla. Eksik giriş varsa toplam null veya açık kısmi toplamdır. Hesap kotasındaki değişim bu görevin token harcaması değildir. Önce/sonra karşılaştırmasında aynı sınıfta görev, aynı gerekli kalite, benzer kaynak/ortam ve tüm başarısız denemeler bulunmalıdır.
