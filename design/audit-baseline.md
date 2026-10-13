# İnceleme başlangıcı — 2026-10-13

Bu belge yeni mimarinin nedenini korur; eski bulguları sonsuza dek güncel saymaz. Kaynak değiştiğinde sembolü/caller'ı yeniden kontrol et. Eski runtime'a patch bu oturumda uygulanmadı.

## Kullanıcı talebi ve kapsam değişimi

İlk metin: profesyonel ürün ekibi gibi çalışan sistem; gerçek ihtiyacı anlama, erken UX gösterimi, etkili uzmanlık, FE/BE birlikteliği, benimseme, kesinti devamı, doğru mağaza materyali/gerçek yayın sonucu, ölçülmüş hız/kalite. Aynı zamanda somut kusurları düzeltme istedi.

Sonraki açıklama: “Herhangi bir skile bağlı olarak çalışma ... rahatça, serbest bir şekilde eleştirip mimari önereceğin bir oturum.” Bunun ardından mevcut sistemden ayrı alt klasörde yeni skill ve **önce kapsamlı aşamalı mimari/yol haritası**, başka yapay zekaya devir istendi. Bu klasör o son talebi karşılar; eski Brain iş akışını dayatmaz.

Orijinal ek dosyalar aynı içeriğe sahipti; SHA-256: `737F0F2784A706308E68F310E1B1EA3269F8D0E6ECEC6C59EFE565E1E171063A`. Devir için ek dosyaya erişim gerekmemesi amacıyla kapsam bu belgelere dağıtılmıştır.

## Korunmuş başlangıç

- Üst depo: `D:/repositories/store-otomaston`, o incelemede branch `factory-bootstrap`, HEAD `eca283f` (tarihsel referans; devamda yeniden kontrol edilir).
- Başlangıçta untracked `.factory/` ve `.project-brain/tasks/PB-026.md` vardı. Bunlar bu yeni tasarımın çalışması değildir; silinmez/sahiplenilmez.
- `tool/factory.py`, `subscriptions.py`, `dispatch.py`, `sessions.py`, `native_agents.py`, `release.py`, `artifacts.py`, testler, skill/referansları ve `D:/AppPublishing/README.md` incelendi. Credentials okunmadı.

## Kanıtlı bulgular

| ID | Kaynak / tetikleyici | Gözlenen sonuç / güven | Çözüm yönü |
|---|---|---|---|
| F01 | `factory._model_run` Codex; `evidence_gate` OpenCode ses_ export | Codex biçimli reviewer ID reddediliyor; B odaklı repro + kaynak, yüksek güven | Sağlayıcıdan bağımsız gerçek atama/sonuç kökeni |
| F02 | `subscriptions.report_valid`, `factory.main`, çağrılmayan `dispatch.checked_report` | BANANA state ve yanlış rol ayrı ayrı CLI exit 0; B, parent tekrar üretti | Allowlist state, ortak rol/route doğrulama, explicit success |
| F03 | `evidence_gate` native export sahipliği | Farklı project ve parent içeren mock export ACCEPTABLE; B, parent tekrar üretti | Doğru project/attempt/bağımsızlık ilişkisi |
| F04 | `_model_run` source_snapshots | Captured hash'leri iş sonrasında doğrulayan caller yok; source değişen mock çalışması FINISHED; B, uzman tekrarı + kaynak | İş sonrası snapshot geçerliliği |
| F05 | `validate_contract` ve `verification_commands/evidence_gate` | Kabul/required_evidence metinleri semantik olarak yürütülmüyor; sabit factory/Flutter/APK profili | Kriter bazında makine/yolculuk/platform kanıtı |
| F06 | Eski SKILL mandatory preflight ve lifecycle fazları | İncelemeden önce katalog/ekip; erken kullanıcı prototip/ilk dilim şartı eksik; kaynak, yüksek güven | Riskle ölçeklenen süreç, erken gerçek gösterim |
| F07 | `architecture-review.md` ile `evidence_gate` | Belge kabul edilmiş küçük bulguya izin veriyor, kod findings=[] istiyor | Açık disposition, ihlal edilmeyen zorunlu kriter |

Bu bulgular bütün gerçek uygulamaların düşük kaliteli olduğunu kanıtlamaz. Ajan rapor processing kusurları gerçek provider inference yerine mock transport kullanılarak gösterildi. Kötü niyetli yabancı oturum gerçekten kullanılmış veya canlı hesap aşılmış iddiası yok.

## Yapılan ölçüm ve kontrol

