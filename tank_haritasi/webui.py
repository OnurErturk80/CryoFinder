"""Yerel tarayıcı arayüzü. Yalnızca 127.0.0.1'e bağlanır; oturum anahtarı, Host/Origin denetimi ve
JSON-only POST ile başka web sitelerinin (CSRF / DNS rebinding) bu arayüzü kullanması engellenir."""
from __future__ import annotations

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .service import EditService

MAX_BODY = 64 * 1024


def make_server(service: EditService, log_path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        server_version = "TankHaritasi"

        def log_message(self, *a):  # konsola hücre içeriği sızmasın
            pass

        # -- yardımcılar
        def _hosts(self):
            p = self.server.server_address[1]
            return {f"127.0.0.1:{p}", f"localhost:{p}"}

        def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        def _guard(self, api: bool) -> bool:
            if self.headers.get("Host") not in self._hosts():
                self._json({"ok": False, "message": "Geçersiz Host"}, 403); return False
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://{h}" for h in self._hosts()}:
                self._json({"ok": False, "message": "Geçersiz Origin"}, 403); return False
            if api and not secrets.compare_digest(self.headers.get("X-Session-Token", ""), token):
                self._json({"ok": False, "message": "Oturum anahtarı geçersiz"}, 403); return False
            return True

        # -- yönlendirme
        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/":
                if self._guard(False):
                    self._send(200, PAGE.replace("__TOKEN__", token).encode("utf-8"), "text/html; charset=utf-8")
                return
            if not url.path.startswith("/api/") or not self._guard(True):
                if not url.path.startswith("/api/"):
                    self._json({"ok": False, "message": "yok"}, 404)
                return
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            try:
                if url.path == "/api/state":
                    self._json(service.state())
                elif url.path == "/api/sheet":
                    self._json(service.sheet_view(q["name"], int(q.get("row0", 1)), int(q.get("rows", 50)),
                                                  q.get("fresh") == "1"))
                elif url.path == "/api/search":
                    self._json({"hits": service.search(q.get("q", ""))})
                elif url.path == "/api/reg/options":
                    self._json(service.reg_options())
                elif url.path == "/api/log":
                    self._json({"lines": service.recent_log(log_path)})
                else:
                    self._json({"ok": False, "message": "yok"}, 404)
            except Exception as e:  # noqa: BLE001
                self._json({"ok": False, "message": str(e)}, 400)

        def do_POST(self):
            url = urlparse(self.path)
            if not self._guard(True):
                return
            if not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self._json({"ok": False, "message": "JSON bekleniyor"}, 415); return
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                self._json({"ok": False, "message": "çok büyük"}, 413); return
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if url.path == "/api/propose":
                    self._json(service.propose(body["sheet"], body["cell"], body.get("value", "")))
                elif url.path == "/api/apply":
                    self._json(service.apply(body["id"]))
                elif url.path == "/api/reg/suggest":
                    self._json(service.reg_suggest(int(body["tank"]), int(body["n"]), str(body.get("kat", "otomatik"))))
                elif url.path == "/api/reg/preview":
                    self._json(service.reg_preview(str(body["plan_id"]), str(body["straw_type"]),
                                                   list(body["straws"]), dict(body["patient"])))
                elif url.path == "/api/reg/apply":
                    self._json(service.reg_apply(str(body["id"])))
                elif url.path == "/api/decline":
                    self._json(service.decline(body["id"]))
                elif url.path == "/api/commit/prepare":
                    self._json(service.prepare_commit())
                elif url.path == "/api/commit":
                    self._json(service.commit())
                else:
                    self._json({"ok": False, "message": "yok"}, 404)
            except Exception as e:  # noqa: BLE001
                self._json({"ok": False, "message": str(e)}, 400)

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return srv, token


def serve_in_thread(srv) -> threading.Thread:
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return t


PAGE = r"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tank Haritası</title>
<style>
:root{--bg:#f6f7f9;--fg:#1c2330;--mut:#667085;--line:#d9dde4;--card:#fff;--acc:#1a56db;--ok:#067647;--bad:#b42318;--warn:#fef0c7}
@media(prefers-color-scheme:dark){:root{--bg:#10141b;--fg:#e6e9ef;--mut:#98a2b3;--line:#2a3140;--card:#181d27;--acc:#6ea0ff;--ok:#47cd89;--bad:#f97066;--warn:#3a2f10}}
*{box-sizing:border-box}[hidden]{display:none!important}body{margin:0;font:14px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--fg)}
header{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 16px;background:var(--card);border-bottom:1px solid var(--line)}
header b{font-size:15px}.pill{padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut);font-size:12px}
.prod{background:var(--bad);color:#fff;border-color:var(--bad)}
main{display:grid;grid-template-columns:1fr 340px;gap:16px;padding:16px}
@media(max-width:900px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
input,select,button,textarea{font:inherit;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--fg)}
button{cursor:pointer}button.p{background:var(--acc);color:#fff;border-color:var(--acc)}button.d{border-color:var(--bad);color:var(--bad)}
button:disabled{opacity:.5;cursor:not-allowed}
#wrap{overflow:auto;max-height:68vh;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:max-content;min-width:100%}
th,td{border:1px solid var(--line);padding:3px 8px;white-space:nowrap;max-width:260px;overflow:hidden;text-overflow:ellipsis;font-size:13px}
th{background:var(--bg);position:sticky;top:0;color:var(--mut);font-weight:600}
td.rn{background:var(--bg);color:var(--mut);position:sticky;left:0}
td.c{cursor:pointer}td.c:hover{outline:2px solid var(--acc);outline-offset:-2px}td.sel{background:var(--warn)}
.mut{color:var(--mut)}.ok{color:var(--ok)}.bad{color:var(--bad)}
.diff{border:1px solid var(--line);border-radius:8px;padding:8px;margin:8px 0;background:var(--bg)}
.diff div{word-break:break-word}.old{color:var(--bad)}.new{color:var(--ok)}
#results{max-height:160px;overflow:auto;margin-bottom:8px}#results div{padding:3px 6px;cursor:pointer;border-radius:6px}#results div:hover{background:var(--bg)}
pre{white-space:pre-wrap;font-size:11px;color:var(--mut);max-height:180px;overflow:auto;margin:0}
</style></head><body>
<header><b id="file">…</b><button id="tabMap" class="p">Harita</button><button id="tabReg">Yeni hasta</button><span class="pill" id="mode"></span><span class="pill prod" id="prod" hidden>GERÇEK DOSYA</span>
<span class="pill" id="bk"></span><span style="flex:1"></span><span id="pend" class="mut"></span>
<button class="p" id="commit" hidden>OneDrive'a yükle…</button></header>
<main id="mapView">
<section class="card">
  <div class="bar"><select id="sheet"></select><input id="q" placeholder="Ara (en az 2 harf)…" size="22">
   <button id="refresh">Yenile</button><button id="prev">◀</button><button id="next">▶</button><span class="mut" id="range"></span></div>
  <div id="results"></div>
  <div id="wrap"><table id="grid"></table></div>
</section>
<aside class="card">
  <h3 style="margin-top:0">Değişiklik</h3>
  <div id="idle" class="mut">Bir hücreye tıklayın.</div>
  <div id="edit" hidden>
    <div><b id="addr"></b></div>
    <div class="mut">Şu anki değer:</div><div id="cur" style="margin-bottom:8px;word-break:break-word"></div>
    <textarea id="nv" rows="3" style="width:100%" placeholder="Yeni değer (boş = hücreyi temizle)"></textarea>
    <div style="margin-top:8px"><button class="p" id="review">Gözden geçir</button></div>
  </div>
  <div id="confirm" hidden>
    <div class="diff"><div class="mut" id="caddr"></div><div class="old">eski: <span id="co"></span></div><div class="new">yeni: <span id="cn"></span></div></div>
    <div class="mut" style="margin-bottom:8px">Onaylarsanız önce OneDrive'daki <b>Yedekler</b> klasörüne yedek alınır, sonra yazılır.</div>
    <button class="p" id="yes">Onayla ve uygula</button> <button id="no">Vazgeç</button>
  </div>
  <div id="msg" style="margin-top:10px"></div>
  <h4>Son kayıtlar</h4><pre id="log"></pre>
</aside></main>
<main id="regView" hidden style="grid-template-columns:1fr">
<section class="card">
  <h3 style="margin-top:0">1) Yer öner</h3>
  <div class="bar">
    <label>Tank <select id="rTank"></select></label>
    <label>Straw sayısı <input id="rN" type="number" min="1" max="12" value="2" style="width:70px"></label>
    <label>Tür <select id="rType"></select></label>
    <label>Kat <select id="rKat"><option value="otomatik">Otomatik (önce alt)</option><option value="alt">Yalnız alt</option><option value="ust">Yalnız üst</option></select></label>
    <button class="p" id="rSuggest">Yer öner</button>
  </div>
  <div id="rPlans"></div>
</section>
<section class="card" id="rStep2" hidden>
  <h3 style="margin-top:0">2) Straw renkleri ve hasta bilgileri</h3>
  <table id="rStraws"></table>
  <div class="bar" style="margin-top:10px">
    <label>Soyad <input id="pSoyad" size="16"></label><label>Ad <input id="pAd" size="16"></label>
    <label>Eşi <input id="pEsi" size="16" placeholder="(isteğe bağlı)"></label>
    <label>Tarih <input id="pDate" type="date"></label>
    <button class="p" id="rPreview">Önizle</button>
  </div>
</section>
<section class="card" id="rStep3" hidden>
  <h3 style="margin-top:0">3) Onay</h3>
  <div style="max-height:260px;overflow:auto"><table id="rChanges"></table></div>
  <div class="mut" style="margin:8px 0">Onaylarsanız önce OneDrive'daki <b>Yedekler</b> klasörüne yedek alınır, sonra yukarıdaki hücreler yazılır.</div>
  <button class="p" id="rApply">Onayla ve yaz</button> <button id="rCancel">Vazgeç</button>
  <div id="rMsg" style="margin-top:10px"></div>
</section>
</main>
<script>
const TOKEN="__TOKEN__";const $=id=>document.getElementById(id);
async function api(path,body){
  const o=body===undefined?{headers:{"X-Session-Token":TOKEN}}
   :{method:"POST",headers:{"X-Session-Token":TOKEN,"Content-Type":"application/json"},body:JSON.stringify(body)};
  const r=await fetch(path,o);return r.json();}
let S={},view=null,row0=1,sel=null,pid=null;
function msg(t,cls){const m=$("msg");m.textContent=t||"";m.className=cls||"";}
async function state(){S=await api("/api/state");$("file").textContent=S.file;
  $("mode").textContent=S.mode==="excel-api"?"Excel API":"bellek-içi (eTag)";$("prod").hidden=!S.production;
  $("bk").textContent=S.backup?"Yedek: "+S.backup:"Yedek: ilk onayda alınır";
  $("commit").hidden=!S.needs_commit||!S.staged;$("pend").textContent=S.staged?S.staged+" değişiklik yüklenmeyi bekliyor":"";
  const sh=$("sheet");if(!sh.options.length){S.sheets.forEach(n=>sh.add(new Option(n,n)));}}
async function loadSheet(fresh){const v=await api(`/api/sheet?name=${encodeURIComponent($("sheet").value)}&row0=${row0}&rows=50${fresh?"&fresh=1":""}`);
  if(v.ok===false){msg(v.message,"bad");return;}view=v;row0=v.row0;
  const t=$("grid");t.textContent="";const h=t.insertRow();h.appendChild(document.createElement("th"));
  v.cols.forEach(c=>{const th=document.createElement("th");th.textContent=c;h.appendChild(th);});
  v.rows.forEach((r,i)=>{const tr=t.insertRow();const rn=tr.insertCell();rn.className="rn";rn.textContent=v.row0+i;
    r.forEach((val,j)=>{const td=tr.insertCell();td.className="c";td.textContent=val;td.title=val;
      td.onclick=()=>pick(v.cols[j]+(v.row0+i),val,td);});});
  $("range").textContent=`satır ${v.row0}–${Math.min(v.row0+49,v.max_row)} / ${v.max_row}`;}
function pick(addr,val,td){document.querySelectorAll("td.sel").forEach(x=>x.classList.remove("sel"));if(td)td.classList.add("sel");
  sel={sheet:$("sheet").value,cell:addr};$("addr").textContent=sel.sheet+" ! "+addr;$("cur").textContent=val===""?"(boş)":val;
  $("nv").value="";$("idle").hidden=true;$("edit").hidden=false;$("confirm").hidden=true;msg("");}
$("review").onclick=async()=>{const r=await api("/api/propose",{sheet:sel.sheet,cell:sel.cell,value:$("nv").value});
  if(!r.ok){msg(r.message,"bad");return;}pid=r.id;$("caddr").textContent=r.sheet+" ! "+r.cell;
  $("co").textContent=r.old===""?"(boş)":r.old;$("cn").textContent=r.new===""?"(boş)":r.new;
  $("edit").hidden=true;$("confirm").hidden=false;msg("");};
$("no").onclick=async()=>{await api("/api/decline",{id:pid});pid=null;$("confirm").hidden=true;$("edit").hidden=false;msg("Vazgeçildi.");logs();};
$("yes").onclick=async()=>{$("yes").disabled=true;const r=await api("/api/apply",{id:pid});$("yes").disabled=false;pid=null;
  $("confirm").hidden=true;msg(r.message,r.ok?"ok":"bad");if(r.ok){$("idle").hidden=false;$("edit").hidden=true;await state();await loadSheet(true);}logs();};
$("commit").onclick=async()=>{const p=await api("/api/commit/prepare");
  if(!p.ok){msg(p.message||("Yüklenemez: "+[...(p.problems||[]),...(p.lost||[])].join("; ")),"bad");return;}
  if(!confirm(p.count+" değişiklik OneDrive'a yüklenecek:\n"+p.changes.join("\n")+"\n\nDosya başkası tarafından değiştirilmişse hiçbir şey yazılmaz. Yüklensin mi?"))return;
  const r=await api("/api/commit",{});msg(r.message,r.ok?"ok":"bad");await state();await loadSheet(true);logs();};
let qt;$("q").oninput=()=>{clearTimeout(qt);qt=setTimeout(async()=>{const q=$("q").value;const box=$("results");box.textContent="";
  if(q.trim().length<2)return;const r=await api("/api/search?q="+encodeURIComponent(q));
  r.hits.forEach(h=>{const d=document.createElement("div");d.textContent=`${h.sheet} ! ${h.cell} — ${h.value}`;
   d.onclick=async()=>{$("sheet").value=h.sheet;row0=Math.max(1,h.row-3);await loadSheet();box.textContent="";};box.appendChild(d);});
  if(!r.hits.length)box.textContent="Eşleşme yok.";},300);};
$("sheet").onchange=()=>{row0=1;loadSheet();};$("refresh").onclick=()=>loadSheet(true);
$("prev").onclick=()=>{row0=Math.max(1,row0-50);loadSheet();};$("next").onclick=()=>{if(view&&row0+50<=view.max_row){row0+=50;loadSheet();}};
async function logs(){const r=await api("/api/log");$("log").textContent=r.lines.map(l=>{try{const e=JSON.parse(l);
  return e.ts.slice(11,19)+" "+e.event+(e.cell?" "+e.sheet+"!"+e.cell:"");}catch(_){return l;}}).join("\n");}
/* ---- Yeni hasta */
let R={plans:[],plan:null,regId:null};
function show(view){$("mapView").hidden=view!=="map";$("regView").hidden=view!=="reg";
  $("tabMap").className=view==="map"?"p":"";$("tabReg").className=view==="reg"?"p":"";if(view==="reg")regInit();}
$("tabMap").onclick=()=>show("map");$("tabReg").onclick=()=>show("reg");
function rmsg(t,cls){$("rMsg").textContent=t||"";$("rMsg").className=cls||"";}
async function regInit(){const o=await api("/api/reg/options");const t=$("rTank");const keep=t.value;t.textContent="";
  o.tanks.forEach(n=>t.add(new Option(`Tank ${n} (${o.free_rows[n]} boş satır)`,n)));if(keep)t.value=keep;
  const ty=$("rType");if(!ty.options.length)o.types.forEach(x=>ty.add(new Option(x,x)));
  if(!$("pDate").value){const d=new Date();$("pDate").value=d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");}}
function planText(pl){return pl.placements.map(p=>`Canister ${p.canister} / ${p.label} (${p.kat} kat) satır ${p.rows[0]}${p.rows.length>1?"–"+p.rows[p.rows.length-1]:""}: ${p.colors.join(", ")}`).join("  →  ");}
$("rSuggest").onclick=async()=>{$("rStep2").hidden=true;$("rStep3").hidden=true;const box=$("rPlans");box.textContent="";
  const r=await api("/api/reg/suggest",{tank:+$("rTank").value,n:+$("rN").value,kat:$("rKat").value});
  if(!r.ok){box.textContent=r.message;return;}R.plans=r.plans;if(!r.plans.length){box.textContent=r.message;return;}
  r.plans.forEach((pl,i)=>{const lab=document.createElement("label");lab.style.cssText="display:block;padding:6px;border:1px solid var(--line);border-radius:8px;margin:6px 0;cursor:pointer";
    const rb=document.createElement("input");rb.type="radio";rb.name="plan";rb.onclick=()=>pickPlan(pl);lab.appendChild(rb);
    lab.appendChild(document.createTextNode(` ${i+1}. ${planText(pl)}`));box.appendChild(lab);});};
function pickPlan(pl){R.plan=pl;$("rStep3").hidden=true;$("rStep2").hidden=false;const t=$("rStraws");t.textContent="";
  const h=t.insertRow();["Konum","Satır","Renk","HÜCRE (örn. D5 (4AA))"].forEach(x=>{const c=document.createElement("th");c.textContent=x;h.appendChild(c);});
  pl.placements.forEach((p,pi)=>p.rows.forEach((row,ri)=>{const tr=t.insertRow();tr.dataset.p=pi;
    tr.insertCell().textContent=`Canister ${p.canister} / ${p.label} (${p.kat})`;tr.insertCell().textContent=row;
    const sel=document.createElement("select");p.free_colors.forEach(c=>sel.add(new Option(c,c)));sel.value=p.colors[ri];tr.insertCell().appendChild(sel);
    const inp=document.createElement("input");inp.size=22;tr.insertCell().appendChild(inp);}));
  const ins=[...t.querySelectorAll("input")];  /* ilk HÜCRE metni, elle değiştirilmemiş diğer satırlara kopyalanır */
  ins.forEach((i,k)=>i.oninput=()=>{if(k>0)i.dataset.touched="1";else ins.slice(1).forEach(o=>{if(!o.dataset.touched)o.value=ins[0].value;});});}
$("rPreview").onclick=async()=>{rmsg("");const rows=[...$("rStraws").rows].slice(1);
  const straws=rows.map(tr=>({color:tr.querySelector("select").value,hucre:tr.querySelector("input").value}));
  const r=await api("/api/reg/preview",{plan_id:R.plan.id,straw_type:$("rType").value,straws,
    patient:{soyad:$("pSoyad").value,ad:$("pAd").value,esi:$("pEsi").value,tarih:$("pDate").value}});
  if(!r.ok){$("rStep3").hidden=true;alert(r.message);return;}R.regId=r.id;const t=$("rChanges");t.textContent="";
  const h=t.insertRow();["Hücre","Eski","Yeni"].forEach(x=>{const c=document.createElement("th");c.textContent=x;h.appendChild(c);});
  r.changes.forEach(c=>{const tr=t.insertRow();tr.insertCell().textContent=c.where;tr.insertCell().textContent=c.old||"(boş)";tr.insertCell().textContent=c.new;});
  $("rStep3").hidden=false;};
$("rApply").onclick=async()=>{$("rApply").disabled=true;const r=await api("/api/reg/apply",{id:R.regId});$("rApply").disabled=false;
  rmsg(r.message,r.ok?"ok":"bad");if(r.ok){R.regId=null;await state();$("rPlans").textContent="";$("rStep2").hidden=true;
    $("pSoyad").value=$("pAd").value=$("pEsi").value="";}logs();};
$("rCancel").onclick=()=>{R.regId=null;$("rStep3").hidden=true;rmsg("Vazgeçildi.");};
(async()=>{await state();await loadSheet();logs();})();
</script></body></html>"""
