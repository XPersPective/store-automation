# Bu kaynakta çalışan ajan için

Kullanıcı yeni mimariyi Store Automation Next altında bağımsız geliştirmeyi, tamamlandıktan sonra eski kökü değiştirip içeriği bir üste taşımayı, boş Next klasörünü kaldırmayı, bilgisayardaki ajanlara ve GitHub'a dağıtmayı açıkça istedi. Bu çalışma Project Brain veya başka skill protokolüne zorunlu bağlı değildir. Eski Brain/backlog devamına kayma.

Önce HANDOFF.md ve gerçek git durumunu oku. design/roadmap.md aşamaları, design/architecture.md kararları, design/validation-report.md kanıt sınırlarını tutar. Durumu yalnız HANDOFF'ta güncelle. Kaynak/test/çağıranları anla; mevcut yardımcı, stdlib ve native özellikleri kullan. Yeni dependency/framework/prosedür için somut ihtiyaç gerekir. Nontrivial davranışa bir anlamlı runnable check bırak.

Bilinmeyen kullanıcı işi ve .git korunur. Eski kök ancak doğrulanmış aday ve repo dışında geri dönüş yedeğiyle değiştirilir. maintenance/promote.ps1 önce dry-run, sonra journal ile uygular. Kurulu dağıtım Skills Manager sahipliğini korur. Ücretli AI API, credential içerik okuma/aktarma, billing/signing değişikliği ve seçilmemiş üretim yayını yok. Mevcut AppPublishing/Fastlane yeniden kullanılır.

Uzman görevleri gerektiğinde gerçek native araçla başlar. Ortak dosyanın tek yazarı vardır; salt okunur veya açık ayrık alanlar paralel olabilir. Prompt kapsamı sandbox değildir. Yönetici gerçek native sonucu gözler; worker PASS/provenance alanını kendiliğinden güvenilir sayma. Eksik kanıtı açık tut, tamamlanmış işi tekrar etme. Devirde owner, partial work, pending external effect ve ilk güvenli adımı yaz.
