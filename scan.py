#!/usr/bin/env python3
"""Radar Futsal — motor CLOUD (corre no GitHub Actions, sem Mac).
Lê feeds RSS/Atom datados, filtra 48h, deduplica, escreve index.html autónomo.
Sem dependências externas (só stdlib). Estado de dedup persiste em seen.json (commitado)."""
import email.utils, html as html_mod, json, os, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
import render as R
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
JANELA_H = 72
MAX_ITENS = 55

FUTSAL_RE = re.compile(r"futsal|f[úu]tbol sala|calcio a 5|liga placard|futsalista", re.I)
TEMA_RE = re.compile(
    r"futsal|f[úu]tbol sala|calcio a 5|liga placard|benfica|sporting|braga|bar[çc]a|barcelona|"
    r"elpozo|palma|jimbee|movistar|cartagena|valdepe|pe[ñn][íi]scola|santa coloma|xota|osasuna magna|"
    r"magnus|pato futsal|corinthians|joinville|cascavel|carlos barbosa|kairat|lnfs?\b|uefa|champions|"
    r"sele[çc][ãa]o|fifa|fund[ãa]o|el[ée]ctrico|famalic[ãa]o|z[êe]zere|porto salvo|portimonense|"
    r"rio ave|torreense|upvn|nun.?[áa]lvares|liga feminina", re.I)

