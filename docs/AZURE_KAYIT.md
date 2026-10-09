# Azure portalında uygulama kaydı (kişisel Microsoft hesabı)

Ücretsizdir; Azure aboneliği gerekmez. **OneDrive'ın sahibi olan kişisel hesapla** giriş yapın.

1. <https://portal.azure.com> → kişisel Microsoft hesabınızla giriş yapın (ilk seferde "Default Directory" oluşur).
2. Üst arama çubuğuna **Microsoft Entra ID** (eski adı Azure Active Directory) yazıp açın.
3. Sol menü → **Manage → App registrations → + New registration**.
4. Formu doldurun:
   - **Name:** `TankHaritasi-Editor` (herhangi bir ad)
   - **Supported account types:** **Personal Microsoft accounts only**
   - **Redirect URI:** platform **Public client/native (mobile & desktop)**, değer `http://localhost`
   - **Register**'a basın.
5. **Overview** sayfasındaki **Application (client) ID** değerini kopyalayın → `.env` içindeki `AZURE_CLIENT_ID`.
   (Tenant ID gerekmez; program `consumers` yetkilisini kullanır.)
6. **Manage → API permissions → + Add a permission → Microsoft Graph → Delegated permissions**:
   - **Files.ReadWrite** işaretleyin → *Add permissions*. (`User.Read` zaten vardır; kalsın.)
   - `Files.ReadWrite.All`, *Application permissions* veya başka izin **eklemeyin**.
   - Kişisel hesapta yönetici onayı yoktur; izni ilk girişte siz onaylarsınız.
7. **Manage → Authentication**: `http://localhost` yönlendirmesi "Mobile and desktop applications" altında görünmeli.
   "Allow public client flows" kapalı kalabilir (etkileşimli tarayıcı girişi için gerekmez).
8. **Client secret OLUŞTURMAYIN.** Bu bir *public client*; sır gerekmez.
9. Depoda: `cp .env.example .env`, `AZURE_CLIENT_ID`'yi yapıştırın. `.env` ve `.token_cache.json` `.gitignore` ile korunur.

## Sık hatalar
- **AADSTS700016 / "application not found in directory 'Microsoft Accounts'"**: hesap türü "Personal Microsoft accounts only" değil; Authentication/Manifest'ten düzeltin.
- **`api.requestedAccessTokenVersion` hatası**: Manifest'te `requestedAccessTokenVersion` değerini `2` yapıp kaydedin.
- **AADSTS50011 redirect uyuşmazlığı**: yönlendirme "Web" değil, "Mobile and desktop" platformu altında `http://localhost` olmalı.
- Onay ekranında "doğrulanmamış uygulama" uyarısı normaldir (kendi kaydınız).