- Eski depo kökünde `python -m unittest discover -s tests -v`: **130 test, 26.230 saniye, OK**. Log: eski depodaki `.factory/product-audit-baseline-20261013.log`; aday pakete dahil edilmez. F01–F03 kontrolü bu suite'in geçmesinin uçtan uca akışı kanıtlamadığını gösterir.
- `python tool/factory.py providers --catalogue`: tool duvar süresi yaklaşık 9.96 saniye. Bu tek örnekten genel tasarruf yüzdesi çıkarılmaz. Canlı hesap metadata'sı model/task yeterliliği değildir.
- Native host üzerinden iki salt okunur uzman incelemesi, ardından ayrı mimari eleştirisi tamamlandı; anlamlı bulgular verdi. Bu, eski factory'nin kendi delegasyon/acceptance zincirinin çalıştığını kanıtlamaz. Toplam token kullanımı ölçülmedi.
- Gerçek uygulama ekranları, FE/BE live akışı, cihaz kabulü, global kurulum ve mağaza yayını bu incelemede denenmedi. Eski release kanıtları bugünkü başarı sayılmadı.

## F02 yeniden üretimi

Eski repo duruyorsa kökünde aşağıdaki Python'u stdin üzerinden `python -B -` ile çalıştır. Yalnız TemporaryDirectory fixture yazılır, inference taklit edilir; credential/ağ/üretim çağrısı yok. Bu kontrolü kalıcı yeni runtime testi gibi sunma; N01 kendi bağımsız regresyonunu yazacak.

```python
import io, json, sys
from contextlib import redirect_stdout
from unittest.mock import patch
sys.path.insert(0, 'tests')
from test_factory import FactoryChecks
from tool import factory as f
x = FactoryChecks()
x.setUp()
try:
    c = f.ROOT / 'contracts/delegation-smoke.json'
    p = f.ROOT / 'contracts/audit.txt'
    p.write_text('Offline audit')
    route = dict(provider='codex', model='gpt-6-luna', effort='low')
    for state, role in [('BANANA', x.contract['persona']['role']),
                        ('COMPLETED', 'unassigned-role')]:
        report = dict(task=x.contract['task_id'], role=role, **route,
                      state=state, changed_files=[], evidence=['synthetic'],
                      usage=None, blockers=[], next_action='Done')
        result = dict(exit_code=0, selected=route, stdout=json.dumps(dict(
            type='item.completed', item=dict(type='agent_message',
                                            text=json.dumps(report)))))
        out = f.ROOT / '.factory/runs' / f'{state}.json'
        argv = ['factory', 'run', '--provider', 'codex', '--contract', str(c),
                '--prompt-file', str(p), '--output', str(out), '--json']
        with patch.object(sys, 'argv', argv), patch.object(
                f, 'model_run', return_value=result), redirect_stdout(io.StringIO()):
            code = f.main()
        print(state, role, '=> exit', code)
finally:
    x.doCleanups()
```

Gözlenen çıktı: `BANANA Principal Architecture Reviewer => exit 0`; `COMPLETED unassigned-role => exit 0`.

F01/F03 fixture mantığı: `tests/test_factory.py:test_evidence_rejects_stale_failed_missing_artifact_and_same_reviewer` gerçek temp Git/hash'lerini kullanır; check ve native export mock'tur. Eşleşen source/contract/log yanında Codex biçimli ID → `Review requires a native reviewer session`. `ses_fake`, agent `factory-reviewer`, parent `unrelated-parent`, directory `D:/unrelated-project`, eşleşen verdict fields → `ACCEPTABLE`. Yeni N01/N02 bu negatifleri kendi kayıtlarında yeniden üretmeli.

## Bağımsız mimari eleştirisinden alınan kararlar

- Brain'i sözde opsiyonel yapıp validator içinde PB zorunluluğu tutma; gerçek execution sınırında kaldır.
- Native delegation daha az kod sağlar, ancak wrapper izinlerini otomatik devralmaz; requested/enforced/observed ayrımı gerekir.
- Journey demo yeni global PASS olmasın; prototip, service, cihaz ve signed paket kanıtı ayrı.
- Resume yalnız checkbox'a değil süreç/diff/requirements/pending external effect uzlaştırmasına dayansın.
- Yeni coordinator'ın arkasında eski zorunlu workflow yaşamaya devam etmesin; geçişte tek giriş ve gerçek rollback olsun.

## İncelenen dış dayanaklar

13 Ekim 2026'da resmi Google preview assets, Apple Review Guidelines, GitHub Actions billing ve W3C resize/contrast sayfaları okundu. Bağlantılar ilgili references dosyalarındadır. Bu tarih sonraki release'te yeniden kontrolün yerine geçmez. Kullanıcının CI hesabı kalan free entitlement'ı veya mağaza yetkisi bu sayfalardan çıkarılmadı.
