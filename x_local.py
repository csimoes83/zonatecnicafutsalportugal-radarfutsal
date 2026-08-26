#!/usr/bin/env python3
"""Recolha LOCAL de X/Twitter via nitter (corre no Mac, IP residencial que o nitter
aceita). Puxa TODAS as contas de X, com espaçamento + arrefecimento anti-bloqueio,
e escreve x_cache.json que o scan.py (cloud) lê. Reutiliza FEEDS/parse do scan.py.

FAILOVER: as instâncias nitter morrem com frequência (nitter.net deu 410 em ago/2026).
Este script tenta uma LISTA de instâncias, valida que trazem conteúdo real (não
placeholders tipo "not whitelisted"/datas de 1971) e memoriza a que funciona
(x_instance.txt) para tentar primeiro na próxima. Se NENHUMA estiver viva, sai sem
mexer na cache — quando alguma reviver, o X volta sozinho."""
import json, os, re, time
from datetime import datetime, timezone, timedelta
import scan

ROOT = os.path.dirname(os.path.abspath(__file__))
XCACHE = os.path.join(ROOT, "x_cache.json")
IST_FILE = os.path.join(ROOT, "x_instance.txt")
ESPACO = 5.0        # segundos entre contas (gentil com o nitter)
JANELA_H = 336

# Instâncias nitter candidatas (ordem = preferência). A lista é propositadamente
# larga: quando qualquer uma revive, o failover apanha-a automaticamente.
INSTANCIAS = [
    "nitter.net", "nitter.poast.org", "nitter.privacyredirect.com",
    "nitter.tiekoetter.com", "lightbrd.com", "nitter.space",
    "nitter.kavin.rocks", "nitter.privacydev.net", "xcancel.com",
    "nitter.woodland.cafe", "nitter.lucabased.xyz",
]


def handle_de(url):
    """Extrai o handle de um URL tipo https://nitter.net/PalmaFutsal/rss."""
    m = re.search(r"://[^/]+/([^/]+)/rss", url)
    return m.group(1) if m else None


def _feed_vivo(raw):
    """True se o raw traz pelo menos 1 tweet com data real (>=2015),
    filtrando placeholders (datas de 1971, 'not whitelisted', etc.)."""
    if not raw or b"<item" not in raw:
        return False
    try:
        for it in scan.parse_feed("probe", raw):
            w = it.get("when")
            if w and w.year >= 2015:
                return True
    except Exception:
        pass
    return False


def escolhe_instancia():
    """Encontra UMA instância viva (probe com um handle ativo). Tenta a última que
    funcionou primeiro. Devolve o host ou None se todas estiverem mortas."""
    ordem = list(INSTANCIAS)
    try:
        ultima = open(IST_FILE).read().strip()
        if ultima in ordem:
            ordem.remove(ultima); ordem.insert(0, ultima)
    except Exception:
        pass
    for host in ordem:
        raw = scan.fetch(f"https://{host}/UEFAFutsal/rss")
        if _feed_vivo(raw):
            try: open(IST_FILE, "w").write(host)
            except Exception: pass
            return host
        time.sleep(2)
    return None


def main():
    xs = [(n, u, f) for n, u, f in scan.FEEDS if str(f).startswith("X")]
    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)

    host = escolhe_instancia()
    if not host:
        print("X local: nenhuma instância nitter viva agora — cache mantida "
              "(failover volta a tentar no próximo ciclo)")
        return

    cache = {}
    try:
        for p in json.load(open(XCACHE, encoding="utf-8")):
            if p.get("link"):
                cache[p["link"]] = p
    except Exception:
        pass

    ok = fail = novos = falhas_seguidas = 0
    for name, url, filt in xs:
        h = handle_de(url)
        raw = scan.fetch(f"https://{host}/{h}/rss") if h else None
        if not _feed_vivo(raw):
            fail += 1
            falhas_seguidas += 1
            if falhas_seguidas >= 4:   # instância a fraquejar -> tentar reeleger
                novo = escolhe_instancia()
                if novo and novo != host:
                    host = novo
                falhas_seguidas = 0
                time.sleep(30)
            time.sleep(ESPACO)
            continue
        falhas_seguidas = 0
        req = scan.FUTSAL_RE if filt == "X_FUTSAL" else None
        got = 0
        for it in scan.parse_feed(name, raw):
            if not it["when"] or it["when"] < corte:
                continue
            if req and not req.search(it["title"]):
                continue
            cache[it["link"]] = {
                "title": it["title"][:180], "source": name,
                "link": it["link"], "when": it["when"].isoformat(),
            }
            got += 1
            novos += 1
        if got:
            ok += 1
        time.sleep(ESPACO)

    vivos = [p for p in cache.values()
             if datetime.fromisoformat(p["when"]) >= corte]
    vivos.sort(key=lambda x: x["when"], reverse=True)
    json.dump(vivos, open(XCACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print(f"X local [{host}]: {ok} contas c/ tweets · {fail} falha · "
          f"+{novos} novos · cache {len(vivos)} tweets")


if __name__ == "__main__":
    main()
