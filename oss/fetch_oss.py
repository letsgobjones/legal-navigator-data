#
#  fetch_oss.py
#  legal-navigator-data
#
#  Created by Brandon Jones (https://github.com/letsgobjones) on 2026-09-30.
#

"""Fetch licensing data per KBLI 2025 code from the public OSS RBA KBLI pages.

For each code in scope/creative_subsectors.json:
  1. find its OSS detail page id via the portal search (the same request the
     oss.go.id search page makes);
  2. fetch https://oss.go.id/id/kbli/detail/<id> and read the structured data
     embedded in the page (Next.js flight data);
  3. save that raw data as a dated snapshot in oss/raw/<code>.json.

Then normalize everything into oss/oss_licensing.json and write
oss/review_report.md. Text is kept exactly as OSS returns it.

Usage (from the repo root):
    python3 oss/fetch_oss.py            # fetch codes without a snapshot, then build
    python3 oss/fetch_oss.py --refresh  # re-fetch every code, then build
    python3 oss/fetch_oss.py --offline  # rebuild from existing snapshots only
    python3 oss/fetch_oss.py --refresh --only=14111,74113   # just these codes
    python3 oss/fetch_oss.py --reextract  # re-read saved pages (oss/raw/pages), then rebuild
"""

import datetime
import gzip
import html as htmllib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

__author__ = "Brandon Jones (https://github.com/letsgobjones)"

FETCHER_VERSION = "1.0"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = HERE / "raw"
PAGES = RAW / "pages"          # gzipped page HTML, gitignored
SCOPE_FILE = ROOT / "scope" / "creative_subsectors.json"
KBLI_2025_JSON = ROOT / "kbli" / "kbli_2025.json"

SEARCH_URL = "https://gw.oss.go.id/v2/portal/kbli"
DETAIL_URL = "https://oss.go.id/id/kbli/detail/{id}"
KBLI_2025_VERSION_ID = "fff4053d-cbb0-51e9-9dc5-1e85b5740704"
HEADERS = {
    "User-Agent": "legal-navigator-data/1.0 (+https://github.com/letsgobjones)",
    "Origin": "https://oss.go.id",
    "Referer": "https://oss.go.id/",
}
DELAY_SECONDS = 1.5          # between requests, to keep the load on OSS light


# --------------------------------------------------------------------------
# 1. Fetch
# --------------------------------------------------------------------------

def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def find_detail_id(code):
    query = urllib.parse.urlencode({
        "kategori": "semua", "search": code, "lang": "id", "localization": "id",
        "limit": 20, "id_version": KBLI_2025_VERSION_ID,
    })
    data = json.loads(get(f"{SEARCH_URL}?{query}"))
    for hit in data["data"]["result"]:
        src = hit["_source"]
        if src.get("kode") == code and str(src.get("version")) == "2025":
            return hit["_id"]
    return None


