# Store Automation skill

Her uygulama kendi proje klasöründe, kendi Git deposu ve `.project-brain/` ile çalýþýr. Bu depo ortak aracýn geliþtirme kaynaðýdýr; uygulamalar buraya taþýnmaz.

## Codex içinde

Uygulamanýn klasörünü Codex’te aç ve yaz:

```text
$store-automation Bu projeyi incele, hatalarý düzelt ve test et.
```

Yeni uygulamada önce hedef klasörü ve fikrini söyle. Skill, mevcut `project-brain` skill’ini yükler; plan ve ilerleme seçilen projede tutulur. Konuþtuðun asistan normalde yürütücü/supervisor olur. Ayrý orkestratör her küçük görev için çalýþtýrýlmaz. Karmaþýklýða uygun persona ve model seçilir; basit iþlerde önce scripts/araçlar veya hafif model kullanýlýr.

## OpenCode içinde (isteðe baðlý)

PowerShell’de **uygulama klasöründen**:

```powershell
cd D:\repositories\uygulamam
python "$env:USERPROFILE/.codex/skills/store-automation/runtime/tool/factory.py" open
```

Üç native rol ve `/factory-start`, `/factory-resume`, `/factory-audit` bu oturumda yüklenir. Global/proje OpenCode config dosyalarý deðiþtirilmez. Worker scope’u kontratla sýnýrlandýrýlýr; inceleme ayrý oturumda yapýlýr.

## Dosyalar nerede?

```text
D:/repositories/uygulamam/
  .project-brain/       # bu projenin hedefi/görevleri/kaldýðý yer
  contracts/            # bu projenin görev kontratlarý
  .factory/runs/        # yerel loglar; Git ignore eklenir
  lib/, test/, ...      # uygulamanýn kodu
```

Yeni proje için kurulu CLI’nin `bootstrap D:/repositories/yeni-uygulama ...` komutu açýkça seçilen **yeni** klasörü oluþturur; mevcut klasörü reddeder. Starter’ýn Brain geçmiþini taþýmaz. Yeni Brain skeleton’ý DRAFT baþlar; kullanýcýnýn gerçek hedefiyle tamamlanýr. Eski Factory altýndaki test/probe klasörleri taþýnmadý.

## Abonelikler

Onaylý resmî CLI/subscription yollarý görev ihtiyacýna göre kullanýlabilir; model/persona ayrý seçilir. Ýlk seçim veya önceki kullanýcý yetkisi proje Brain’ine kaydedilir. Kota ya da hata, otomatik ücretli API veya hesap döndürme nedeni deðildir. [Güncel CLI envanteri ve yönlendirme](skills/store-automation/references/cli-routing.md).

Wrapper þu an ölçülmüþ ücretsiz OpenCode modelleri ve Codex/ChatGPT read-only handoff destekler. Diðer CLI’lar skill tarafýndan, kendi resmî izin/giriþ yöntemleri doðrulandýktan sonra kullanýlýr; evrensel adapter tamamlandý iddiasý yoktur. Wrapper’ýn `gate` komutu OpenCode native reviewer oturumunu doðrular; baþka host’un incelemesi kendi gerçek kanýtlarýyla kaydedilir.

## Skill kurulumu/güncelleme

Bu geliþtirme deposundan bir kez:

```powershell
python tool/install-skill.py
python -m unittest discover -s tests -v
```

Codex ve OpenCode global skill dizinlerine kendine yeterli kopyalar kurulur. Çalýþýrken bu kaynak depoya ihtiyaç yoktur. Kurulum yerel deðiþiklik yapýlmýþ skill dosyalarýný ezmez; mevcut global ayarlar korunur. Codex yeni skill’i listelemiyorsa yeni bir sohbet/oturum aç.

Uygulama starter/core kaynaklarý hâlâ `D:/repositories/napp_app_template` ve `D:/repositories/napp-core`; publishing protokolü `D:/AppPublishing/README.md`. Canlý maðaza/receipt ve iOS/Xcode ayrýca doðrulanýr. [Kurulum ve geçmiþ doðrulama raporu](docs/report.json).
