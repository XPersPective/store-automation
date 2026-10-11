# İhtiyaca göre servis seçimi

10 Ekim 2026 resmi sayfaları incelendi. Bir uygulama talebi olmadığı için hesap,
backend veya ücretli plan açılmadı. Bu liste seçim girdisidir; deploy edilmiş
servis ya da garantili ücretsiz quota kaydı değildir.

| Aday | İlk değerlendirme | Resmi kota/fiyat kaynağı |
|---|---|---|
| Local Flutter | offline veri, ayarlar; backend ihtiyacı yoksa varsayılan | mevcut napp SettingsStore/backup |
| Cloudflare | edge API, D1, R2; auth/receipt güven sınırı ayrıca gerekir | [Workers](https://developers.cloudflare.com/workers/platform/pricing/), [D1](https://developers.cloudflare.com/d1/platform/pricing/), [R2](https://developers.cloudflare.com/r2/pricing/) |
| Firebase | FCM, auth, mobile diagnostics; bütün backend'i zorunlu kılmaz | [pricing](https://firebase.google.com/pricing) |
| Supabase | Postgres, auth/RLS/realtime/storage | [pricing](https://supabase.com/pricing) |
| Appwrite | auth, database, storage/functions; cloud veya self-host | [pricing](https://appwrite.io/pricing) |
| PocketBase | küçük self-host backend; hosting/backup operasyonu kullanıcıda | [docs](https://pocketbase.io/docs/) |
| Neon | managed Postgres; auth/push ayrı ihtiyaç | [pricing](https://neon.com/pricing) (bu incelemede fetch başarısız, seçimde tekrar doğrula) |
| Turso | libSQL ve edge veri | [pricing](https://turso.tech/pricing) |

Servis ADR'sinde capability, beklenen günlük trafik/CPU/storage/egress, ücretsiz
tavan, region/data residency, uyku/retention/backup, bakım sorumlusu, lock-in,
SDK lisansı ve çıkış planı yazılır. Sayfadaki değerler app intake tarihinde
tekrar doğrulanır; cached 'free' etiketiyle billing açılmaz.

FCM+Cloudflare gibi kombinasyon ancak bağımsız gerçek ihtiyaç varsa seçilir.
Quota failure'da degradation/limit/BLOCKED; production verisini otomatik başka
provider'a taşıma. Receipt doğrulama sunucusu client purchase event'ini otorite
saymaz: mağaza API'si, expiry, revocation, user bağlama, idempotency ve webhooks
test edilir. Store credential yoksa monthly production gate BLOCKED kalır.


Seçim ADR'sine her servis/plan için resmi kaynak ve kontrol tarihiyle kart gereksinimi,
hard quota sonrası durma/ret/ücret davranışı, ücretli plana geçiş, otomatik overage,
harcama tavanı ve budget alert'in gerçekten harcamayı durdurup durdurmadığı eklenir.
Cloudflare'ın bütün ürünleri aynı billing kuralına sahip değildir; Firebase Spark
ile Blaze aynı değildir. FCM ihtiyacı bütün backend'in Firebase olmasını gerektirmez.
Kartsız/ücretsiz kesin sınır kullanıcı şartıysa bunu karşılamayan servis seçilmez;
ücretsiz etiketinden koşulsuz maliyet garantisi çıkarılmaz. Uygun alternatifleri
mevcut gerçek ihtiyaca göre karşılaştır, kota aşımı için kullanıcıya görünen
limit/degradation davranışını test et. Kullanıcı seçimi eksikse aktivasyondan önce sor.
