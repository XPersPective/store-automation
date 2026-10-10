# Store Automation

[![Portable checks](https://github.com/XPersPective/store-automation/actions/workflows/checks.yml/badge.svg)](https://github.com/XPersPective/store-automation/actions/workflows/checks.yml)

Flutter projelerini incelemek, geliştirmek ve mağazaya hazırlamak için global bir Codex/OpenCode skill’i. Her proje kendi klasöründe, kendi Git deposu ve Project Brain’iyle çalışır.

## Hemen kullan

Codex’te uygulamanın klasörünü aç ve yaz:

```text
$store-automation Bu projeyi incele, kaldığı yerden devam et ve hataları düzelt.
```

Terminalde aynı proje klasöründen:

```powershell
store-automation
# Belirli bir hedefle:
store-automation start "Bu projeyi incele ve testleri geçen bir sürüme getir"
# Resmî Codex CLI ile:
store-automation start --host codex "Bu projeyi incele ve devam et"
```

Komut, bulunduğun klasörü seçer. Brain varsa yükler; yoksa mevcut dosyaları koruyarak Genesis iskeleti oluşturur. Yeni hedef DRAFT başlar; ürün hedefi uydurulmaz. Mevcut Codex sohbetinde ikinci bir yönetici açılmaz.

## İş akışı

```mermaid
flowchart LR
    A[Mevcut projeyi tara / Brain yükle] --> B[Görev + kapsamlı persona]
    B --> C[Uygun doğrulanmış araç / model]
    C --> D[Sıralı uygulama]
    D --> E[Makine kontrolleri]
    E --> F[Yeni bağımsız inceleme]
    F --> G[Kanıt + checkpoint]
    G --> H[Yayın hazırlığı]
```

Basit doğrulamalar önce betiklerle yapılır. Model ve persona ayrı seçilir; kalite eşiği token tasarrufu için düşürülmez. Kota/hata sonrası değişiklikler uzlaştırılmadan görev başka modele körlemesine aktarılmaz. Bir projede tek Brain ve tek otomatik uygulama görevi vardır.

## Ajanları gör ve müdahale et

OpenCode görev çalıştırıcısında `run --visible`, gerçek oturumlar için Windows Terminal bölmeleri açar. Yönetici, çalışan ve inceleyen ayrı native oturumlardır; ajanlar durumlarını ana yöneticiye bildirir. Görev tamamlandığında yalnız o görevin sunucusu kapanır, oturum geçmişi ve kanıtlar kalır.

```powershell
store-automation activity
store-automation providers
```

`activity` görev/persona rolü, sağlayıcı/model, süreç durumu ve sağlayıcının bildirdiği token kullanımını gösterir. Bilinmeyen kota ve kullanım alanları bilinmeyen kalır. Codex/Claude/Gemini oturumları kendi native arayüzlerinden izlenir; OpenCode’a zorunlu bağımlılık yoktur. [Canlı ajanlar ve müdahale](skills/store-automation/references/live-agents.md).

## Projeye ait dosyalar

```text
uygulamam/
  .project-brain/       # hedef, mimari, görevler ve devam noktası
  contracts/            # göreve özel persona / izin / kabul ölçütleri
  .factory/runs/        # yerel çalışma kanıtı; Git dışında
  lib/, test/, ...      # uygulamanın kodu
```

Başka projenin görevleri veya oturumları taşınmaz. `adopt` yalnız mevcut projeyi yükler. `bootstrap <yeni-klasör> --name "Ad" --package com.example.ad --ads no --pro no` açıkça seçilmiş yeni klasör oluşturur; mevcut projeyi ezmez. Yeni projeler normalde Factory’nin altında değil, diğer projelerin yanında tutulur.

## Şablon ve yayın

napp çekirdeği tema, kalıcı dil seçimi, yerelleştirme, hakkımızda, gizlilik, lisanslar ve mağaza/paylaşım servislerini sağlar. Reklam/Pro modülleri seçmelidir; kapalı modüllerin bağımlılıkları üretilen uygulamaya eklenmez. iOS paylaş/puan ver bağlantısı gerçek App Store ID ister. Bulut veri modu doğru gizlilik metnine bağlanır. Yeni paketler yalnız somut ihtiyaca göre eklenir.

Yayın dosyalarının tek kaynağı `D:/AppPublishing/README.md` protokolü; kaynak projeye ikinci katalog veya gizli bilgi şeması kurulmaz.

```powershell
store-automation release-preflight . --app-id uygulamam --platform android --locale tr-TR --locale en-US
```

Kontrol; kaynak kimliği/sürümü, derleme hash’i, mağaza metinleri ve görsel başlıklarını inceler. İmza, gerçek cihaz, mağaza beyanları, hesap yetkisi ve uzak sürüm ayrıca doğrulanır. Yerel geçiş üretim yayınına hazır kabul edilmez. [Yayın ve gizli bilgi sınırları](skills/store-automation/references/publishing.md).

## Abonelikler ve hesaplar

Resmî CLI’lar kendi abonelik oturumlarını kullanır; API anahtarına otomatik geçilmez. Codex, Claude, Gemini, Qwen, Antigravity ve MiniMax Code envanteri tutulur. Kurulu olmak, oturumun/modelin çalıştığını kanıtlamaz. GLM/Z.ai için doğrulanmış bir headless yol yoksa sistem bunu açıkça engeller. [Güncel envanter ve yönlendirme](skills/store-automation/references/cli-routing.md).

Girişler resmî istemcide kullanıcı tarafından yapılır. Anahtar/parola içerikleri okunmaz veya loglanmaz; Fastlane ve sağlayıcı araçları mevcut güvenli dosya/secret referanslarını tüketir. Aynı Windows kullanıcısına ait bir dosya, tam yetkili bir ajandan teknik olarak gizlenmiş sayılmaz. Kesin ayrım ayrı işletim sistemi kimliği ve sınırlı broker gerektirir; skill bunu varmış gibi göstermez. Üretim/backend işlemleri seçilmiş uygulama, hesap ve işlem yetkisiyle yürütülür.

## Kurulum ve geliştirme

Python 3.11+, Project Brain skill’i ve kullanılacak resmî CLI gerekir. Bu depodan:

```powershell
python tool/install-skill.py
python -m unittest discover -s tests -v
```

Kurulum Codex ve OpenCode skill dizinlerine kendine yeterli kopyalar, kullanıcının `.local/bin` dizinine `store-automation` başlatıcısı yazar. Değiştirilmiş/başkasına ait dosyaları ezmez; global model ayarlarını değiştirmez. `.local/bin` PATH üzerinde olmalıdır; bu bilgisayarda zaten vardır. Yeni skill görünmüyorsa yeni sohbet/terminal aç.

Bu bilgisayarın varsayılanları: starter `D:/repositories/napp_app_template`, core `D:/repositories/napp-core`, publishing `D:/AppPublishing`. Başka kurulumlarda `STORE_AUTOMATION_STARTER`, `STORE_AUTOMATION_KIT`, `STORE_AUTOMATION_BRAIN` (brain.py yolu) ve preflight’ın `--publishing-root` seçeneği kullanılabilir. Çalışma sırasında bu araç geliştirme deposuna ihtiyaç yoktur.

CI, haricî hesap/SDK gerektirmeyen süreç ve yayın kontrollerini çalıştırır; tam yerel entegrasyon yukarıdaki test komutuyla doğrulanır. Android cihaz/derleme, iOS/macOS, canlı mağaza/receipt ve sağlayıcı girişleri ayrı kanıt kapılarıdır. [Doğrulama raporu](docs/report.json).