FEEDS = [
    ("Palma Futsal", "https://www.palmafutsal.com/feed/", None),
    ("ElPozo Murcia", "https://www.elpozomurcia.com/feed/", None),
    ("Movistar Inter", "https://www.interfutbolsala.com/feed/", None),
    ("Jimbee Cartagena", "https://jimbeecartagena.es/feed/", None),
    ("Valdepeñas", "https://www.fsvaldepenas.com/feed/", None),
    ("Osasuna Magna", "https://xota.es/feed/", None),
    ("Peñíscola", "https://peniscolafs.com/feed/", None),
    ("Santa Coloma", "https://fsgarcia.cat/feed/", None),
    ("CROfutsal", "https://www.crofutsal.com/feed/", None),
    ("Futsal Dinamo", "https://futsal-dinamo.hr/feed/", None),
    ("Magnus", "https://magnusfutsal.com.br/feed/", None),
    ("Pato Futsal", "https://patofutsal.com.br/feed/", None),
    ("LNF Brasil", "https://lnfoficial.com.br/noticias/feed/", None),
    ("Itália C5", "https://www.divisionecalcioa5.it/feed/", None),
    ("Meta Catania", "https://metacatania.it/feed/", None),
    ("Famalicão", "https://www.fcfamalicao.pt/feed/", "FUTSAL"),
    ("zerozero", "https://www.zerozero.pt/rss/noticias.php", "FUTSAL"),
    ("Record", "https://www.record.pt/rss", "FUTSAL"),
    ("Imprensa", "https://news.google.com/rss/search?q=futsal%20%28site%3Arecord.pt%20OR%20site%3Aojogo.pt%20OR%20site%3Amaisfutebol.iol.pt%20OR%20site%3Aabola.pt%20OR%20site%3Atvi24.iol.pt%20OR%20site%3Asapo.pt%20OR%20site%3Artp.pt%20OR%20site%3Adn.pt%20OR%20site%3Ajn.pt%29&hl=pt-PT&gl=PT&ceid=PT:pt", None),
    # Google News p/ encher níveis (o melhor do futsal, mesmo com IG calado):
    ("Futsal Feminino", "https://news.google.com/rss/search?q=futsal%20feminino%20%28Portugal%20OR%20Benfica%20OR%20Sporting%20OR%20%22liga%20feminina%22%29&hl=pt-PT&gl=PT&ceid=PT:pt", None),
    ("Fútbol Sala", "https://news.google.com/rss/search?q=%22f%C3%BAtbol%20sala%22%20OR%20futsal%20%28Espa%C3%B1a%20OR%20Primera%20OR%20LNFS%20OR%20Palma%20OR%20ElPozo%20OR%20Movistar%20OR%20%22Bar%C3%A7a%22%20OR%20Jimbee%20OR%20Osasuna%20OR%20Valdepe%C3%B1as%20OR%20%22Ja%C3%A9n%22%20OR%20Cartagena%20OR%20Pe%C3%B1%C3%ADscola%29&hl=es&gl=ES&ceid=ES:es", None),
    ("Futsal Brasil", "https://news.google.com/rss/search?q=futsal%20%28Brasil%20OR%20LNF%20OR%20%22Liga%20Nacional%22%20OR%20Magnus%20OR%20Pato%20OR%20Corinthians%20OR%20%22Atl%C3%A2ntico%22%20OR%20%22Carlos%20Barbosa%22%20OR%20%22Jaragu%C3%A1%22%20OR%20Joinville%20OR%20Cascavel%20OR%20%22sele%C3%A7%C3%A3o%20brasileira%22%29&hl=pt-BR&gl=BR&ceid=BR:pt", None),
    ("Futsal Portugal", "https://news.google.com/rss/search?q=futsal%20Portugal&hl=pt-PT&gl=PT&ceid=PT:pt", None),
    ("Português no Estrangeiro", "https://news.google.com/rss/search?q=futsal%20%28portugu%C3%AAs%20OR%20portuguesa%20OR%20luso%29%20%28Espanha%20OR%20It%C3%A1lia%20OR%20Fran%C3%A7a%20OR%20Kuwait%20OR%20Jap%C3%A3o%20OR%20Ar%C3%A1bia%20OR%20estrangeiro%20OR%20internacional%29&hl=pt-PT&gl=PT&ceid=PT:pt", None),
    ("Seleção Portugal", "https://news.google.com/rss/search?q=futsal%20sele%C3%A7%C3%A3o%20%28Portugal%20OR%20portuguesa%20OR%20%22Jorge%20Braz%22%20OR%20sub-19%20OR%20sub-21%29&hl=pt-PT&gl=PT&ceid=PT:pt", None),
    ("Calcio a 5", "https://news.google.com/rss/search?q=%22calcio%20a%205%22%20OR%20futsal%20%28Italia%20OR%20%22Serie%20A%22%20OR%20Napoli%20OR%20Feldi%20OR%20%22divisione%20calcio%22%29&hl=it&gl=IT&ceid=IT:it", None),
    ("Futsal França", "https://news.google.com/rss/search?q=futsal%20%28France%20OR%20%22D1%20Futsal%22%20OR%20championnat%20OR%20Nantes%20OR%20%22coupe%20de%20France%20futsal%22%20OR%20ACCS%29&hl=fr&gl=FR&ceid=FR:fr", None),
    ("Futsal Croácia", "https://news.google.com/rss/search?q=%28futsal%20OR%20%22mali%20nogomet%22%29%20%28Hrvatska%20OR%20%22Futsal%20Dinamo%22%20OR%20%22Novo%20Vrijeme%22%20OR%20reprezentacija%20OR%20Osijek%29&hl=hr&gl=HR&ceid=HR:hr", None),
    ("Futsal Ásia", "https://news.google.com/rss/search?q=futsal%20%28Japan%20OR%20Iran%20OR%20%22AFC%20Futsal%22%20OR%20%22F.League%22%20OR%20%22Asian%20Cup%22%20OR%20Thailand%20OR%20Vietnam%29&hl=en&gl=US&ceid=US:en", None),
    ("CONMEBOL", "https://www.conmebol.com/feed/", "FUTSAL"),
    ("Google Alerts", "https://www.google.com/alerts/feeds/07340303412689524551/4521077332057732674", "TEMA"),
    ("Alerts Futsal", "https://www.google.com/alerts/feeds/07340303412689524551/6715931025412471738", "TEMA"),
    ("X · Palma", "https://nitter.net/PalmaFutsal/rss", None),
    ("X · Magnus", "https://nitter.net/MagnusFutsal/rss", None),
    ("X · Jimbee", "https://nitter.net/JimbeeCartagena/rss", None),
    ("X · Barça FS", "https://nitter.net/FCBfutbolsala/rss", None),
    ("X · LNFS", "https://nitter.net/LNFS/rss", None),
    ("X · UEFA Futsal", "https://nitter.net/UEFAFutsal/rss", None),
    ("X · RFEF", "https://nitter.net/RFEF/rss", "FUTSAL"),
    ("X · ElPozo", "https://nitter.net/ElPozoMurcia_FS/rss", None),
    ("X · Pato", "https://nitter.net/patofutsal/rss", None),
    ("X · Alzira FS", "https://nitter.net/AlziraFS/rss", None),
    ("X · Fahey", "https://nitter.net/jamiefahey1/rss", "FUTSAL"),
    ("X · KSA Futsal", "https://nitter.net/futsal_KSA2030/rss", None),
    ("X · Munhana", "https://nitter.net/gustavomunana/rss", None),
    ("X · Candelas", "https://nitter.net/CandelasJr/rss", None),
    ("X · RFEF Futsal", "https://nitter.net/FutSalRFEF/rss", None),
    ("X · Efesé Cartagena", "https://nitter.net/EfeseForo/rss", None),
    ("X · F.League Japão", "https://nitter.net/futsal1958/rss", None),
    ("X · Copa América", "https://nitter.net/CopaAmerica/rss", "FUTSAL"),
    ("X · Futsal Planet", "https://nitter.net/futsalplanet97/rss", None),
    ("X · zerozero Futsal", "https://nitter.net/futsalzerozero/rss", None),
    ("X · Futsal Fichajes", "https://nitter.net/FutsalFichajes3/rss", None),
    ("X · AMFutsal", "https://nitter.net/AMFutsal/rss", "FUTSAL"),
    ("X · Futsal Talk", "https://nitter.net/futsal_talk/rss", "FUTSAL"),
    ("X · Futsal França FR", "https://nitter.net/FutsalFrance/rss", "FUTSAL"),
    ("X · Actufutsal", "https://nitter.net/Actufutsal/rss", "FUTSAL"),
    ("X · Futsal Polónia", "https://nitter.net/FutsalPolska/rss", "FUTSAL"),
    ("X · Futsal Legends", "https://nitter.net/Futsal_Legends/rss", "FUTSAL"),
    ("OFC Oceânia", "https://www.oceaniafootball.com/feed/", "FUTSAL"),
]

