# Yayın, ürün sunumu ve bakım

Mevcut yayın düzenini incele: bu makinede `D:/AppPublishing/README.md` ve seçilen uygulamanın Fastlane dosyaları. Başka ortamda gerçek mevcut konumu belirle; sabit yolu evrensel şart yapma. İkinci katalog, credential şeması veya uploader kurma.

## Platforma göre kanıt

| Hedef | Aday ve yerel kontrol | Ayrı dış kanıt |
|---|---|---|
| Google Play | Son AAB, iç package/version, imza, ilgili Android cihaz akışı, metadata/görseller/beyanlar | Hesap/app/track/version geri okuması; inceleme ve dağıtım durumu |
| App Store | Archive/IPA, bundle/version/signing, gerekli iOS cihaz/simulator kapsamı, store materyali | App Store Connect build processing, seçilmiş submission, kabul ve erişilebilirlik |
| Windows | Seçilmiş installer/MSIX/portable paket; kurulum/açılış/güncelleme/kaldırma | Seçilmiş kanal/store/indirme ve yayımlanan sürüm |
| Web | Son bundle + deployment config; gerçek browser/servis akışı | Hedef hosting URL, revision, ortam ve çalışan erişim |

Factory testi uygulama kabulü değildir; APK kontrolü AAB'yi, Android screenshot iOS'u, simulator debug signed release'i kanıtlamaz. Seçilmeyen platform için işlem başlatma. Desteklenmeyen adapter/ortamı başarılı sayma.

## Tek son adayla tutarlılık

Kaynak/gereksinim snapshot'ı, artifact hash, gömülü kimlik/sürüm, imza kontrolü, cihaz/locale görüntüleri, metadata ve uzak sürüm referanslarını aynı adaya bağla. Yeni bir yayın veritabanı gerekmez; mevcut release evidence kaydı bu referansları tutabilir. Görsel manifest kaydı, görüntünün decode edildiği veya UX'in kabul edildiği anlamına gelmez.

Konumlandırma ve ürün adı gerçek kullanıcı ihtiyacını anlatsın. İkon, screenshot sırası/anlatımı, kısa/uzun açıklama, yerelleştirme, sürüm notu, gizlilik/destek bağlantıları aynı ürünü tarif etsin. Olmayan özellik, temelsiz sağlık/güvenlik iddiası, sahte rating veya keyword doldurma yok. ASO ve web SEO farklı hedef/kurallara göre değerlendirilir; ticari başarı garanti edilmez.

Görselleri gerçek son uygulamadan al; tanıtım kompozisyonu gerçek cihaz/etkileşim kanıtının yerine geçmez. Son export'u görüntüle, metin/lokalizasyon/formatı kontrol et; görsel/font/audio kaynağı ve kullanım hakkını kaydet. Makine çevirisi tek başına dil kalitesi kabulü değildir. Kaynak değişince etkilenen görüntü ve metni tekrar kontrol et.

Güncel resmi kaynakları hedef sürümde kontrol et: [Google preview assets](https://support.google.com/googleplay/android-developer/answer/9866151), [Apple review](https://developer.apple.com/app-store/review/guidelines/), [Fastlane supply](https://docs.fastlane.tools/actions/supply/), [deliver](https://docs.fastlane.tools/actions/deliver/). Statik limitleri sonsuza dek geçerli sayma.

## Yetki ve uzak sonuç

Kullanıcının mevcut tam app/account/action/destination yetkisi geçerlidir; tekrar sorulmaz. Eksikse önce geri alınabilir hazırlığı bitir ve somut adayı göster; sadece eksik dış kararı iste. Genel skill kurulum veya uygulama yap talebi üretim mağaza yetkisi değildir.

Credential içeriğini model bağlamına alma. Mevcut native araçların doğrudan path/secret referansıyla tüketmesi kullanılır. Billing/signing/rol değişikliği otomatik yapılmaz. Production lane'i “deneme” diye çalıştırma.

Durumlar ayrı raporlanır: `LOCAL_PREPARED`, `UPLOADED`, `SUBMITTED`, `APPROVED`, `AVAILABLE`; her biri gerçek hedefe göre gözlenir, doğrusal geçiş varsayılmaz. Hesap/app/channel/version/status readback olmadan gönderim tamamlandı denmez. Yanıt kaybında yeniden upload'dan önce remote state incelenir. API'deki completed durumu dünya çapında kullanıcı erişimini tek başına kanıtlamaz.

## iOS / CI

Uygun macOS/Xcode veya seçilmiş CI gerekir. Public standard runner, private kota, larger runner ve storage ayrı maliyet şartlarıdır; plan adı kalan ücretsiz hakkı kanıtlamaz. Hesap/repo/runner ve geçerli maliyet sınırı doğrulanmadan “ücretsiz” denmez. Özel kaynak veya kullanıcı verisi ücretsiz CI uğruna yayınlanmaz. Bütçe/billing ayarı değiştirilmez. [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

## Yayın sonrası

Gerçek destek sorunu, uygun crash/performance verisi ve uygulanabilir SDK/store değişikliği ile küçük bakım işi aç. Yeni tracking varsayılan eklenmez. Kullanıcı yalnız seçilmiş projeler için izleme istediyse mevcut host zamanlayıcısını kullan; aynı kalan durumda sessiz, anlamlı değişimde bildirim. Yeni daemon kurma. Düzeltme ilgili test/cihaz/materyal/yayın kanıtını yeniler; bütün ürün kararlarını baştan açmaz.
