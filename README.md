# legal-navigator-data

Structured data for the BCIC Legal Navigator iOS app, parsed from official Indonesian government sources. Every output traces back to a specific source file and page. Text is copied from the source, never reworded.

## Layout

| Folder | What it produces | Status |
|---|---|---|
| [`kbli/`](kbli/) | `kbli_2025.json`: the full KBLI 2025 classification (2,443 codes) | Done |
| [`scope/`](scope/) | `creative_subsectors.json`: which KBLI 2025 codes count as Fesyen / Kriya | Provisional, until the official Kemenekraf list is available |
| [`oss/`](oss/) | `oss_licensing.json`: licensing data per KBLI 2025 code from the public OSS RBA KBLI pages: scopes, risk and license per business scale, requirements, obligations, authority, PB UMKU, and the 2020 → 2025 conversion | Done for all 1,558 KBLI 2025 kelompok (219 have no licensing data on OSS, mostly sectors licensed outside OSS such as education, public administration and OJK-regulated finance); tagged Fesyen/Kriya via the scope file |
| [`sources/`](sources/) | The official PDFs (not committed) and [`SOURCES.md`](sources/SOURCES.md) with URLs and checksums | |

## How the data links

Everything the app uses is keyed by **KBLI 2025** code:

```
kbli_2025.json  ◄──  oss/oss_licensing.json      (same KBLI 2025 codes)
      ▲
      └──────────── scope/creative_subsectors.json (which codes are Fesyen / Kriya)
```

The legal basis for the licensing data is PP 28/2025. Its appendix tables use **KBLI 2020** codes, and some numbers changed meaning in KBLI 2025 (e.g. 2020's 16214 is 2025's 16212, which was a different activity in 2020), so PP 28 rows must never be matched to KBLI 2025 by number alone. OSS has already done that conversion, which is why OSS is the primary source and the PP 28 PDFs are kept for citation and spot checks.

OSS is a live website: `oss/raw/<code>.json` keeps a dated snapshot of each fetch, so any value can be traced to what OSS showed on that date.

## Setup

Requires Python 3.9+.

```bash
pip3 install -r requirements.txt
```

Download the source PDFs listed in [`sources/SOURCES.md`](sources/SOURCES.md) into `sources/`, then run each parser from the repo root, e.g.:

```bash
python3 kbli/parse_kbli.py
```

The OSS data needs no PDF; it fetches from oss.go.id (about 3 seconds per code, to keep the load light):

```bash
python3 oss/fetch_oss.py            # fetch codes without a snapshot yet
```
```bash
python3 oss/fetch_oss.py --refresh  # re-fetch everything
```

See each folder's README for details.

## Author

Brandon Jones · [GitHub](https://github.com/letsgobjones) · [LinkedIn](https://www.linkedin.com/in/letsgobjones/)
