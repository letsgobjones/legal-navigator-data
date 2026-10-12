#
#  export_app_data.py
#  legal-navigator-data
#
#  Created by Brandon Jones (https://github.com/letsgobjones) on 2026-10-12.
#

"""Write the small, app-ready OSS file from the full licensing data.

Reads (never modifies):
    oss/oss_licensing.json            full OSS data, 1,558 codes (~43 MB)
    scope/creative_subsectors.json    which codes the app covers right now

Writes:
    app/oss_fesyen_kriya.json         only the in-scope codes, only the fields the app uses

The app reads kbli/kbli_2025.json directly; it is small enough to need no export.

What changes in the app copy (text is never reworded):
  - only codes listed in the scope file are kept
  - dropped fields: title (the app takes titles from KBLI), found, ossCode, scaleLabel,
    riskLabel (the app derives labels from scale and risk), landArea, validity and
    regulations (empty everywhere), html (the plain `text` is kept)
  - a deadline that is only whitespace becomes null (OSS has a few such values)

Usage (from the repo root):
    python3 app/export_app_data.py
"""

import datetime
import json
import sys
from pathlib import Path

__author__ = "Brandon Jones (https://github.com/letsgobjones)"

SCHEMA_VERSION = 1
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OSS_FILE = ROOT / "oss" / "oss_licensing.json"
SCOPE_FILE = ROOT / "scope" / "creative_subsectors.json"
KBLI_FILE = ROOT / "kbli" / "kbli_2025.json"
OUT_FILE = HERE / "oss_fesyen_kriya.json"


def clean_deadline(value):
    """Whitespace-only deadlines carry no information; trim the rest."""
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def item(raw):
    return {"ossId": raw["ossId"], "text": raw["text"], "deadline": clean_deadline(raw.get("deadline"))}


def authority(raw):
    out = {"parameter": raw.get("parameter"), "authority": raw["authority"]}
    if raw.get("ossId"):
        out["ossId"] = raw["ossId"]
    return out


def row(raw):
    return {
        "ossId": raw["ossId"],
        "scale": raw["scale"],
        "risk": raw["risk"],
        "licenses": raw["licenses"],
        "licenseDocuments": raw["licenseDocuments"],
        "issuanceTime": raw.get("issuanceTime"),
        "requirements": [item(i) for i in raw["requirements"]],
        "obligations": [item(i) for i in raw["obligations"]],
        "authority": [authority(a) for a in raw["authority"]],
    }


def scope(raw):
    return {
        "ossId": raw["ossId"],
        "scope": raw["scope"],
        "sector": raw["sector"],
        "ministry": raw.get("ministry"),
        "ossUpdatedAt": raw["ossUpdatedAt"],
        "rows": [row(r) for r in raw["rows"]],
    }


def pb_umku(raw):
    return {
        "ossId": raw["ossId"],
        "document": raw["document"],
        "sector": raw.get("sector"),
        "authority": [authority(a) for a in raw["authority"]],
        "requirements": [item(i) for i in raw["requirements"]],
        "obligations": [item(i) for i in raw["obligations"]],
    }


def entry(raw, subsectors):
    return {
        "code": raw["code"],
        "subsectors": subsectors,
        "conversion": raw.get("conversion"),
        "scopes": [scope(s) for s in raw.get("scopes") or []],
        "pbUmku": [pb_umku(u) for u in raw.get("pbUmku") or []],
        "source": raw["source"],
    }


def main():
    full = json.loads(OSS_FILE.read_text(encoding="utf-8"))
    scope_codes = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    kbli_codes = {e["code"] for e in json.loads(KBLI_FILE.read_text(encoding="utf-8"))["entries"]}
    by_code = {e["code"]: e for e in full["entries"]}

    errors = []
    entries = []
    for item_ in scope_codes["codes"]:
        code = item_["code"]
        raw = by_code.get(code)
        if raw is None or not raw.get("found"):
            errors.append(f"{code}: no OSS data in oss_licensing.json")
        elif code not in kbli_codes:
            errors.append(f"{code}: not a KBLI 2025 code")
        else:
            entries.append(entry(raw, item_["subsectors"]))
    if errors:
        print("Export failed:", *errors, sep="\n  ", file=sys.stderr)
        sys.exit(1)

    src = full["meta"]
    meta = {
        "format": "legal-navigator-app-export",
        "schemaVersion": SCHEMA_VERSION,
        "kbliEdition": src["kbliEdition"],
        "legalBasis": src["legalBasis"],
        "source": src["source"],
        "fetchedFrom": src["fetchedFrom"],
        "fetchedTo": src["fetchedTo"],
        "generatedAt": datetime.date.today().isoformat(),
        "derivedFrom": {"file": "oss/oss_licensing.json", "fetcherVersion": src["fetcherVersion"]},
        "scope": {"file": "scope/creative_subsectors.json", "status": scope_codes["meta"]["status"]},
        "counts": {
            "codes": len(entries),
            "scopes": sum(len(e["scopes"]) for e in entries),
            "rows": sum(len(s["rows"]) for e in entries for s in e["scopes"]),
            "pbUmku": sum(len(e["pbUmku"]) for e in entries),
        },
    }

    # One entry per line: small, and a change to one code is one changed line.
    body = ",\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in entries)
    OUT_FILE.write_text(
        '{"meta":' + json.dumps(meta, ensure_ascii=False) + ',\n"entries":[\n' + body + "\n]}\n",
        encoding="utf-8",
    )
    size_kb = OUT_FILE.stat().st_size / 1000
    print(f"Wrote {OUT_FILE.relative_to(ROOT)}: {meta['counts']} ({size_kb:,.0f} KB)")


if __name__ == "__main__":
    main()
