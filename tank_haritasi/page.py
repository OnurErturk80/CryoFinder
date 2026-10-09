"""Yerel arayüzün tek sayfası (HTML + CSS + JS). Hücre/hasta verisi her zaman textContent ile yazılır (innerHTML yok)."""

PAGE = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark"><meta name="theme-color" content="#2563eb">
<title>Tank Haritası</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%232563eb'/%3E%3Ccircle cx='22' cy='24' r='7' fill='%23fff'/%3E%3Ccircle cx='42' cy='24' r='7' fill='%23facc15'/%3E%3Ccircle cx='22' cy='44' r='7' fill='%2322c55e'/%3E%3Ccircle cx='42' cy='44' r='7' fill='%23f97316'/%3E%3C/svg%3E">
<style>
:root{--bg:#f3f5fa;--surface:#fff;--surface2:#f7f8fc;--fg:#0f172a;--mut:#64748b;--line:#e3e8f1;--acc:#2563eb;--acc-fg:#fff;--acc-soft:#e8efff;
--ok:#047857;--ok-soft:#d8f5e8;--bad:#b91c1c;--bad-soft:#fde4e4;--warn:#92400e;--warn-soft:#fef3c7;--r:14px;
--shadow:0 1px 2px rgba(15,23,42,.05),0 6px 20px rgba(15,23,42,.06);--nav-h:64px}
@media(prefers-color-scheme:dark){:root{--bg:#0b1020;--surface:#131a2c;--surface2:#18213a;--fg:#e6eaf6;--mut:#97a3bb;--line:#26314b;--acc:#7aa2ff;--acc-fg:#0b1020;--acc-soft:#1a2a4f;
--ok:#4ade80;--ok-soft:#0e2e22;--bad:#fb7185;--bad-soft:#3b1620;--warn:#fcd34d;--warn-soft:#3a2f10;--shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px rgba(0,0,0,.25)}}
*{box-sizing:border-box}[hidden]{display:none!important}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
button,input,select,textarea{font:inherit;color:inherit}
:focus-visible{outline:3px solid color-mix(in srgb,var(--acc) 55%,transparent);outline-offset:2px;border-radius:8px}
h2{font-size:20px;margin:0 0 4px}h3{font-size:16px;margin:0 0 10px}small,.mut{color:var(--mut)}

/* üst çubuk + gezinme */
.top{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:12px;padding:10px 20px;padding-top:max(10px,env(safe-area-inset-top));
 background:color-mix(in srgb,var(--surface) 88%,transparent);backdrop-filter:saturate(1.4) blur(12px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:10px;min-width:0}.brand svg{flex:none}.brand b{display:block;line-height:1.15}
.brand small{display:block;max-width:34ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.chips{display:flex;gap:6px;flex-wrap:wrap}.chip{padding:2px 10px;border-radius:99px;background:var(--surface2);border:1px solid var(--line);color:var(--mut);font-size:12px;white-space:nowrap}
.spacer{flex:1}
.tabs{display:flex;gap:4px;padding:8px 20px;overflow:auto}
.tabs button{display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:12px;border:1px solid transparent;background:transparent;color:var(--mut);cursor:pointer;white-space:nowrap;font-weight:600}
.tabs button svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.tabs button:hover{background:var(--surface)}.tabs button.on{background:var(--acc-soft);color:var(--acc)}
#prodBar{background:var(--bad);color:#fff;text-align:center;padding:6px 12px;font-weight:700;font-size:13px;letter-spacing:.02em}
#stagedBar{position:sticky;top:60px;z-index:15;display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:0 20px;padding:10px 14px;border-radius:12px;background:var(--warn-soft);color:var(--warn);border:1px solid color-mix(in srgb,var(--warn) 25%,transparent)}

/* içerik */
.wrap{max-width:1180px;margin:0 auto;padding:8px 20px 40px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:16px;box-shadow:var(--shadow);margin-bottom:16px;min-width:0}
.cols{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:16px;align-items:start}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}.row>.grow{flex:1 1 220px}
.field{display:grid;gap:4px;min-width:0}.field>span{font-size:12px;color:var(--mut);font-weight:600}
input,select,textarea{padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--surface);min-height:42px;min-width:0;width:100%}
input[type=checkbox],input[type=radio]{width:20px;height:20px;min-height:0;padding:0;flex:none;accent-color:var(--acc)}
input::placeholder,textarea::placeholder{color:var(--mut)}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:42px;padding:0 16px;border-radius:10px;border:1px solid var(--line);background:var(--surface);cursor:pointer;font-weight:600;white-space:nowrap;width:auto}
.btn:hover{background:var(--surface2)}.btn.primary{background:var(--acc);border-color:var(--acc);color:var(--acc-fg)}.btn.primary:hover{filter:brightness(1.07)}
.btn.danger{background:var(--bad);border-color:var(--bad);color:#fff}.btn.ghost{background:transparent;border-color:transparent;color:var(--mut)}
.btn:disabled{opacity:.55;cursor:not-allowed}.btn.loading{position:relative;color:transparent!important}
.btn.loading::after{content:"";position:absolute;width:16px;height:16px;border-radius:50%;border:2px solid var(--acc-fg);border-top-color:transparent;animation:sp .7s linear infinite}
.btn:not(.primary):not(.danger).loading::after{border-color:var(--acc);border-top-color:transparent}@keyframes sp{to{transform:rotate(360deg)}}
.alert{padding:10px 12px;border-radius:10px;margin-top:10px;font-weight:500}.alert.ok{background:var(--ok-soft);color:var(--ok)}.alert.bad{background:var(--bad-soft);color:var(--bad)}.alert.info{background:var(--acc-soft);color:var(--acc)}
.steps{counter-reset:s}.step h3{display:flex;align-items:center;gap:10px}.step h3::before{counter-increment:s;content:counter(s);display:grid;place-items:center;width:26px;height:26px;border-radius:50%;background:var(--acc);color:var(--acc-fg);font-size:13px}

/* tablo görünümü */
.sheetbox{overflow:auto;height:calc(100vh - 300px);min-height:300px;border:1px solid var(--line);border-radius:12px;background:var(--surface);-webkit-overflow-scrolling:touch}
.sheetbox::-webkit-scrollbar{width:13px;height:13px}.sheetbox::-webkit-scrollbar-track{background:var(--surface2)}.sheetbox::-webkit-scrollbar-thumb{background:var(--mut);border-radius:7px;border:3px solid var(--surface2)}
table{border-collapse:collapse;width:max-content;min-width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--line);border-right:1px solid var(--line);padding:5px 9px;white-space:nowrap;max-width:260px;overflow:hidden;text-overflow:ellipsis}
th{background:var(--surface2);position:sticky;top:0;color:var(--mut);font-weight:600;z-index:1}
td.rn{background:var(--surface2);color:var(--mut);position:sticky;left:0;text-align:right}td.c{cursor:pointer}td.c:hover{outline:2px solid var(--acc);outline-offset:-2px}td.sel{background:var(--warn-soft)}
.found{max-height:170px;overflow:auto;margin:8px 0}.found div{padding:8px 10px;border-radius:8px;cursor:pointer}.found div:hover{background:var(--surface2)}

/* öğe kartları */
.list{display:grid;gap:8px}.item{display:flex;gap:12px;align-items:center;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--surface2)}
.item.pick{cursor:pointer}.item.pick:has(input:checked){border-color:var(--acc);background:var(--acc-soft)}
.item .grow{flex:1;min-width:0}.item b{word-break:break-word}.item .sub{color:var(--mut);font-size:13px;word-break:break-word}
.straw{display:grid;grid-template-columns:minmax(0,1.3fr) 150px minmax(0,1.6fr);gap:10px;align-items:end;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:var(--surface2);margin-bottom:8px}
.change{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr) minmax(0,1fr);gap:8px;padding:7px 10px;border-bottom:1px solid var(--line);font-size:13px}
.change .w{color:var(--mut);font-family:ui-monospace,Menlo,monospace;font-size:12px;word-break:break-all}.change .o{color:var(--bad);text-decoration:line-through;word-break:break-word}.change .n{color:var(--ok);font-weight:600;word-break:break-word}
.changes{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:12px}

