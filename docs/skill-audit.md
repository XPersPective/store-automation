# OpenCode context/skill audit

Kaynak envanter: `evidence/skills-inventory.json`. Byte/line gerçek ölçümdür;
token maliyeti yaklaşık bytes/4, dil/tokenizer farkıyla değişir. Discovery listesi
yalnız metadata yükler; full content skill çağrısında yüklenir.

| Tanım | Amaç / kullanım | Factory gerekli? / örtüşme | Eylem / geri dönüş |
|---|---|---|---|
| project-brain | Git state/plan; supervisor | evet; 4 home link aynı source hash | KEEP_BUT_SCOPE; supervisor on-demand, worker slice; linkler korunur |
| archify | mimari görselleştirme | rutin Flutter workflow için şart değil | KEEP_BUT_SCOPE; factory permission deny, diğer projeler korunur |
| archify-review | archify çıktısı review | archify ile bağlı, code review yerine geçmez | KEEP_BUT_SCOPE; factory deny |
| harsh-self-critique | genel öz-eleştiri | factory üç tur/kontratla kısmen örtüşür | KEEP_BUT_SCOPE; factory deny |
| customize-opencode (built in) | OpenCode config yardımı | kurulum zamanı gerekebilir | default factory skill deny; native tanım silinmez |
| app-factory | kısa core workflow | evet | repo-local; on-demand, global context'e eklenmedi |
| factory-release | mevcut publishing prosedürüne bağlantı | yalnız release reviewer/human session | on-demand; private protocol factory dışına otomatik okunmaz |

Mevcut global agent tanımı yok; global default qwen-cloud disabled olduğu halde
seçili. Factory bunu repo config'te ücretsiz modelle ezer; global tercih değiştirilmez.
Global Ponytail plugin korunur. Factory komutları `--pure` ile external plugin
yüklemez; keşifte normal plugin startup gecikmişti. Bu mod başka projelerin plugin
davranışını değiştirmez. ~/.opencode/command/project-brain.md pointer korunur;
factory commands repo config'te tanımlanır. Model sağlayıcı secret option değerleri
env/repo'ya taşınmadı. Yeni MCP/server/dependency eklenmedi.

Fiziksel skill silme/arşivleme yapılmadı: aktif diğer projelerde kullanılmadığına
dair kanıt yok. Fabrika için gereksiz üç skill görünür tool listesinden permission
deny ile çıkarıldı; geri dönüş opencode.json skill scope diff'ini revert etmektir.
Başka projede gerekli skill'i global kaldırmak daha az güvenli olurdu.

İşlem sınırı: prompt ve OpenCode glob izinleri OS sandbox değildir. Read-only
reviewer'da bash ve edit araçları runtime discovery ile gerçekten kapalı.
Worker shell tamamen kapalı; supervisor sabit doğrulama komutlarını yürütür.
No-paid CLI allowlist resmi free fiyatlarıyla güncellenir; native OpenCode generic
model picker provider whitelist'e daraltıldı. Yetkili factory
runner paid model'i inference başlamadan reddeder. Başka harness kullanımı bu guard
kapsamı dışındadır.
