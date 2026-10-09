# CryoFinder — OneDrive tank haritası düzenleyici

OneDrive'daki (kişisel Microsoft hesabı) `.xlsx` tank haritasını, **diske kaydetmeden**, güvenli biçimde düzenler.

## Güvenlik kuralları (kodda zorunlu)
- **Silme yok:** HTTP istemcisi yalnızca GET/POST/PUT/PATCH bilir; `DELETE` istisna fırlatır (test: `test_no_delete_anywhere`).
- **Yedek:** ilk onaylı değişiklikten önce `Yedekler/<ad>_yedek_<YYYY-MM-DD_HHMMSS>.xlsx` oluşturulur
  (aynı adlı dosyanın üzerine asla yazılmaz). Yedek alınamazsa hiçbir şey yazılmaz.
- **Onay:** her hücre değişikliği için ayrı `[e/H]` sorusu; onay atlama bayrağı yoktur, terminal gerekir.
- **Kayıt:** `degisiklik_kaydi.jsonl` (eklemeli; onaylanan/reddedilen/başarısız her olay, eski→yeni değer, eTag, yedek yolu).
- **Gerçek dosya:** `--production` + dosya adını yazma gerekir; adında `TEST` olmayan dosyaya `--production`'sız yazılmaz.
- **Gizlilik:** `.env` (Client ID), `.token_cache.json`, değişiklik kaydı ve `*.xlsx` `.gitignore`'dadır.
- Formül içeren hücrelerin üzerine ve `=` ile başlayan değerler yazılmaz.

## Kurulum
`pip install -r requirements.txt`, [docs/AZURE_KAYIT.md](docs/AZURE_KAYIT.md) adımlarını izleyin, `.env.example` → `.env`.

## Kullanım (varsayılan hedef: TANK_HARITASI_TEST.xlsx)
```
python -m tank_haritasi login                # tarayıcı olmayan ortamda: --device-code
python -m tank_haritasi probe                 # Excel API çalışıyor mu? (salt-okunur)
python -m tank_haritasi probe --write-probe   # + yedekli, onaylı, içeriği değiştirmeyen yazma testi
python -m tank_haritasi sheets
python -m tank_haritasi show Sayfa1 --range A1:L30
python -m tank_haritasi find "Hasta"
python -m tank_haritasi set -c "Sayfa1!B3=Yeni değer" -c "Sayfa1!B4="
```
`--mode auto` (varsayılan): Excel API çalışıyorsa onu, çalışmıyorsa dosyayı yalnızca bellekte açıp
`If-Match: <eTag>` ile geri yükleyen yöntemi seçer. `--mode excel-api|memory` ile zorlanabilir.

## Tarayıcı arayüzü (önerilen)
```
python3 -m tank_haritasi gui
```
Yalnızca bu bilgisayardan erişilen (127.0.0.1) yerel bir sayfa açar: sayfa seç, ara, hücreye tıkla, yeni değeri yaz,
eski→yeni farkını gör, **Onayla ve uygula**'ya bas. Kurallar CLI ile aynıdır: onaydan önce hiçbir şey yazılmaz, ilk onayda
`Yedekler/`'e yedek alınır, her olay `degisiklik_kaydi.jsonl`'e yazılır, silme yok. Siz incelerken hücre başkasınca
değiştirilirse uygulama reddedilir. Gerçek dosya için `--production` (başlangıçta terminalde dosya adı sorulur).
Güvenlik: oturum anahtarı, Host/Origin denetimi, yalnızca JSON POST; diğer web siteleri arayüzü kullanamaz.
Hücreler Excel'de göründüğü biçimde (tarihler dahil) gösterilir.

## Bellek-içi yöntemin sınırları
Yükleme öncesi doğrulanır: yalnızca onaylı hücreler değişti mi; grafik/resim/pivot gibi parçalar kaybolacak mı
(kaybolacaksa yüklenmez). Formüllerin önbellek değerleri Excel açıldığında yeniden hesaplanır.
Başka biri dosyayı okuduktan sonra değiştirirse (412) hiçbir şey yazılmaz.