/* tank haritası */
.legend{display:flex;gap:14px;flex-wrap:wrap;align-items:center;color:var(--mut);font-size:12.5px;margin:6px 0 12px}.legend>span{display:inline-flex;align-items:center;gap:6px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-bottom:14px}
.tile{padding:10px 12px;border-radius:12px;background:var(--surface2);border:1px solid var(--line)}.tile b{display:block;font-size:22px;line-height:1.1}.tile span{color:var(--mut);font-size:12px;display:flex;align-items:center;gap:6px}
#vizCans{display:flex;gap:12px;align-items:flex-start;overflow:auto;padding:2px 2px 12px;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}
.can{flex:none;width:236px;scroll-snap-align:start;border:1px solid var(--line);border-radius:14px;background:var(--surface2);padding:8px 8px 4px}
.can h4{margin:2px 0 4px;text-align:center;font-size:14px}.lh{display:flex;gap:8px;padding:0 6px 4px 34px;color:var(--mut);font-size:11px;font-weight:600}.lh span{width:84px;text-align:center}
.gob{display:flex;align-items:center;gap:8px;padding:3px 6px;border-top:1px dashed var(--line)}.gn{width:22px;text-align:right;color:var(--mut);font-size:12px}
.lv{display:flex;gap:4px;width:84px;justify-content:center}.lv .none{color:var(--mut)}
.dot{width:17px;height:17px;border-radius:50%;border:1.5px solid var(--mut);font-size:9px;line-height:14px;text-align:center;cursor:pointer;color:#111;font-weight:700;flex:none;display:inline-block;padding:0;min-height:0;background:transparent}
.dot.empty{border-style:dashed;opacity:.7}.dot.cm{background:#3b82f6;border-color:#1d4ed8;color:#fff}.dot.cs{background:#facc15;border-color:#a16207}
.dot.cy{background:#22c55e;border-color:#15803d}.dot.ct{background:#f97316;border-color:#c2410c}.dot.rapidi{background:#e5e7eb;border-color:#6b7280}.dot.other{background:#6b7280;border-color:#374151;color:#fff}
.dot.hit{outline:3px solid #ef4444;outline-offset:1px}.dot.sel{box-shadow:0 0 0 3px var(--acc)}.legend .dot{cursor:default}
pre{white-space:pre-wrap;font-size:11.5px;color:var(--mut);max-height:200px;overflow:auto;margin:8px 0 0}details summary{cursor:pointer;font-weight:600}

/* pencere ve bildirimler */
dialog{border:0;border-radius:18px;padding:20px;max-width:min(440px,calc(100vw - 32px));width:100%;background:var(--surface);color:var(--fg);box-shadow:0 20px 60px rgba(0,0,0,.35)}
dialog::backdrop{background:rgba(8,12,24,.55);backdrop-filter:blur(2px)}dialog h3{margin-bottom:8px}dialog p{margin:6px 0;color:var(--mut)}
dialog .actions{display:flex;gap:10px;justify-content:flex-end;margin-top:16px}
#toasts{position:fixed;right:16px;bottom:16px;display:grid;gap:8px;z-index:50;max-width:calc(100vw - 32px)}
.toast{padding:11px 14px;border-radius:12px;background:var(--fg);color:var(--bg);box-shadow:var(--shadow);font-weight:500;transition:opacity .4s,transform .4s}
.toast.ok{background:var(--ok);color:#06251a}.toast.bad{background:var(--bad);color:#fff}.toast.out{opacity:0;transform:translateY(8px)}

/* mobil */
@media(max-width:860px){.cols{grid-template-columns:minmax(0,1fr)}.sheetbox{height:62vh}}
@media(max-width:700px){
 body{font-size:16px;padding-bottom:calc(var(--nav-h) + env(safe-area-inset-bottom))}
 .top{padding:8px 14px;padding-top:max(8px,env(safe-area-inset-top))}.brand{flex:1 1 0}.brand>div{min-width:0}.brand small{max-width:none}
 .chips{display:none}.spacer{display:none}
 .tabs{position:fixed;left:0;right:0;bottom:0;z-index:30;padding:6px 6px calc(6px + env(safe-area-inset-bottom));justify-content:space-around;gap:0;
  background:color-mix(in srgb,var(--surface) 92%,transparent);backdrop-filter:blur(14px);border-top:1px solid var(--line)}
 .tabs button{flex-direction:column;gap:2px;padding:6px 8px;font-size:11px;flex:1;border-radius:10px}
 .wrap{padding:6px 12px 24px}#stagedBar{margin:0 12px;top:54px}
 .card{padding:14px;border-radius:12px}.row>.field{flex:1 1 calc(50% - 10px)}.row>.grow{flex:1 1 100%}.row .btn{flex:1 1 auto}
 .tiles{grid-template-columns:repeat(3,1fr);gap:8px}.tile{padding:8px 10px}.tile b{font-size:19px}.tile span{font-size:11px}.tile .dot,.legend .dot{width:13px;height:13px;min-height:0}
 .legend{gap:8px 12px;font-size:12px}
 .straw{grid-template-columns:1fr 1fr}.straw>.field:first-child{grid-column:1/-1}.change{grid-template-columns:1fr}.change .o{display:none}
 .btn{min-height:46px}input,select,textarea{font-size:16px;min-height:46px}
 .can{width:min(84vw,280px)}.dot{width:22px;height:22px;line-height:18px;font-size:10px}.lh span,.lv{width:106px}.lh{padding-left:36px}
 #toasts{left:12px;right:12px;bottom:calc(var(--nav-h) + 12px + env(safe-area-inset-bottom))}
 dialog{margin:auto 16px calc(var(--nav-h) + 8px) 16px;max-width:none;width:auto}
}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<div id="prodBar" hidden>⚠ GERÇEK DOSYA — değişiklikler canlı haritaya yazılır</div>
<header class="top">
  <div class="brand">
    <svg width="34" height="34" viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#2563eb"/><circle cx="22" cy="24" r="7" fill="#fff"/><circle cx="42" cy="24" r="7" fill="#facc15"/><circle cx="22" cy="44" r="7" fill="#22c55e"/><circle cx="42" cy="44" r="7" fill="#f97316"/></svg>
    <div><b>Tank Haritası</b><small id="file">…</small></div>
  </div>
  <div class="chips"><span class="chip" id="mode">…</span><span class="chip" id="bk"></span></div>
  <span class="spacer"></span>
  <button class="btn ghost" id="quit" title="Programı kapat">Kapat</button>
</header>
<nav class="tabs" id="tabs" aria-label="Bölümler">
  <button data-view="viz" class="on"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>Tank haritası</button>
  <button data-view="reg"><svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M19 8v6M16 11h6"/></svg>Yeni hasta</button>
  <button data-view="rem"><svg viewBox="0 0 24 24"><circle cx="9" cy="8" r="4"/><path d="M2 21c0-4 3-6 7-6s7 2 7 6M16 11h6"/></svg>Hasta çıkar</button>
  <button data-view="map"><svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16"/></svg>Tablo</button>
</nav>
<div id="stagedBar" hidden><span id="stagedTxt"></span><button class="btn primary" id="commit">OneDrive'a yükle…</button></div>

<main class="wrap">
<!-- Tank haritası -->
<section id="v-viz">
  <div class="card">
    <div class="row">
      <label class="field" style="max-width:200px"><span>Tank</span><select id="vTank"></select></label>
      <label class="field grow"><span>Hasta ara (soyad/ad) — haritada işaretlenir</span><input id="vq" placeholder="örn. yılmaz" enterkeyhint="search"></label>
      <button class="btn primary" id="vFind">Ara</button><button class="btn" id="vRefresh">Yenile</button>
    </div>
    <div class="mut" id="vInfo" style="margin-top:8px"></div>
  </div>
  <div class="card">
    <div class="tiles" id="vTiles"></div>
    <div class="legend" id="vLegend"></div>
    <div id="vizCans"></div>
  </div>
  <div class="card" id="vDetail" hidden></div>
</section>

<!-- Yeni hasta -->
<section id="v-reg" hidden class="steps">
  <div class="card step"><h3>Yer öner</h3>
    <div class="row">
      <label class="field"><span>Tank</span><select id="rTank"></select></label>
      <label class="field"><span>Straw sayısı</span><input id="rN" type="number" inputmode="numeric" min="1" max="12" value="2"></label>
      <label class="field"><span>Tür</span><select id="rType"></select></label>
      <label class="field"><span>Kat</span><select id="rKat"><option value="otomatik">Otomatik (önce alt)</option><option value="alt">Yalnız alt</option><option value="ust">Yalnız üst</option></select></label>
      <button class="btn primary" id="rSuggest">Yer öner</button>
    </div>
    <div class="list" id="rPlans" style="margin-top:12px"></div>
  </div>
  <div class="card step" id="rStep2" hidden><h3>Straw renkleri ve hasta bilgileri</h3>
    <div id="rStraws"></div>
    <div class="row" style="margin-top:10px">
      <label class="field grow"><span>Soyad</span><input id="pSoyad" autocomplete="off"></label>
      <label class="field grow"><span>Ad</span><input id="pAd" autocomplete="off"></label>
      <label class="field grow"><span>Eşi (isteğe bağlı)</span><input id="pEsi" autocomplete="off"></label>
      <label class="field"><span>Tarih</span><input id="pDate" type="date"></label>
      <button class="btn primary" id="rPreview">Önizle</button>
    </div>
    <div id="rErr"></div>
  </div>
  <div class="card step" id="rStep3" hidden><h3>Onay</h3>
    <div class="changes" id="rChanges"></div>
    <p class="mut">Onaylarsanız önce OneDrive'daki <b>Yedekler</b> klasörüne yedek alınır, sonra yukarıdaki hücreler yazılır.</p>
    <div class="row"><button class="btn primary" id="rApply">Onayla ve yaz</button><button class="btn" id="rCancel">Vazgeç</button></div>
    <div id="rMsg"></div>
  </div>
</section>

<!-- Hasta çıkar -->
<section id="v-rem" hidden>
  <div class="card"><h3>Hasta çıkar</h3>
    <p class="mut" style="margin-top:-4px">Satırın hücrelerini temizler; dosya, satır ve <b>NO</b> etiketi silinmez.</p>
    <div class="row"><label class="field grow"><span>Soyad veya ad</span><input id="xq" placeholder="en az 2 harf" enterkeyhint="search"></label><button class="btn primary" id="xSearch">Ara</button></div>
    <div class="mut" id="xInfo" style="margin:8px 0"></div>
    <div class="list" id="xHits"></div>
    <div class="row" style="margin-top:12px"><button class="btn" id="xPreview">Seçilenleri önizle</button></div>
  </div>
  <div class="card" id="xStep2" hidden><h3>Temizlenecek hücreler</h3>
    <div class="changes" id="xChanges"></div>
    <p class="mut">Onaylarsanız önce <b>Yedekler</b> klasörüne yedek alınır. Eski değerler değişiklik kaydında da tutulur.</p>
    <div class="row"><button class="btn danger" id="xApply">Onayla ve temizle</button><button class="btn" id="xCancel">Vazgeç</button></div>
    <div id="xMsg"></div>
  </div>
</section>

<!-- Tablo -->
<section id="v-map" hidden>
  <div class="cols">
    <div class="card">
      <div class="row">
        <label class="field"><span>Sayfa</span><select id="sheet"></select></label>
        <label class="field grow"><span>Ara</span><input id="q" placeholder="en az 2 harf"></label>
        <label class="field"><span>Satır</span><select id="per" title="Sayfa başına satır"><option value="50">50 satır</option><option value="100">100 satır</option><option value="250">250 satır</option><option value="5000">Tümü</option></select></label>
        <label class="field"><span>Yakınlaştırma</span><select id="zoom"><option value="13">100%</option><option value="11">85%</option><option value="9">70%</option><option value="7">55%</option></select></label>
      </div>
      <div class="row" style="margin:10px 0"><button class="btn" id="refresh">Yenile</button><button class="btn" id="prev">◀</button><button class="btn" id="next">▶</button><span class="mut" id="range"></span></div>
      <div class="found" id="results"></div>
      <div class="sheetbox" id="wrap"><table id="grid"></table></div>
    </div>
    <aside class="card" id="cellPanel">
      <h3>Hücre düzenle</h3>
      <div id="idle" class="mut">Düzenlemek için bir hücreye dokunun.</div>
      <div id="edit" hidden>
        <b id="addr"></b>
        <p class="mut" style="margin:6px 0 2px">Şu anki değer</p><div id="cur" style="word-break:break-word;margin-bottom:10px"></div>
        <label class="field"><span>Yeni değer (boş = hücreyi temizle)</span><textarea id="nv" rows="3"></textarea></label>
        <div class="row" style="margin-top:10px"><button class="btn primary" id="review">Gözden geçir</button></div>
      </div>
      <div id="confirm" hidden>
        <div class="changes"><div class="change" style="grid-template-columns:1fr"><span class="w" id="caddr"></span><span class="o" style="display:block" id="co"></span><span class="n" id="cn"></span></div></div>
        <p class="mut">Onaylarsanız önce <b>Yedekler</b> klasörüne yedek alınır, sonra yazılır.</p>
        <div class="row"><button class="btn primary" id="yes">Onayla ve uygula</button><button class="btn" id="no">Vazgeç</button></div>
      </div>
      <div id="msg"></div>
    </aside>
  </div>
</section>

<details class="card"><summary>Son işlem kayıtları</summary><pre id="log"></pre></details>
</main>

<dialog id="dlg"><form method="dialog"><h3 id="dlgTitle"></h3><div id="dlgBody"></div>
  <div class="actions"><button class="btn" value="cancel">Vazgeç</button><button class="btn primary" id="dlgOk" value="ok">Onayla</button></div></form></dialog>
<div id="toasts" aria-live="polite"></div>

<script>
const TOKEN="__TOKEN__";const $=id=>document.getElementById(id);
function h(tag,a,...kids){const e=document.createElement(tag);for(const[k,v]of Object.entries(a||{})){if(k==="class")e.className=v;else if(k.startsWith("on"))e[k]=v;else if(v!==false&&v!=null)e.setAttribute(k,v===true?"":v);}
  kids.flat().forEach(c=>{if(c==null||c===false)return;e.append(c instanceof Node?c:document.createTextNode(String(c)));});return e;}
async function api(path,body){const o=body===undefined?{headers:{"X-Session-Token":TOKEN}}:{method:"POST",headers:{"X-Session-Token":TOKEN,"Content-Type":"application/json"},body:JSON.stringify(body)};
  const r=await fetch(path,o);return r.json();}
async function busy(btn,fn){btn.disabled=true;btn.classList.add("loading");try{return await fn();}finally{btn.disabled=false;btn.classList.remove("loading");}}
function toast(msg,kind){const t=h("div",{class:"toast "+(kind||"")},msg);$("toasts").append(t);setTimeout(()=>t.classList.add("out"),3800);setTimeout(()=>t.remove(),4300);}
function alertBox(el,msg,kind){el.textContent="";if(msg)el.append(h("div",{class:"alert "+(kind||"info")},msg));}
function ask(title,body,ok,danger){return new Promise(res=>{const d=$("dlg");if(typeof d.showModal!=="function"){res(confirm(title+"\n"+(Array.isArray(body)?body.join("\n"):body)));return;}
  $("dlgTitle").textContent=title;const b=$("dlgBody");b.textContent="";(Array.isArray(body)?body:[body]).forEach(x=>b.append(x instanceof Node?x:h("p",{},x)));
  const okb=$("dlgOk");okb.textContent=ok||"Onayla";okb.className="btn "+(danger?"danger":"primary");d.returnValue="";d.onclose=()=>res(d.returnValue==="ok");d.showModal();});}

/* ---- gezinme ve genel durum */
let S={},CUR="viz";
function show(v){CUR=v;["viz","reg","rem","map"].forEach(x=>$("v-"+x).hidden=x!==v);
  document.querySelectorAll("#tabs button").forEach(b=>b.classList.toggle("on",b.dataset.view===v));
  if(v==="reg")regInit();if(v==="viz")vizInit();if(v==="map")mapInit();try{history.replaceState(null,"","#"+v);}catch(_){}window.scrollTo(0,0);}
document.querySelectorAll("#tabs button").forEach(b=>b.onclick=()=>show(b.dataset.view));
async function state(){S=await api("/api/state");$("file").textContent=S.file;$("mode").textContent=S.mode==="excel-api"?"Excel API":"Bellek modu (eTag)";
  $("prodBar").hidden=!S.production;$("bk").textContent=S.backup?"✓ Yedek alındı":"Yedek: ilk onayda";$("bk").title=S.backup||"";
  $("stagedBar").hidden=!(S.needs_commit&&S.staged);$("stagedTxt").textContent=S.staged+" değişiklik OneDrive'a yüklenmeyi bekliyor";
  const sh=$("sheet");if(!sh.options.length)S.sheets.forEach(n=>sh.add(new Option(n,n)));}
async function logs(){const r=await api("/api/log");$("log").textContent=r.lines.map(l=>{try{const e=JSON.parse(l);return e.ts.slice(11,19)+" "+e.event+(e.cell?" "+e.sheet+"!"+e.cell:"");}catch(_){return l;}}).join("\n");}
$("commit").onclick=async()=>{const p=await api("/api/commit/prepare");
  if(!p.ok){toast(p.message||("Yüklenemez: "+[...(p.problems||[]),...(p.lost||[])].join("; ")),"bad");return;}
  if(!await ask(p.count+" değişiklik yüklenecek",[p.changes.join(", "),"Dosya başkası tarafından değiştirilmişse hiçbir şey yazılmaz."],"Yükle"))return;
  const r=await busy($("commit"),()=>api("/api/commit",{}));toast(r.message,r.ok?"ok":"bad");await state();if(CUR==="map")loadSheet(true);if(CUR==="viz")loadViz();logs();};
$("quit").onclick=async()=>{const warn=S.staged?["Yüklenmemiş "+S.staged+" değişiklik kaybolur."]:["Tarayıcı sekmesini sonra kapatabilirsiniz."];
  if(!await ask("Program kapatılsın mı?",warn,"Kapat",!!S.staged))return;await api("/api/shutdown",{});
  document.body.textContent="";document.body.append(h("div",{style:"padding:40px;text-align:center"},h("h2",{},"Program kapatıldı"),h("p",{class:"mut"},"Bu sekmeyi kapatabilirsiniz.")));};

/* ---- Tank haritası */
const CCLS={"MAVİ":"cm","SARI":"cs","YEŞİL":"cy","TURUNCU":"ct"},CLET={"MAVİ":"M","SARI":"S","YEŞİL":"Y","TURUNCU":"T"};
function dotEl(s){const d=h("button",{class:"dot "+(s.state==="color"?CCLS[s.color]:s.state),type:"button","data-id":s.id,
  title:(s.state==="empty"?"boş":(s.vial||"dolu"))+" · satır "+s.row,"aria-label":(s.state==="empty"?"boş":(s.vial||"dolu"))+", satır "+s.row},
  s.state==="color"?CLET[s.color]:(s.state==="rapidi"?"R":(s.state==="other"?"?":"")));d.onclick=()=>slotClick(s.id,d);return d;}
function legend(){const L=$("vLegend");L.textContent="";[["empty","Boş"],["cm","Mavi"],["cs","Sarı"],["cy","Yeşil"],["ct","Turuncu"],["rapidi","Rapidi (renksiz)"],["other","Dolu, renk okunamadı"]]
  .forEach(([c,t])=>L.append(h("span",{},h("span",{class:"dot "+c}),t)));}
async function vizInit(){legend();const o=await api("/api/reg/options");const t=$("vTank");const keep=t.value;t.textContent="";
  o.tanks.forEach(n=>t.add(new Option("Tank "+n,n)));if(keep)t.value=keep;await loadViz();}
function tile(label,val,cls){return h("div",{class:"tile"},h("b",{},val),h("span",{},cls?h("span",{class:"dot "+cls,style:"cursor:default"}):null,label));}
async function loadViz(){$("vDetail").hidden=true;const m=await api("/api/map?tank="+$("vTank").value);const box=$("vizCans");box.textContent="";const T=$("vTiles");T.textContent="";
  if(!m.ok){box.append(h("div",{class:"mut"},m.message));return;}const st=m.stats;
  T.append(tile("Toplam straw yeri",st.slots),tile("Boş",st.free,"empty"),tile("Mavi",st["MAVİ"],"cm"),tile("Sarı",st["SARI"],"cs"),tile("Yeşil",st["YEŞİL"],"cy"),tile("Turuncu",st["TURUNCU"],"ct"),tile("Rapidi",st.rapidi,"rapidi"));
  if(st.other)T.append(tile("Renk okunamadı",st.other,"other"));if(m.nonstandard)T.append(tile("Haritada olmayan konum",m.nonstandard));
  m.canisters.forEach(c=>{const cd=h("div",{class:"can"},h("h4",{},"Canister "+c.canister),h("div",{class:"lh"},h("span",{},m.has_ust?"üst":""),h("span",{},"alt")));
    c.goblets.forEach(g=>{const row=h("div",{class:"gob"},h("span",{class:"gn"},g.n));
      [["ust",m.has_ust],["alt",true]].forEach(([k,on])=>{if(!on)return;const lv=h("span",{class:"lv"});
        if(g[k])g[k].slots.forEach(s=>lv.append(dotEl(s)));else lv.append(h("span",{class:"none"},"—"));row.append(lv);});cd.append(row);});box.append(cd);});}
async function slotClick(id,el){document.querySelectorAll(".dot.sel").forEach(x=>x.classList.remove("sel"));el.classList.add("sel");
  const r=await api("/api/map/slot",{id});const d=$("vDetail");d.textContent="";d.hidden=false;
  if(!r.ok){d.append(h("div",{},r.message));return;}d.append(h("div",{class:"mut"},r.where));
  if(r.state==="empty"){d.append(h("b",{},"Boş straw yeri"));}
  else{d.append(h("h3",{style:"margin:4px 0"},`${r.soyad} ${r.ad}`+(r.esi?` (eşi: ${r.esi})`:"")),h("div",{},`${r.vial||"-"} · ${r.hucre||"-"} · ${r.tarih||"-"}`),
    h("div",{class:"row",style:"margin-top:10px"},h("button",{class:"btn",onclick:()=>{$("xq").value=r.soyad;show("rem");$("xSearch").click();}},"Hasta çıkar ekranında aç")));}
  d.scrollIntoView({behavior:"smooth",block:"nearest"});}
$("vTank").onchange=loadViz;$("vRefresh").onclick=()=>busy($("vRefresh"),loadViz);
$("vFind").onclick=()=>busy($("vFind"),async()=>{document.querySelectorAll(".dot.hit").forEach(x=>x.classList.remove("hit"));$("vInfo").textContent="";
  const r=await api("/api/map/find",{q:$("vq").value,tank:+$("vTank").value});if(!r.ok){$("vInfo").textContent=r.message;return;}
  let first=null;r.hits.forEach(x=>{const el=document.querySelector(`.dot[data-id="${CSS.escape(x.id)}"]`);if(el){el.classList.add("hit");first=first||el;}});
  $("vInfo").textContent=r.hits.length?`${r.hits.length} straw: `+r.hits.slice(0,6).map(x=>x.where).join(" | "):"Bu tankta eşleşme yok.";
  if(first)first.scrollIntoView({block:"center",inline:"center",behavior:"smooth"});});
$("vq").onkeydown=e=>{if(e.key==="Enter")$("vFind").click();};

/* ---- Yeni hasta */
let R={plans:[],plan:null,regId:null};
async function regInit(){const o=await api("/api/reg/options");const t=$("rTank");const keep=t.value;t.textContent="";
  o.tanks.forEach(n=>t.add(new Option(`Tank ${n} (${o.free_rows[n]} boş satır)`,n)));if(keep)t.value=keep;
  const ty=$("rType");if(!ty.options.length)o.types.forEach(x=>ty.add(new Option(x,x)));
  if(!$("pDate").value){const d=new Date();$("pDate").value=d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");}}
function planText(pl){return pl.placements.map(p=>`Canister ${p.canister} · ${p.label} (${p.kat}) · satır ${p.rows[0]}${p.rows.length>1?"–"+p.rows[p.rows.length-1]:""}`).join("  →  ");}
$("rSuggest").onclick=()=>busy($("rSuggest"),async()=>{$("rStep2").hidden=true;$("rStep3").hidden=true;const box=$("rPlans");box.textContent="";
  const r=await api("/api/reg/suggest",{tank:+$("rTank").value,n:+$("rN").value,kat:$("rKat").value});
  if(!r.ok||!r.plans.length){box.append(h("div",{class:"alert info"},r.message||"Uygun yer bulunamadı."));return;}R.plans=r.plans;
  r.plans.forEach((pl,i)=>{const rb=h("input",{type:"radio",name:"plan",onclick:()=>pickPlan(pl)});
    const colors=pl.placements.map(p=>p.colors.join(" · ")).join("  /  ");
    box.append(h("label",{class:"item pick"},rb,h("div",{class:"grow"},h("b",{},`${i+1}. ${planText(pl)}`),h("div",{class:"sub"},"Renkler: "+colors))));});});
function pickPlan(pl){R.plan=pl;$("rStep3").hidden=true;$("rStep2").hidden=false;const box=$("rStraws");box.textContent="";const ins=[];
  pl.placements.forEach((p,pi)=>p.rows.forEach((row,ri)=>{const sel=h("select",{"data-p":pi},p.free_colors.map(c=>h("option",{value:c},c)));sel.value=p.colors[ri];
    const inp=h("input",{placeholder:"örn. D5 (4AA)",autocomplete:"off"});ins.push(inp);
    box.append(h("div",{class:"straw"},h("div",{},h("b",{},`Canister ${p.canister} · ${p.label} (${p.kat})`),h("div",{class:"sub"},"satır "+row)),
      h("label",{class:"field"},h("span",{},"Renk"),sel),h("label",{class:"field"},h("span",{},"HÜCRE"),inp)));}));
  ins.forEach((i,k)=>i.oninput=()=>{if(k>0)i.dataset.touched="1";else ins.slice(1).forEach(o=>{if(!o.dataset.touched)o.value=ins[0].value;});});
  $("rStep2").scrollIntoView({behavior:"smooth",block:"start"});}
function changesTable(el,list,after){el.textContent="";list.forEach(c=>el.append(h("div",{class:"change"},h("span",{class:"w"},c.where),h("span",{class:"o"},c.old||"(boş)"),h("span",{class:"n"},c.new===""?"(boş)":c.new))));}
$("rPreview").onclick=()=>busy($("rPreview"),async()=>{alertBox($("rErr"),"");alertBox($("rMsg"),"");
  const straws=[...$("rStraws").querySelectorAll(".straw")].map(d=>({color:d.querySelector("select").value,hucre:d.querySelector("input").value}));
  const r=await api("/api/reg/preview",{plan_id:R.plan.id,straw_type:$("rType").value,straws,patient:{soyad:$("pSoyad").value,ad:$("pAd").value,esi:$("pEsi").value,tarih:$("pDate").value}});
  if(!r.ok){$("rStep3").hidden=true;alertBox($("rErr"),r.message,"bad");return;}R.regId=r.id;changesTable($("rChanges"),r.changes);$("rStep3").hidden=false;$("rStep3").scrollIntoView({behavior:"smooth",block:"start"});});
$("rApply").onclick=()=>busy($("rApply"),async()=>{const r=await api("/api/reg/apply",{id:R.regId});alertBox($("rMsg"),r.message,r.ok?"ok":"bad");
  if(r.ok){R.regId=null;toast("Kayıt yazıldı","ok");await state();$("rPlans").textContent="";$("rStep2").hidden=true;$("pSoyad").value=$("pAd").value=$("pEsi").value="";}logs();});
$("rCancel").onclick=()=>{R.regId=null;$("rStep3").hidden=true;};

/* ---- Hasta çıkar */
let X={regId:null};
$("xSearch").onclick=()=>busy($("xSearch"),async()=>{alertBox($("xMsg"),"");$("xStep2").hidden=true;const t=$("xHits");t.textContent="";
  const r=await api("/api/rem/search",{q:$("xq").value});if(!r.ok){$("xInfo").textContent=r.message;return;}
  $("xInfo").textContent=r.hits.length?`${r.hits.length} satır bulundu${r.truncated?" (ilk 200)":""}. Temizlenecekleri işaretleyin.`:"Eşleşme yok.";
  r.hits.forEach(x=>{const cb=h("input",{type:"checkbox","data-sheet":x.sheet,"data-row":x.row,"data-col":x.col});
    t.append(h("label",{class:"item pick"},cb,h("div",{class:"grow"},h("b",{},`${x.soyad} ${x.ad}`+(x.esi?` · eşi ${x.esi}`:"")),
      h("div",{class:"sub"},`Tank ${x.tank||"?"} · Canister ${x.canister||"?"} · ${x.label} (${x.kat}) · satır ${x.row}`),h("div",{class:"sub"},`${x.vial||"-"} · ${x.hucre||"-"} · ${x.tarih||"-"}`))));});});
$("xq").onkeydown=e=>{if(e.key==="Enter")$("xSearch").click();};
$("xPreview").onclick=()=>busy($("xPreview"),async()=>{alertBox($("xMsg"),"");const items=[...$("xHits").querySelectorAll("input:checked")].map(c=>({sheet:c.dataset.sheet,row:+c.dataset.row,col:+c.dataset.col}));
  const r=await api("/api/rem/preview",{items});if(!r.ok){$("xStep2").hidden=true;toast(r.message,"bad");return;}X.regId=r.id;changesTable($("xChanges"),r.changes);$("xStep2").hidden=false;$("xStep2").scrollIntoView({behavior:"smooth",block:"start"});});
$("xApply").onclick=async()=>{if(!await ask("Seçilen satırlar temizlensin mi?","Hücrelerin içeriği silinir (dosya ve satırlar kalır). Önce yedek alınır.","Temizle",true))return;
  await busy($("xApply"),async()=>{const r=await api("/api/rem/apply",{id:X.regId});alertBox($("xMsg"),r.message,r.ok?"ok":"bad");
    if(r.ok){X.regId=null;$("xHits").textContent="";$("xInfo").textContent="";toast("Temizlendi","ok");await state();}logs();});};
$("xCancel").onclick=()=>{X.regId=null;$("xStep2").hidden=true;};

/* ---- Tablo (Excel görünümü) */
let view=null,row0=1,sel=null,pid=null,mapReady=false;
async function mapInit(){if(!mapReady){mapReady=true;await loadSheet();}}
async function loadSheet(fresh){const v=await api(`/api/sheet?name=${encodeURIComponent($("sheet").value)}&row0=${row0}&rows=${$("per").value}${fresh?"&fresh=1":""}`);
  if(v.ok===false){alertBox($("msg"),v.message,"bad");return;}view=v;row0=v.row0;
  const t=$("grid");t.textContent="";const hr=t.insertRow();hr.append(h("th"));v.cols.forEach(c=>hr.append(h("th",{},c)));
  v.rows.forEach((r,i)=>{const tr=t.insertRow();tr.append(h("td",{class:"rn"},v.row0+i));
    r.forEach((val,j)=>{const td=h("td",{class:"c",title:val},val);td.onclick=()=>pick(v.cols[j]+(v.row0+i),val,td);tr.append(td);});});
  t.style.fontSize=$("zoom").value+"px";const per=+$("per").value;$("range").textContent=`satır ${v.row0}–${Math.min(v.row0+per-1,v.max_row)} / ${v.max_row} · ${v.max_col} sütun`;}
function pick(addr,val,td){document.querySelectorAll("td.sel").forEach(x=>x.classList.remove("sel"));td.classList.add("sel");
  sel={sheet:$("sheet").value,cell:addr};$("addr").textContent=sel.sheet+" ! "+addr;$("cur").textContent=val===""?"(boş)":val;
  $("nv").value="";$("idle").hidden=true;$("edit").hidden=false;$("confirm").hidden=true;alertBox($("msg"),"");
  if(matchMedia("(max-width:860px)").matches)$("cellPanel").scrollIntoView({behavior:"smooth",block:"start"});}
$("review").onclick=()=>busy($("review"),async()=>{const r=await api("/api/propose",{sheet:sel.sheet,cell:sel.cell,value:$("nv").value});
  if(!r.ok){alertBox($("msg"),r.message,"bad");return;}pid=r.id;$("caddr").textContent=r.sheet+" ! "+r.cell;
  $("co").textContent=r.old===""?"(boş)":r.old;$("cn").textContent=r.new===""?"(boş)":r.new;$("edit").hidden=true;$("confirm").hidden=false;alertBox($("msg"),"");});
$("no").onclick=async()=>{await api("/api/decline",{id:pid});pid=null;$("confirm").hidden=true;$("edit").hidden=false;alertBox($("msg"),"Vazgeçildi.");logs();};
$("yes").onclick=()=>busy($("yes"),async()=>{const r=await api("/api/apply",{id:pid});pid=null;$("confirm").hidden=true;alertBox($("msg"),r.message,r.ok?"ok":"bad");
  if(r.ok){$("idle").hidden=false;$("edit").hidden=true;await state();await loadSheet(true);}logs();});
let qt;$("q").oninput=()=>{clearTimeout(qt);qt=setTimeout(async()=>{const q=$("q").value;const box=$("results");box.textContent="";if(q.trim().length<2)return;
  const r=await api("/api/search?q="+encodeURIComponent(q));
  r.hits.forEach(x=>box.append(h("div",{onclick:async()=>{$("sheet").value=x.sheet;row0=Math.max(1,x.row-3);await loadSheet();box.textContent="";}},`${x.sheet} ! ${x.cell} — ${x.value}`)));
  if(!r.hits.length)box.textContent="Eşleşme yok.";},300);};
$("sheet").onchange=()=>{row0=1;loadSheet();};$("refresh").onclick=()=>busy($("refresh"),()=>loadSheet(true));
$("per").onchange=()=>{row0=1;loadSheet();};$("zoom").onchange=()=>{$("grid").style.fontSize=$("zoom").value+"px";};
$("prev").onclick=()=>{row0=Math.max(1,row0-+$("per").value);loadSheet();};
$("next").onclick=()=>{const per=+$("per").value;if(view&&row0+per<=view.max_row){row0+=per;loadSheet();}};

(async()=>{await state();const v=(location.hash||"").slice(1);show(["viz","reg","rem","map"].includes(v)?v:"viz");logs();})();
</script></body></html>"""