RUIDO = re.compile(
    r"zapatill|sapatilh|decathlon|\bnike\b|\bjoma\b|ripley|balon\b|bolas?\b|tienda|loja|"
    r"sala de espera|sala de consumo|sala de imprensa|sala de aula|"
    # futsal amador/municipal/base (BR/US) — o Carlos não publica isto:
    r"campeonato municipal|municipal de futsal|interinstitucional|copa .{0,18} de futsal|"
    r"de base\b|futsal de base|categorias de base|entrada gratuita|rel[âa]mpago|"
    r"unitedfutsal|united futsal|world futsal champ|liga usuluteca|santafesina|"
    r"bauru cup|araucária|arapiraca|traipu|citadino|distrital amador|"
    r"ver[ãa]o|f[ée]rias|escolar\b|amistoso beneficente|torneio solid[áa]rio|"
    # outros desportos das contas multi-modalidades (Braga/Benfica/Sporting…): não é futsal
    r"voleibol|volleyball|#volei|andebol|handball|h[óo]quei|hockey|basquet|basketball|"
    r"nata[çc][ãa]o|atletismo|r[aâ]guebi|\brugby\b|ciclismo|t[ée]nis de mesa|ginm[áa]stica|"
    r"gin[áa]stica|patinagem|triatlo|\bp[óo]lo aqu[áa]tico|badminton|karat[ée]|jud[oó]",
    re.I)

# prioridade editorial do Carlos (PT + PT no estrangeiro + Placard + relevante)
PRIO_PT = re.compile(
    r"benfica|sporting|braga|porto|fc porto|leões porto salvo|el[ée]ctrico|torreense|fund[ãa]o|"
    r"famalic[ãa]o|z[êe]zere|portimonense|rio ave|upvn|nun.?[áa]lvares|liga placard|liga feminina|"
    r"sele[çc][ãa]o portuguesa|portugu[êe]s|portuguesa|treinador portugu|fpf|\bportugal\b|"
    r"barcelona|bar[çc]a|palma|elpozo|movistar|jimbee|rfef|lnfs|uefa futsal|champions|"
    r"ricardinho|bruno coelho|jo[ãa]o matos|higor|f[úu]tbol sala", re.I)