def flight_data(html):
    """The page's embedded React Server Components payload, as one string."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S)
    return "".join(json.loads(f'"{c}"') for c in chunks)


def extract(html):
    flight = flight_data(html)
    decoder = json.JSONDecoder()
    scopes = {}
    for m in re.finditer(r'\{"id":"[0-9a-f-]{36}","localization"', flight):
        try:
            obj, _ = decoder.raw_decode(flight, m.start())
        except ValueError:
            continue
        if "KbliResikos" in obj:
            scopes[obj["id"]] = obj
    umku = {}
    for m in re.finditer(r'\{"id":"[0-9a-f-]{36}","kode":"\d+","localization":\{"en":\{"nama_dokumen"', flight):
        try:
            obj, _ = decoder.raw_decode(flight, m.start())
        except ValueError:
            continue
        if "parameter_kewenangan" in obj:
            umku[obj["id"]] = obj

    # The 2020 -> 2025 conversion is only present as rendered text.
    conversion = None
    badge = re.search(r'"ti ti-[a-z-]+","aria-hidden":"true"\}\],"([^"]+)",\["\$","span",null,'
                      r'\{"className":"[^"]*","children":"([^"]+)"\}\]', flight)
    # The explanation paragraph right under the badge.
    sentence = re.search(r'"className":"leading-relaxed mt-2 text-sm text-oss-gray-600","children":"([^"]+)"', flight)
    if badge or sentence:
        links = re.findall(r'"href":"/id/kbli/konversi/([^"]+)"', flight)
        conversion = {
            "label": badge.group(1) if badge else None,
            "ratio": badge.group(2) if badge else None,
            "text": sentence.group(1) if sentence else None,
            "from2020": sorted(set(links)),
        }
    return list(scopes.values()), conversion, list(umku.values())


def fetch(code):
    detail_id = find_detail_id(code)
    time.sleep(DELAY_SECONDS)
    if detail_id is None:
        return {"code": code, "found": False,
                "fetchedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    url = DETAIL_URL.format(id=detail_id)
    html = get(url)
    time.sleep(DELAY_SECONDS)
    PAGES.mkdir(parents=True, exist_ok=True)
    (PAGES / f"{code}.html.gz").write_bytes(gzip.compress(html.encode("utf-8")))
    return snapshot_from(code, detail_id, url, html,
                         datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))


def snapshot_from(code, detail_id, url, html, fetched_at):
    scopes, conversion, umku = extract(html)
    return {
        "code": code,
        "found": True,
        "ossId": detail_id,
        "url": url,
        "fetchedAt": fetched_at,
        "conversion": conversion,
        "scopes": scopes,
        "pbUmku": umku,
    }


# --------------------------------------------------------------------------
# 2. Normalize
# --------------------------------------------------------------------------

def loc(obj, key="uraian"):
    if not obj:
        return None
    local = obj.get("localization") or obj.get("local") or {}
    return (local.get("id") or {}).get(key)


def with_unit(value, unit_obj):
    if value in (None, ""):
        return None
    unit = loc(unit_obj)
    return f"{value} {unit}".strip() if unit else str(value)


SCALE_KEY = {"Usaha Mikro": "mikro", "Usaha Kecil": "kecil", "Usaha Menengah": "menengah", "Usaha Besar": "besar"}
RISK_KEY = {"Rendah": "rendah", "Menengah Rendah": "menengahRendah",
            "Menengah Tinggi": "menengahTinggi", "Tinggi": "tinggi"}


def normalize_row(r):
    scale, risk = loc(r.get("SkalaUsaha")), loc(r.get("Resiko"))
    return {
        "ossCode": r.get("kode"),
        "scale": SCALE_KEY.get(scale, scale),
        "scaleLabel": scale,
        "risk": RISK_KEY.get(risk, risk),
        "riskLabel": risk,
        "licenses": [loc(i.get("JenisPerizinan")) for i in r.get("KbliIzins") or []],
        "licenseDocuments": [loc(i.get("Izin"), "nama_dokumen") for i in r.get("KbliIzins") or []],
        "landArea": with_unit(r.get("luas_lahan"), r.get("SatuanLuasTanah")),
        "issuanceTime": with_unit(r.get("jangka_waktu"), r.get("SatuanJangkaWaktu")),
        "validity": with_unit(r.get("masa_berlaku"), r.get("SatuanMasaBerlaku")),
        "requirements": [
            {"text": loc(p), "deadline": with_unit(p.get("jangka_waktu"), p.get("SatuanJangkaWaktu"))}
            for p in r.get("KbliPersyaratans") or []
        ],
        "obligations": [
            {"text": loc(k), "deadline": with_unit(k.get("jangka_waktu"), k.get("SatuanJangkaWaktu"))}
            for k in r.get("KbliKewajibans") or []
        ],
        "authority": [
            {"parameter": loc(k.get("ParameterKewenangan")), "authority": loc(k.get("Kewenangan"))}
            for k in r.get("KbliResikoKewenangans") or []
        ],
    }


def plain(text):
    """HTML from OSS rich-text fields -> plain text; list items on their own lines."""
    if not text:
        return text
    text = re.sub(r"<li[^>]*>", "\n- ", text)
    text = re.sub(r"<br\s*/?>|</p>", "\n", text)
    text = htmllib.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def umku_items(items, key):
    out = []
    for it in items or []:
        raw = ((it.get(key) or {}).get("id") or {})
        value = next(iter(raw.values()), None) if raw else None
        out.append({"text": plain(value), "html": value if value and "<" in value else None,
                    "deadline": it.get("jangkaWaktu") or None})
    return out


def normalize_umku(u):
    return {
        "ossCode": u.get("kode"),
        "document": loc(u, "nama_dokumen"),
        "sector": loc(u.get("sektor")),
        "authority": [{"parameter": p.get("parameter"), "authority": p.get("kewenangan")}
                      for p in u.get("parameter_kewenangan") or []],
        "requirements": umku_items(u.get("persyaratan"), "persyaratan"),
        "obligations": umku_items(u.get("kewajiban"), "kewajiban"),
        "regulations": u.get("referensi_peraturan") or [],
    }


def normalize(snapshot, scope_entry, kbli2025):
    code = snapshot["code"]
    entry = {
        "code": code,
        "title": kbli2025[code]["title"] if code in kbli2025 else None,
        "subsectors": scope_entry["subsectors"],
        "found": snapshot["found"],
    }
    if not snapshot["found"]:
        return entry
    entry["conversion"] = snapshot["conversion"]
    entry["scopes"] = [
        {
            "scope": loc(s),
            "sector": loc(s.get("Sektor")),
            "ministry": loc(s.get("Sektor"), "deskripsi"),
            "regulations": [loc(p) or p for p in s.get("ReferensiPeraturans") or []],
            "ossUpdatedAt": s.get("updated_at") or s.get("created_at"),
            "rows": sorted((normalize_row(r) for r in s["KbliResikos"]),
                           key=lambda row: list(SCALE_KEY.values()).index(row["scale"])
                           if row["scale"] in SCALE_KEY.values() else 99),
        }
        for s in snapshot["scopes"]
    ]
    entry["pbUmku"] = [normalize_umku(u) for u in snapshot.get("pbUmku", [])]
    entry["source"] = {"url": snapshot["url"], "ossId": snapshot["ossId"], "fetchedAt": snapshot["fetchedAt"]}
    return entry


# --------------------------------------------------------------------------
# 3. Validate and write
# --------------------------------------------------------------------------

def validate(entries, kbli2025):
    errors, warnings = [], []
    for e in entries:
        c = e["code"]
        if c not in kbli2025:
            errors.append(f"{c}: not a KBLI 2025 code")
        if not e["found"]:
            warnings.append(("Not found in OSS search", c, ""))
            continue
        if not e["scopes"]:
            warnings.append(("No scope (ruang lingkup) data on the OSS page", c, e["source"]["url"]))
        if e["conversion"] is None:
            warnings.append(("No 2020 → 2025 conversion info on the page", c, ""))
        for s in e["scopes"]:
            scales = [r["scale"] for r in s["rows"]]
            if len(scales) != len(set(scales)):
                warnings.append(("Duplicate business scale within one scope", c, f"{s['scope']}: {scales}"))
            for r in s["rows"]:
                if r["scale"] not in SCALE_KEY.values():
                    warnings.append(("Unknown business scale", c, str(r["scaleLabel"])))
                if r["risk"] not in RISK_KEY.values():
                    warnings.append(("Unknown risk level", c, str(r["riskLabel"])))
                if not r["authority"]:
                    warnings.append(("No authority listed", c, f"{s['scope']} / {r['scaleLabel']}"))
    return errors, warnings


def write_report(path, entries, warnings, meta):
    lines = ["# OSS licensing fetch — review report", "",
             f"Generated {datetime.date.today().isoformat()} by fetch_oss.py v{FETCHER_VERSION}.", "",
             "Counts: " + ", ".join(f"{k} {v}" for k, v in meta["counts"].items()), "",
             f"**{len(warnings)} warnings.**", ""]
    by_kind = defaultdict(list)
    for kind, where, detail in warnings:
        by_kind[kind].append((where, detail))
    for kind, items in by_kind.items():
        lines += [f"## {kind} ({len(items)})", ""]
        lines += [f"- **{w}** — {d}" if d else f"- **{w}**" for w, d in items]
        lines.append("")
    lines += ["## Risk by code and business scale", "",
              "| Code | Title | Scope | Mikro | Kecil | Menengah | Besar |", "|---|---|---|---|---|---|---|"]
    for e in entries:
        for s in e.get("scopes", []):
            risk = {r["scale"]: r["riskLabel"] for r in s["rows"]}
            lines.append(f"| {e['code']} | {e['title']} | {s['scope']} | "
                         + " | ".join(risk.get(k, "—") for k in SCALE_KEY.values()) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    refresh, offline = "--refresh" in sys.argv, "--offline" in sys.argv
    if "--reextract" in sys.argv:
        for page in sorted(PAGES.glob("*.html.gz")):
            code = page.name.split(".")[0]
            old = json.loads((RAW / f"{code}.json").read_text(encoding="utf-8"))
            html = gzip.decompress(page.read_bytes()).decode("utf-8")
            snap = snapshot_from(code, old["ossId"], old["url"], html, old["fetchedAt"])
            (RAW / f"{code}.json").write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
        offline = True
    scope = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    kbli2025 = {e["code"]: e for e in json.loads(KBLI_2025_JSON.read_text(encoding="utf-8"))["entries"]}
    RAW.mkdir(exist_ok=True)

    only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")), None)
    for item in scope["codes"]:
        path = RAW / f"{item['code']}.json"
        if only and item["code"] not in only:
            continue
        if offline or (path.exists() and not refresh):
            continue
        print(f"fetching {item['code']} …", flush=True)
        snapshot = fetch(item["code"])
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")

    entries = []
    for item in scope["codes"]:
        path = RAW / f"{item['code']}.json"
        if not path.exists():
            print(f"missing snapshot for {item['code']} (run without --offline)", file=sys.stderr)
            continue
        entries.append(normalize(json.loads(path.read_text(encoding="utf-8")), item, kbli2025))

    errors, warnings = validate(entries, kbli2025)
    fetched = sorted(e["source"]["fetchedAt"] for e in entries if e["found"])
    meta = {
        "source": "OSS RBA public KBLI pages (https://oss.go.id/id/kbli)",
        "legalBasis": "PP No. 28 Tahun 2025 tentang Penyelenggaraan Perizinan Berusaha Berbasis Risiko",
        "kbliEdition": "KBLI 2025",
        "scope": {"file": "scope/creative_subsectors.json", "status": scope["meta"]["status"]},
        "fetcherVersion": FETCHER_VERSION,
        "fetchedFrom": fetched[0] if fetched else None,
        "fetchedTo": fetched[-1] if fetched else None,
        "generatedAt": datetime.date.today().isoformat(),
        "note": "Text is copied exactly as OSS returns it. An empty `licenses` list means OSS lists no "
                "license beyond the base registration for that scale.",
        "counts": {
            "codes": len(entries),
            "found": sum(e["found"] for e in entries),
            "scopes": sum(len(e.get("scopes", [])) for e in entries),
            "rows": sum(len(s["rows"]) for e in entries for s in e.get("scopes", [])),
            "pbUmku": sum(len(e.get("pbUmku", [])) for e in entries),
        },
    }
    write_report(HERE / "review_report.md", entries, warnings, meta)

    if errors:
        print(f"{len(errors)} hard errors — JSON not written:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)

    (HERE / "oss_licensing.json").write_text(
        json.dumps({"meta": meta, "entries": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {meta['counts']}; {len(warnings)} warnings -> review_report.md")


if __name__ == "__main__":
    main()
