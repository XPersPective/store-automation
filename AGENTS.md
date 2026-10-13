# Bu kaynakta çalışan ajan için

Store Automation 4 kaynağı (git tabanlı plan + kanıta bağlı kabul; Project Brain sentezi). Next'ten köke taşıma ve dağıtım tamamlandı; eski Brain/factory/backlog devamına kayma. Project Brain veya başka skill protokolüne zorunlu bağlı değildir.

Önce HANDOFF.md ve gerçek git durumunu oku. design/v4-target.md hedef/mimari/aşamaları, design/validation-report.md kanıt sınırlarını tutar; design/architecture.md ve roadmap.md 3.x geçmişidir. Durumu yalnız HANDOFF'ta güncelle. Kaynak/test/çağıranları anla; mevcut yardımcı, stdlib ve native özellikleri kullan. Yeni dependency/framework/prosedür için somut ihtiyaç gerekir. Nontrivial davranışa bir anlamlı runnable check bırak.

Kaynak değişince: testler + `node tests/reference-ui-check.cjs`, `python package.py <yeni-boş-dizin>` ile paket, release/store-automation'ı o paketle değiştir, master'a push, Skills Manager `skills update store-automation`, ardından `skills status` ile ajan listesinin düşmediğini ve kurulum hashlerini manifestle doğrula. Release elle düzenlenmez.

Bilinmeyen kullanıcı işi ve .git korunur. Kurulu dağıtım Skills Manager sahipliğini korur. Ücretli AI API, credential içerik okuma/aktarma, billing/signing değişikliği ve seçilmemiş üretim yayını yok. Mevcut AppPublishing/Fastlane yeniden kullanılır.

Uzman görevleri gerektiğinde gerçek native araçla başlar. Ortak dosyanın tek yazarı vardır; salt okunur veya açık ayrık alanlar paralel olabilir. Prompt kapsamı sandbox değildir. Yönetici gerçek native sonucu gözler; worker PASS/provenance alanını kendiliğinden güvenilir sayma. Eksik kanıtı açık tut, tamamlanmış işi tekrar etme. Devirde owner, partial work, pending external effect ve ilk güvenli adımı yaz.
