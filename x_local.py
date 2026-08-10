#!/usr/bin/env python3
"""Recolha LOCAL de X/Twitter via nitter (corre no Mac, IP residencial que o nitter
aceita). Puxa TODAS as contas de X, com espaçamento + arrefecimento anti-bloqueio,
e escreve x_cache.json que o scan.py (cloud) lê. Reutiliza FEEDS/parse do scan.py."""
import json, os, time
from datetime import datetime, timezone, timedelta
import scan

ROOT = os.path.dirname(os.path.abspath(__file__))
XCACHE = os.path.join(ROOT, "x_cache.json")
ESPACO = 5.0        # segundos entre contas (gentil com o nitter)
JANELA_H = 72


def main():
    xs = [(n, u, f) for n, u, f in scan.FEEDS if str(f).startswith("X")]
    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)

    cache = {}
    try:
        for p in json.load(open(XCACHE, encoding="utf-8")):
            if p.get("link"):
                cache[p["link"]] = p
    except Exception:
        pass

    ok = fail = novos = falhas_seguidas = 0
    for name, url, filt in xs:
        raw = scan.fetch(url)
        if not raw or b"<item" not in raw:
            fail += 1
            falhas_seguidas += 1
            if falhas_seguidas >= 3:      # nitter a limitar -> arrefecer e continuar
                time.sleep(60)
                falhas_seguidas = 0
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
    print(f"X local: {ok} contas c/ tweets · {fail} falha · cache {len(vivos)} tweets")


if __name__ == "__main__":
    main()