# LIGA PLACARD — prioridade máxima. Nomes dos 12 clubes 26/27 + as contas de IG deles.
# Casa com o título OU a fonte (apanha posts dos clubes mesmo sem o nome na legenda).
PLACARD = re.compile(
    r"liga placard|ligaplacard|"
    r"\bsporting\b|benfica|sp\.? ?braga|sc ?braga|\bbraga\b|le[õo]es (de )?porto salvo|porto salvo|"
    r"el[ée]ctrico|torreense|fund[ãa]o|famalic[ãa]o|z[êe]zere|portimonense|rio ave|\bupvn\b|"
    r"sportingmodalidades|modalidadesslb|scbragamodalidades|leoesportosalvo|electricofc_oficial|"
    r"scutorreensemodalidades|adfundao|fcfamalicaomodalidades|scfz_futsal|portimonense_futsal|"
    r"maisrioave|oficial_upvn", re.I)

# Liga Feminina Placard (2º nível) — texto + contas dos clubes femininos (zerozero 25/26 + subidas)
# NÃO inclui contas partilhadas (Benfica/Leões P.Salvo/Nun'Álvares/Sporting): essas só pelo texto,
# senão marcava os jogos masculinos delas como femininos.
FEMININA = re.compile(
    r"liga feminina|feminin[oa]s?|femenin[oa]s?|\bwomen'?s?\b|futebol feminino|"
    r"futsalfemininonews|forum\.futsal\.feminino|womensfutsalworld|5womens\.sports|sefutbolfem|"
    r"atleticocp|santa_luzia_futebolclube|futsalfeijo|gdarvore1975|novasementefutsal|"
    r"fcaguiassantamarta|u\.a\.povoense|maiafutsal|futsal feij[óo]|novasemente|"
    r"gcrnunalvaresfutsal|nun.?[áa]lvares",   # finalistas Liga Feminina 25/26 — nome forte
    re.I)

# 2ª Divisão Nacional (3º nível) — texto + contas IG dos clubes (II Div 25/26, via zerozero;
# NÃO inclui Portimonense/UPVN/Leões P.Salvo, que subiram à Placard em 26/27)
SEGUNDA = re.compile(
    r"2[.ªaº]? ?divis[ãa]o|segunda divis[ãa]o|ii divis[ãa]o|ii nacional|2ª nacional|"
    r"subida à ii|acesso à ii|"
    r"_boavistafcfutsal_|scbarbarense|acdladoeiro_futsal|arbbesperanca|burinhosafutsal|"
    r"albufeirafutsalclube69|reguilastires|osbelenenses|futsal_arsenalclubemaia|"
    r"valpacosfutsalclube|amigos_de_cerva|viseu2001|"
    r"desportivojorgeantunes|modicus\.sandim|csmaritimomodalidades|cssaojoao|dinamo\.sanjoanense|"
    # 26/27: desceram da Liga Placard -> II Divisão
    r"caxinas|adcrcaxinas|quinta dos lombos|lombos_futsal|"
    # 26/27: subiram da III Divisão -> II Divisão
    r"sassoeiros|cf_sassoeiros|pa[çc]os de ferreira|fcpf_futsal|amarense|aramarense|"
    r"lusit[âa]nio|louros[ao]|lourosafutsal",
    re.I)

# Espanha (4º nível)
ESPANHA = re.compile(
    r"\bpalma\b|elpozo|el pozo|movistar|inter fs|jimbee|cartagena|valdepe|osasuna|\bxota\b|"
    r"pe[ñn][íi]scola|santa coloma|ja[ée]n|ribera navarra|ciudad del vino|\brfef\b|lnfs|"
    r"f[úu]tbol sala|palmafutsaloficial|intermovistar|jimbeecartagena|jaenfutbolsala|c\.d\.xota|"
    r"riberanavarrafs|fsciudaddelvino|futsalrfef|fcbfutsal", re.I)

# Brasil (clubes)
BRASIL = re.compile(
    r"magnus|pato futsal|atl[âa]ntico|carlos barbosa|\bacbf\b|jaragu[áa]|marreco|krona|"
    r"joinville|corinthians|cascavel|foz.?cataratas|magnusfutsal|patofutsaloficial|"
    r"atlanticofutsal|acbffutsal|jaraguafutsal|marrecofutsaloficial|jec\.krona|fozcataratas_futsal|"
    r"futsal brasil|\bbrasil\b|\blnf\b|lnfoficial|liga nacional de futsal",
    re.I)

