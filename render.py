"""Geração do painel do Radar Futsal (cloud) — timeline + tabelas Por fonte + pesquisa/filtros.
Importado por scan.py. Recebe os itens já filtrados e o por_fonte agrupado."""
from datetime import timezone, timedelta, datetime

LX = timezone(timedelta(hours=1))  # Lisboa (verão)
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# prio -> (cor, etiqueta curta) para colorir o cartão e o cabeçalho por nível
NIVEL_INFO = {
    7: ("#16a34a", "🟢 Liga Placard"),
    6: ("#d946ef", "🚺 Liga Feminina"),
    5: ("#3b82f6", "🔵 2ª Divisão"),
    4: ("#ef4444", "📰 Imprensa"),
    3: ("#a855f7", "🌍 Internacional"),
    1: ("#f26430", "🇵🇹 Portugal"),
    0: ("#6b7280", "🌍 Mundo"),
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def rel(w, now):
    """Tempo relativo curto e legível."""
    s = (now - w).total_seconds()
    if s < 0:
        s = 0
    if s < 90:
        return "agora"
    if s < 3600:
        return f"há {int(s // 60)}m"
    if s < 86400:
        return f"há {int(s // 3600)}h"
    d = int(s // 86400)
    return "ontem" if d == 1 else f"há {d}d"


def render(itens, por_fonte, data, ok, nfeeds):
    now = datetime.now(LX)

    # ---- contadores por filtro (mostrados nos chips) ----
    def conta(tok):
        if tok == "all":
            return len(itens)
        return sum(1 for it in itens if tok in it.get("ftag", "").split(","))
    C = {t: conta(t) for t in ["all", "primeira", "placard", "feminina", "segunda",
                               "pt", "es", "br", "mundo", "jornais", "social"]}

    # ---- timeline (Novo, PT primeiro) ----
    tl = []
    for it in itens:
        w = it["when"].astimezone(LX)
        p = it.get("prio", 0)
        df = it.get("ftag", "mundo")
        toks = df.split(",")
        if p == 2:
            cor = "#f59e0b" if "es" in toks else "#10b981"
            lbl = "🇪🇸 Espanha" if "es" in toks else "🇧🇷 Brasil"
        else:
            cor, lbl = NIVEL_INFO.get(p, ("#6b7280", "🌍 Mundo"))
        prim = "primeira" in toks
        selo = '<span class="selo prim">🎯 1ª mão</span>' if prim else '<span class="selo imp">📰 imprensa</span>'
        ts = int(it["when"].timestamp())
        tl.append(f'''    <article class="card" data-f="{df}" data-ts="{ts}" style="--c:{cor}">
      <div class="k"><span class="src">{esc(it["source"])}</span>{selo}<span class="lvl">{lbl}</span></div>
      <h3><a href="{esc(it["link"])}" target="_blank" rel="noopener">{esc(it["title"])}</a></h3>
      <div class="meta"><span class="ago">{rel(w, now)}</span><span class="dt">{w:%d/%m · %H:%M}</span></div>
    </article>''')
    timeline = "\n".join(tl) if tl else '<div class="empty">Sem novidades nas últimas 2 semanas.</div>'

    # ---- secção por nível (espelha os filtros) ----
    NIVEIS = [
        ("primeira", "primeira", "Primeira mão", "🎯 Fonte oficial", "#0f9d58"),
        ("placard", "pt,placard", "Liga Placard", "🟢 M", "#16a34a"),
        ("feminina", "pt,feminina", "Liga Feminina", "🚺", "#d946ef"),
        ("segunda", "pt,segunda", "2ª Divisão", "🔵 Nacional", "#3b82f6"),
        ("jornais", "pt,jornais", "Imprensa", "📰 Jornais", "#ef4444"),
        ("es", "es", "Espanha", "🇪🇸 Fútbol sala", "#f59e0b"),
        ("br", "br", "Brasil", "🇧🇷 LNF", "#10b981"),
        ("mundo", "mundo", "Internacional", "🌍 UEFA/Mundo", "#a855f7"),
        ("social", "social", "X / Redes", "🐦 Tweets", "#1da1f2"),
    ]
    src_cards = []
    for token, df, nome, tag, cor in NIVEIS:
        itens_c = [it for it in itens if token in it.get("ftag", "").split(",")]
        itens_c = sorted(itens_c, key=lambda x: x["when"], reverse=True)[:6]
        if not itens_c:
            continue
        lis = "\n".join(
            f'      <li><a href="{esc(i["link"])}" target="_blank" rel="noopener">'
            f'{esc(i["title"][:95])}</a> <span class="t">{rel(i["when"].astimezone(LX), now)}</span></li>'
            for i in itens_c)
        src_cards.append(
            f'''  <div class="src" data-f="{df}">
    <div class="src-head"><span class="dot" style="background:{cor}"></span>
      <span class="name">{esc(nome)}</span><span class="tag">{tag}</span></div>
    <ul>
{lis}
    </ul>
  </div>''')
    fontes_html = "\n".join(src_cards)

    def chip(f, label, count=True):
        n = f' <span class="cnt">{C.get(f, 0)}</span>' if count and f in C else ''
        act = ' active' if f == 'all' else ''
        return f'<button class="chip{act}" data-f="{f}">{label}{n}</button>'

    chips = "\n ".join([
        chip("all", "Tudo"),
        chip("primeira", "🎯 Primeira mão"),
        chip("jornais", "📰 Jornais"),
        chip("placard", "🟢 Placard"),
        chip("feminina", "🚺 Feminina"),
        chip("segunda", "🔵 2ª Div"),
        chip("pt", "🇵🇹 PT"),
        chip("es", "🇪🇸 ES"),
        chip("br", "🇧🇷 BR"),
        chip("mundo", "🌍 Intl"),
        chip("social", "𝕏 Redes"),
    ])

    return f'''<!DOCTYPE html>
<html lang="pt"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radar Futsal — atualiza sozinho</title>
<style>
 :root{{--bg:#07080b;--panel:#111318;--panel2:#151922;--ink:#eef1f6;--muted:#8b93a4;
  --line:#20242e;--acc:#f26430;--gold:#f5b942;--chip:#161a22}}
 *{{box-sizing:border-box}}
 body{{margin:0;background:
   radial-gradient(1100px 380px at 78% -8%,rgba(242,100,48,.10),transparent 60%),
   radial-gradient(760px 300px at 8% -4%,rgba(245,185,66,.07),transparent 60%),var(--bg);
  color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;line-height:1.5}}
 a{{color:inherit}}
 .wrap{{max-width:1120px;margin:0 auto;padding:0 18px 72px}}
 /* topo fixo: marca + pesquisa + filtros sempre à mão */
 .top{{position:sticky;top:0;z-index:50;background:rgba(7,8,11,.86);backdrop-filter:blur(12px);
  border-bottom:1px solid var(--line);margin:0 -18px;padding:12px 18px 10px}}
 .bar{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
 .brand{{display:flex;align-items:center;gap:9px;font-weight:800;font-size:19px;letter-spacing:-.01em}}
 .brand .ball{{font-size:20px}}
 .brand b{{background:linear-gradient(92deg,var(--gold),var(--acc));-webkit-background-clip:text;background-clip:text;color:transparent}}
 .live{{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;color:var(--muted);
  border:1px solid var(--line);border-radius:20px;padding:3px 10px}}
 .live .pulse{{width:7px;height:7px;border-radius:50%;background:#2ecc71;box-shadow:0 0 0 0 rgba(46,204,113,.7);animation:p 2s infinite}}
 @keyframes p{{0%{{box-shadow:0 0 0 0 rgba(46,204,113,.6)}}70%{{box-shadow:0 0 0 7px rgba(46,204,113,0)}}100%{{box-shadow:0 0 0 0 rgba(46,204,113,0)}}}}
 .stamp{{margin-left:auto;color:var(--muted);font-size:12px;text-align:right}} .stamp b{{color:var(--ink)}}
 .search{{flex:1 1 240px;padding:10px 14px;border-radius:11px;border:1px solid var(--line);
  background:var(--panel);color:var(--ink);font-size:14px;outline:none}}
 .search:focus{{border-color:var(--acc)}}
 .refresh{{padding:9px 14px;border-radius:11px;border:1px solid var(--acc);background:transparent;
  color:var(--acc);font-weight:700;font-size:13px;cursor:pointer;white-space:nowrap}}
 .refresh:active{{transform:scale(.96)}}
 .chips{{display:flex;gap:8px;margin-top:10px;overflow-x:auto;padding-bottom:2px;-webkit-overflow-scrolling:touch;scrollbar-width:none}}
 .chips::-webkit-scrollbar{{display:none}}
 .chip{{display:inline-flex;align-items:center;gap:7px;padding:7px 13px;border-radius:22px;border:1px solid var(--line);
  background:var(--panel);color:var(--muted);font-size:12.5px;cursor:pointer;white-space:nowrap;transition:.12s}}
 .chip:hover{{border-color:#39404e;color:var(--ink)}}
 .chip.active{{background:linear-gradient(92deg,var(--acc),#e0562a);border-color:var(--acc);color:#fff;font-weight:700}}
 .chip .cnt{{font-size:11px;background:rgba(255,255,255,.09);color:inherit;border-radius:20px;padding:1px 7px;min-width:20px;text-align:center}}
 .chip.active .cnt{{background:rgba(0,0,0,.22)}}
 .barinfo{{display:flex;align-items:center;gap:8px;margin:20px 0 12px}}
 .barinfo .sec{{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:700}}
 .barinfo .shown{{margin-left:auto;font-size:12px;color:var(--muted)}} .barinfo .shown b{{color:var(--gold)}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:13px}}
 .card{{position:relative;background:linear-gradient(180deg,var(--panel2),var(--panel));
  border:1px solid var(--line);border-left:3px solid var(--c,#6b7280);border-radius:13px;padding:14px 15px;transition:.14s}}
 .card:hover{{border-color:#39404e;transform:translateY(-2px);box-shadow:0 10px 26px rgba(0,0,0,.35)}}
 .k{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:11px;margin-bottom:7px}}
 .k .src{{font-weight:800;letter-spacing:.02em;color:var(--ink);text-transform:none}}
 .k .lvl{{color:var(--muted)}}
 .selo{{font-size:10px;font-weight:700;padding:2px 7px;border-radius:20px;white-space:nowrap}}
 .selo.prim{{color:#7ff0b6;background:rgba(15,157,88,.16);border:1px solid rgba(15,157,88,.35)}}
 .selo.imp{{color:#ffb3ad;background:rgba(239,68,68,.13);border:1px solid rgba(239,68,68,.3)}}
 .card h3{{font-size:14.5px;line-height:1.35;margin:0 0 9px}}
 .card h3 a{{color:var(--ink);text-decoration:none}} .card h3 a:hover{{color:var(--gold)}}
 .meta{{display:flex;align-items:center;gap:8px;font-size:11.5px;color:var(--muted)}}
 .meta .ago{{color:var(--gold);font-weight:700}} .meta .dt{{margin-left:auto}}
 .empty{{color:var(--muted);padding:30px;text-align:center;border:1px dashed var(--line);border-radius:13px}}
 .sources{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:15px}}
 .src{{background:var(--panel);border:1px solid var(--line);border-radius:13px;overflow:hidden}}
 .src-head{{padding:12px 15px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px}}
 .dot{{width:9px;height:9px;border-radius:50%}} .src-head .name{{font-weight:700;font-size:14px}}
 .src-head .tag{{margin-left:auto;font-size:11px;color:var(--muted);background:var(--chip);padding:3px 9px;border-radius:20px}}
 .src ul{{list-style:none;margin:0;padding:6px 0}} .src li{{padding:8px 15px;font-size:13px;border-bottom:1px solid var(--line)}}
 .src li:last-child{{border-bottom:0}} .src li a{{color:var(--ink);text-decoration:none}} .src li a:hover{{color:var(--gold)}}
 .src li .t{{font-size:10.5px;color:var(--muted);white-space:nowrap}}
 .hidden{{display:none!important}}
 footer{{margin-top:36px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}}
 #gate{{position:fixed;inset:0;background:var(--bg);z-index:9999;display:flex;align-items:center;justify-content:center}}
 #gate.hidden{{display:none}}
 #gate .box{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:32px 26px;max-width:340px;width:90%;text-align:center}}
 #gate .box h2{{margin:12px 0 4px;font-size:19px}}
 #gate .box h2 b{{background:linear-gradient(92deg,var(--gold),var(--acc));-webkit-background-clip:text;background-clip:text;color:transparent}}
 #gate .box p{{color:var(--muted);font-size:13px;margin:0}}
 #gate input{{width:100%;padding:12px 14px;border-radius:11px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-size:15px;margin:16px 0 6px;outline:none}}
 #gate input:focus{{border-color:var(--acc)}}
 #gate button{{width:100%;padding:12px;border-radius:11px;border:0;background:linear-gradient(92deg,var(--acc),#e0562a);color:#fff;font-weight:700;font-size:15px;cursor:pointer}}
 #gate .err{{color:#ff6b6b;font-size:13px;min-height:17px;margin-top:6px}}
 body.locked{{overflow:hidden}}
 @media(max-width:560px){{.stamp{{display:none}} .brand{{font-size:17px}}}}
</style></head><body>
<div id="gate"><div class="box">
 <div style="font-size:36px">🏐🔒</div>
 <h2>Radar <b>Futsal</b></h2>
 <p>Painel privado da equipa.<br>Introduz a palavra-passe.</p>
 <input id="gpw" type="password" placeholder="Palavra-passe" autocomplete="current-password">
 <div class="err" id="gerr"></div>
 <button id="gbtn">Entrar</button>
</div></div>
<div class="wrap">
<div class="top">
 <div class="bar">
   <div class="brand"><span class="ball">🏐</span>Radar <b>Futsal</b></div>
   <span class="live"><span class="pulse"></span>ao vivo · sem PC ligado</span>
   <span class="stamp">Recolha <b>{data}</b> · {len(itens)} novidades · {ok}/{nfeeds} fontes</span>
 </div>
 <div class="bar" style="margin-top:10px">
   <input id="q" class="search" type="search" placeholder="🔍 Procurar clube, jogador, país…">
   <button id="refresh" class="refresh" title="Recarregar a recolha mais recente">↻ Atualizar</button>
 </div>
 <div class="chips" id="chips">
 {chips}
 </div>
</div>
<div class="barinfo">
 <span class="sec">🆕 Novo · últimas 2 semanas</span>
 <span class="shown" id="shown"></span>
</div>
<div class="grid" id="timeline">
{timeline}
</div>
<div class="barinfo" style="margin-top:30px"><span class="sec">Por competição / região</span></div>
<div class="sources" id="fontes">
{fontes_html}
</div>
<footer>Radar Futsal · gerado no GitHub Actions a partir de feeds oficiais. Omite o que já publicaste em zonatecnicafutsal.com / futsalportugal.com.</footer>
</div>
<script>
(function(){{
 var q=document.getElementById('q'), shown=document.getElementById('shown');
 var TL=document.getElementById('timeline');
 var ORD=Array.prototype.slice.call(TL.querySelectorAll('.card')); // ordem original (curada)
 function apply(){{
  var s=(q.value||'').toLowerCase().trim();
  var f=document.querySelector('.chip.active').dataset.f, vis=0, visiveis=[];
  document.querySelectorAll('#timeline .card').forEach(function(c){{
   var okF=(f==='all')||(c.dataset.f||'').split(',').indexOf(f)>=0;
   var okS=!s||c.textContent.toLowerCase().indexOf(s)>=0;
   var v=okF&&okS; c.classList.toggle('hidden', !v); if(v){{vis++;visiveis.push(c);}}
  }});
  // num filtro específico, mostra o MAIS RECENTE primeiro (por data); em "Tudo" mantém a ordem curada
  if(f!=='all'){{
   visiveis.sort(function(a,b){{return (b.dataset.ts||0)-(a.dataset.ts||0);}});
   visiveis.forEach(function(c){{TL.appendChild(c);}});
  }} else {{
   ORD.forEach(function(c){{TL.appendChild(c);}});
  }}
  document.querySelectorAll('#fontes .src').forEach(function(c){{
   var okF=(f==='all')||(c.dataset.f||'').split(',').indexOf(f)>=0;
   var okS=!s||c.textContent.toLowerCase().indexOf(s)>=0;
   c.classList.toggle('hidden', !(okF&&okS));
  }});
  if(shown) shown.innerHTML='A mostrar <b>'+vis+'</b>';
 }}
 q.addEventListener('input',apply);
 var refresh=document.getElementById('refresh');
 refresh.addEventListener('click',function(){{refresh.textContent='↻ A atualizar…';location.reload(true);}});
 document.querySelectorAll('.chip').forEach(function(ch){{
  ch.addEventListener('click',function(){{
   document.querySelectorAll('.chip').forEach(function(x){{x.classList.remove('active')}});
   ch.classList.add('active');apply();}});}});
 apply();  // arranca no chip activo (Tudo por defeito)
 setInterval(function(){{location.reload(true);}}, 5*60*1000);
}})();
</script>
<script>
(function(){{
 var HASH="db1603742b96054705364f15a915d14d04753aeb439a63b71a91315a5d8aee3a";
 var g=document.getElementById('gate'),pw=document.getElementById('gpw'),
     er=document.getElementById('gerr'),b=document.getElementById('gbtn');
 function unlock(){{g.classList.add('hidden');document.body.classList.remove('locked');}}
 if(localStorage.getItem('radar_ok')==='1'){{unlock();}}
 else{{document.body.classList.add('locked');setTimeout(function(){{pw.focus();}},50);}}
 async function sha(s){{
  var buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));
  return Array.from(new Uint8Array(buf)).map(function(x){{return x.toString(16).padStart(2,'0');}}).join('');
 }}
 async function tryit(){{
  var h=await sha(pw.value);
  if(h===HASH){{localStorage.setItem('radar_ok','1');unlock();}}
  else{{er.textContent='Palavra-passe errada';pw.value='';pw.focus();}}
 }}
 if(b){{b.addEventListener('click',tryit);
  pw.addEventListener('keydown',function(e){{if(e.key==='Enter')tryit();}});}}
}})();
</script>
</body></html>'''
