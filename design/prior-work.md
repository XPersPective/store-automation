# Önceki çalışma ile uzlaştırma

2026-10-13: Kullanıcının son eki tekrar okundu. “Yayınlama skill’ini yeniden tasarla” sohbeti (`01a134d6-e60a-7e23-9c72-40c74e3400d3`) ürün/UX/FE-BE/yayın gereksinimlerini bir inceleme prompt'unda birleştirmiş; yeni runtime tamamlanması kaydı değildir. “AI App Factory sistemini kur” sohbetinde (`01a12782-fdba-7ba0-ac6f-0f59ccb60aeb`) ilk gerçek delegation/template çalışmaları var; sonuç eski sürüme ait ve son turn failed durumunda. Eski kanıt bugünkü başarı yerine kullanılmaz.

Depodaki `docs/architecture-cli-team.md` hedef tasarım v3 ve `docs/evidence/architecture-critique-20261012.md` okundu. Belge kendisi implementation/live kabulün tamamlanmadığını söylüyor. Sonraki ADR-005 custom console/sidebar/pane zorunluluğunu kaldırmış. Bunlar yeni tasarıma tekrar zorunlu özellik olarak alınmaz.

| Eski açık iş / yetenek | Yeni karşılık | Karar |
|---|---|---|
| PB031 typed report, gerçek rol/model/risk, dispatch kökeni | N01/N02 | Ortak minimal kayıt ve kriter kabulü; PB zorunluluğu kaldırılır |
| PB032/036 ikinci sağlayıcı metadata/erişim/transport | N02 host sınırı | Mevcut host öncelikli; kanıtsız evrensel sağlayıcı desteği yok; somut eksik yetenek için adapter |
| PB033 kota/reset | N03 | Mevcut host metadata ve gerçek quota; daemon/sürekli inference polling yok |
| PB034 partial work/başka director devri | N03 ve N07 | Süreç/diff/requirements/pending effect ile gerçek devir deneyi |
| PB035 native steer/interrupt/report | N02/N03 | Mevcut host gerçek araçlarını kullan; kontrol ACK'ini uygulanmış sonuç sayma |
| Eski console/telefon UI tasarımı | Yeni ürün kapsamına alınmadı | Son kullanıcı yönü custom agent UI istemiyor; normal sohbet raporu ve artifact yeterli |
| Eski installer/global dağıtım | N06/N08 | Owned-file ve rollback koruması korunur; yeni paket doğrulanınca tüm agent rollout |
| Eski ürün/mağaza protokolü | N04/N05 | Erken gösterim, gerçek yolculuk, kanıtlanmış candidate/readback ile yürütülebilir hale getirme |

Bu eşleştirme eski PB dosyalarını tamamlandı diye işaretlemez, kullanıcı projelerindeki görevleri taşımaz. Yeni tek devam kaynağı HANDOFF ve buradaki roadmap'tir. Kullanıcının tekrar verdiği metin yeni bir başlangıç değil; mevcut çalışma kapsamını teyittir.