# Filtro de clubes ESTRANGEIROS (não afogar o painel). Um post cuja FONTE é um clube
# de fora só passa se: for clube da Liga dos Campeões, OU envolver um português no
# estrangeiro, OU (Brasil) for LNF/seleção/saída p/ estrangeiro. Filtra pela FONTE
# (não pelo título) p/ NÃO cortar notícias PT que mencionem clubes de fora.
ESTRANGEIRO_FONTE = re.compile(
    r"palma|elpozo|movistar|intermovistar|jimbee|cartagena|valdepe|osasuna|\bxota\b|"
    r"pe[ñn][íi]scola|santa coloma|ja[ée]n|ribera navarra|ciudad del vino|fcbfutsal|"
    r"magnus|pato|atl[âa]ntico|acbf|carlos barbosa|jaragu|marreco|krona|joinville|"
    r"corinthians|cascavel|foz.?cataratas|napoli|kairat|kprf|futsal dinamo|piast|differdange|"
    r"shinagawa|semey|ekstraklasa|fsciudaddelvino|riberanavarrafs", re.I)
# clubes tipicamente na UEFA Futsal Champions League (mantêm-se sempre)
CHAMPIONS = re.compile(
    r"bar[çc]a|fcbfutsal|palma|jimbee|elpozo|movistar|inter fs|napoli|kairat|"
    r"anderlecht|sporting|benfica|liga dos campe|champions", re.I)
# clubes estrangeiros COM portugueses — passam sempre (extensível: juntar aqui)
PT_CLUBES_FORA = re.compile(
    r"piast|gliwice|differdange|shinagawa|semey|kprf|"
    r"fcdifferdange03_futsal|shinagawacity_futsalclub|fcsemey|piastgliwicefutsal|sportclubkprf",
    re.I)
# português no estrangeiro (o ângulo forte do Carlos)
PT_ESTRANGEIRO = re.compile(
    r"portugu[êe]s|portuguesa|\bluso\b|treinador portugu|internacional portugu|"
    r"ricardinho|pany|bruno coelho|jo[ãa]o matos|afonso jesus|tiago brito|erick mendon", re.I)
# Brasil: manter se LNF/seleção/saída p/ estrangeiro
BR_MANTER = re.compile(
    r"\blnf\b|sele[çc][ãa]o|canarinh|verde.?amarel|"
    r"deixa|de sa[íi]da|despede|adeus|rumo a|vai para|nova casa|se marcha|farewell|"
    r"de partida|assina pel|\beuropa\b|portugal|espanha|it[áa]lia|kuwait|jap[ãa]o|emirados",
    re.I)


def estrangeiro_corta(it):
    """DESLIGADO (pedido do Carlos: "todas as opções a dar e com notícias").
    Todos os clubes passam a aparecer no seu nível; o limite de 1 post/conta +
    teto global de IG evita a inundação. As regexes CHAMPIONS/PT_CLUBES_FORA/
    ESPANHA/BRASIL continuam a ser usadas para classificar por nível."""
    return False

# Imprensa principal + sites de futsal PT (a seguir às competições)
IMPRENSA = re.compile(
    r"\brecord\b|a bola|\babola\b|\bo jogo\b|\bojogo\b|maisfutebol|mais futebol|zerozero|"
    r"sapo desporto|rtp|futsalportugal|zona ?t[ée]cnica|zonatecnica|foco no futsal|"
    r"foconofutsal|futsal ?planet|futsalplanet1997|record_portugal|zerozeropt|"
    r"gustavomunana|munhana|gustavo munana|\bcandelas\b|fichajes|\bimprensa\b", re.I)

# Institucional internacional (ligas/federações/confederações)
INSTITUCIONAL = re.compile(
    r"\brfef\b|rfef_futsal|futsalrfef|"
    r"calcio a ?5|divisionecalcio|serie a[^.]{0,12}futsal|"
    r"uefa ?futsal|uefafutsal|futsal champions|uefafutsalchampionsleague|"
    r"fifa futsal|futsal world cup|mundial de futsal|"
    r"futsal fran[çc]a|futsal cro[áa]cia|futsal [áa]sia|f\.league|f\.?league jap|copa am[ée]rica", re.I)


def fetch(url):
    h = dict(UA)
    if "news.google.com" in url:  # Google News (UE) exige cookie de consentimento
        h["Cookie"] = "CONSENT=YES+cb.20210328-17-p0.en+FX+"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.read()
    except Exception:
        return None


def unwrap_google(link):
    if "google.com/url" in link:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        for k in ("url", "q"):
            if k in qs:
                return qs[k][0]
    return link


def limpa(t):
    t = re.sub(r"^\s*<!\[CDATA\[\s*", "", t)
    t = re.sub(r"^RT by @\w+:\s*", "", t)
    t = re.sub(r"\s*\]\]>\s*$", "", t)
    return re.sub(r"\s+", " ", html_mod.unescape(html_mod.unescape(t))).strip()


def parse_feed(name, raw):
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.iter("item"):
        t = limpa(it.findtext("title") or "")
        l = (it.findtext("link") or "").strip()
        d = it.findtext("pubDate")
        w = None
        if d:
            try:
                w = email.utils.parsedate_to_datetime(d)
            except Exception:
                pass
        if t and l:
            out.append({"title": t, "link": l, "when": w, "source": name})
    for e in root.findall("a:entry", ns):
        t = limpa(re.sub(r"<[^>]+>", "", e.findtext("a:title", "", ns)))
        le = e.find("a:link", ns)
        l = unwrap_google(le.get("href", "")) if le is not None else ""
        d = e.findtext("a:published", "", ns) or e.findtext("a:updated", "", ns)
        w = None
        if d:
            try:
                w = datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                pass
        if t and l:
            out.append({"title": t, "link": l, "when": w, "source": name})
    return out


def key_of(it):
    dom = urllib.parse.urlparse(it["link"]).netloc.replace("www.", "")
    slug = re.sub(r"[^a-z0-9]+", "-", it["title"].lower())[:60].strip("-")
    return f"{dom} {slug}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def texto_proprio():
    txt = []
    for u in ("https://www.zonatecnicafutsal.com", "https://www.futsalportugal.com"):
        raw = fetch(u)
        if raw:
            txt.append(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "ignore")).lower())
    return " ".join(txt)


NOME_RE = re.compile(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+)+")



# ---- Instagram via Apify (opcional; ativa-se com APIFY_TOKEN nos GitHub Secrets) ----
def _load_ig_handles():
    p = os.path.join(ROOT, "ig_handles.txt")
    try:
        linhas = open(p, encoding="utf-8").read().splitlines()
    except Exception:
        return ["ligaplacard", "foconofutsal", "magnusfutsal", "futsalrfef"]
    hs, vistos = [], set()
    for ln in linhas:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln not in vistos:
            vistos.add(ln); hs.append(ln)
    return hs

IG_HANDLES = _load_ig_handles()

IG_CACHE = os.path.join(ROOT, "ig_cache.json")

def _ig_load_cache():
    """Posts de IG da última varredura (persistem entre recolhas sem custo)."""
    try:
        raw = json.load(open(IG_CACHE, encoding="utf-8"))
    except Exception:
        return []
    out = []
    for it in raw:
        try:
            it["when"] = datetime.fromisoformat(it["when"])
            out.append(it)
        except Exception:
            pass
    return out

def _ig_save_cache(items):
    try:
        json.dump([{**it, "when": it["when"].isoformat()} for it in items],
                  open(IG_CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass

def instagram_apify():
    """Puxa os últimos posts das contas via Apify nas janelas do dia; fora disso
    devolve a cache (para o IG persistir no painel entre varreduras pagas)."""
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        return _ig_load_cache()
    # poupança: cada varredura custa Apify -> só consultar o IG 4x/dia
    # (08/12/16/20 UTC). Forçar só com o input explícito force_ig=true
    # (NÃO nos empurrões automáticos do Mac de 30/30min, senão o custo dispara).
    forcar = os.environ.get("FORCE_IG", "").lower() == "true"
    agora_ig = datetime.now(timezone.utc)
    bucket = agora_ig.strftime("%Y-%m-%d-%H")  # janela horária
    marca = os.path.join(ROOT, "ig_last.txt")
    if not forcar:
        if agora_ig.hour not in (8, 12, 16, 20):
            return _ig_load_cache()   # fora de janela: mantém os posts já guardados
        # guarda: no máx 1 varredura paga por janela horária (o Mac empurra 2x/hora)
        try:
            if open(marca, encoding="utf-8").read().strip() == bucket:
                return _ig_load_cache()
        except Exception:
            pass
    url = ("https://api.apify.com/v2/acts/sones~instagram-posts-scraper-lowcost/"
           "run-sync-get-dataset-items?token=" + urllib.parse.quote(token))
    newer = (datetime.now(timezone.utc) - timedelta(hours=JANELA_H)).strftime("%Y-%m-%d")
    # só puxamos 1 post/conta (é o que o painel mostra) -> custo ~1/6,
    # o que permite 4x/dia dentro do crédito grátis do Apify
    body = json.dumps({
        "usernames": IG_HANDLES, "postsPerProfile": 1, "newerThan": newer,
        "resultsLimit": 200, "maxItems": 200,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                headers={**UA, "Content-Type": "application/json"})
    out = []
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except Exception as e:
        print("IG/Apify falhou:", e)
        return _ig_load_cache()   # falha na varredura: não apagar o que já havia

    def g(p, *keys):
        for k in keys:
            v = p.get(k)
            if v:
                return v
        return ""
    n_ok = 0
    for p in data:
        # caption pode vir como objeto {"text": ...} ou string
        cap = p.get("caption")
        if isinstance(cap, dict):
            cap = cap.get("text", "")
        cap = str(cap or g(p, "text", "title")).strip()
        # username: scraped_username / user.username / ownerUsername ...
        user = g(p, "scraped_username", "ownerUsername", "username", "owner_username", "ownerUserName")
        if not user and isinstance(p.get("user"), dict):
            user = p["user"].get("username", "")
        ts = g(p, "taken_at", "timestamp", "takenAt", "takenAtTimestamp")
        code = g(p, "code", "shortCode", "shortcode")
        post_url = g(p, "post_url", "url")
        if not cap or not ts:
            continue
        try:
            if isinstance(ts, (int, float)):
                w = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                w = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue
        link = (post_url if post_url else
                (f"https://www.instagram.com/p/{code}/" if code
                 else f"https://www.instagram.com/{user}/"))
        out.append({"title": cap[:120], "when": w,
                    "source": ("IG · @" + user) if user else "IG",
                    "link": link})
        n_ok += 1
    try:  # carimba a janela como já varrida (evita 2ª varredura paga na mesma hora)
        open(marca, "w", encoding="utf-8").write(bucket)
    except Exception:
        pass
    if out:
        _ig_save_cache(out)   # guarda p/ persistir entre varreduras
    else:
        out = _ig_load_cache()  # varredura vazia: mantém o anterior
    print(f"IG/Apify: {len(data)} brutos -> {n_ok} posts com data (cache atualizada)")
    return out


def main():
    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)
    proprio = texto_proprio()

    itens, ok = [], 0
    ig_itens = instagram_apify()
    if ig_itens:
        ok += 1
        for it in ig_itens:
            if not it["when"] or it["when"] < corte:
                continue
            if RUIDO.search(it["title"]):
                continue
            if estrangeiro_corta(it):
                continue  # clube estrangeiro sem relevância (não Champions/PT/LNF/seleção/saída)
            frases = [m.group(0).lower() for m in NOME_RE.finditer(it["title"])]
            if proprio and any(f in proprio for f in frases if len(f) >= 9):
                continue
            it["key"] = key_of(it)
            itens.append(it)
    por_fonte = {}
    for name, url, filt in FEEDS:
        raw = fetch(url)
        if not raw:
            continue
        ok += 1
        req = {"FUTSAL": FUTSAL_RE, "TEMA": TEMA_RE}.get(filt)
        for it in parse_feed(name, raw):
            if not it["when"] or it["when"] < corte:
                continue
            if RUIDO.search(it["title"]):
                continue
            if req and not req.search(it["title"]):
                continue
            if estrangeiro_corta(it):
                continue  # clube estrangeiro sem relevância (não Champions/PT/LNF/seleção/saída)
            por_fonte.setdefault(name, []).append(it)  # p/ tabelas Por fonte
            frases = [m.group(0).lower() for m in NOME_RE.finditer(it["title"])]
            if proprio and any(f in proprio for f in frases if len(f) >= 9):
                continue  # já publicado -> fora da timeline
            it["key"] = key_of(it)
            itens.append(it)

    uniq = {}
    for it in sorted(itens, key=lambda x: x["when"], reverse=True):
        uniq.setdefault(it["key"], it)
    itens = list(uniq.values())

    # PRIORIDADE editorial (maior = topo). Casa com título OU fonte (@conta):
    #  7 Liga Placard (M) · 6 Liga Feminina · 5 2ª Divisão · 4 Imprensa/sites PT ·
    #  3 Institucional intl (LNF/RFEF/SerieA/UEFA/FIFA) · 2 clubes ES/BR · 1 PT · 0 resto
    def classifica(it):
        hay = it["title"] + " " + it.get("source", "")
        if FEMININA.search(hay):      return 6, "pt,feminina"
        if PLACARD.search(hay):       return 7, "pt,placard"
        if SEGUNDA.search(hay):       return 5, "pt,segunda"
        if IMPRENSA.search(hay):      return 4, "pt,jornais"
        if INSTITUCIONAL.search(hay): return 3, "mundo,institucional"
        if CHAMPIONS.search(hay):     return 3, "mundo,institucional"  # Napoli/Kairat/…
        if PT_CLUBES_FORA.search(hay):return 3, "mundo,institucional"  # clubes c/ portugueses
        if ESPANHA.search(hay):       return 2, "mundo,es"
        if BRASIL.search(hay):        return 2, "mundo,br"
        if PRIO_PT.search(hay):       return 1, "pt"
        return 0, "mundo"
    for it in itens:
        it["prio"], it["ftag"] = classifica(it)
        # marca extra "jornais" a QUALQUER item de fonte-jornal (mesmo que o nível
        # seja Placard/2ª/etc), p/ o filtro Jornais mostrar toda a imprensa
        if IMPRENSA.search(it.get("source", "")) and "jornais" not in it["ftag"]:
            it["ftag"] += ",jornais"

    # equilíbrio IG (1/conta, teto global) MAS as competições PT (Placard/Feminina/2ª,
    # prio>=5) estão ISENTAS — mostra-se TUDO o que existir delas
    IG_MAX_POR_CONTA = 1
    IG_MAX_TOTAL = 22
    vistos_ig, ig_total, equilibrado = {}, 0, []
    for it in sorted(itens, key=lambda x: x["when"], reverse=True):
        if it["source"].startswith("IG") and it["prio"] < 5:
            if ig_total >= IG_MAX_TOTAL:
                continue
            if vistos_ig.get(it["source"], 0) >= IG_MAX_POR_CONTA:
                continue
            vistos_ig[it["source"]] = vistos_ig.get(it["source"], 0) + 1
            ig_total += 1
        equilibrado.append(it)
    itens = equilibrado

    itens.sort(key=lambda x: (x["prio"], x["when"]), reverse=True)
    # PORTUGAL DOMINA o painel; o estrangeiro aparece mas apertado. Limite por nível
    # (o mais recente de cada): PT (7-4,1) generoso, estrangeiro (3,2,0) curto.
    por_niv = {}
    for it in itens:
        por_niv.setdefault(it["prio"], []).append(it)
    LIM = {7: 22, 6: 10, 5: 8, 4: 12, 3: 4, 2: 8, 1: 8, 0: 2}
    final = []
    for p in sorted(por_niv, reverse=True):
        final += por_niv[p][:LIM.get(p, 2)]
    final.sort(key=lambda x: (x["prio"], x["when"]), reverse=True)
    itens = final

    LX = timezone(timedelta(hours=1))  # hora de Lisboa (verão)
    stamp = agora.astimezone(LX)
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    data = f"{stamp.day} {meses[stamp.month-1]} {stamp.year} · {stamp:%H:%M}"

    html = R.render(itens, por_fonte, data, ok, len(FEEDS))

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK: {len(itens)} itens · {ok}/{len(FEEDS)} fontes · {data}")


if __name__ == "__main__":
    main()
