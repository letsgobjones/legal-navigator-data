# legal-navigator-data

Structured data for the BCIC Legal Navigator iOS app, parsed from official Indonesian government sources. Every output traces back to a specific source file and page. Text is copied from the source, never reworded.

## Layout

| Folder | What it produces | Status |
|---|---|---|
| [`kbli/`](kbli/) | `kbli_2025.json`: the full KBLI 2025 classification (2,443 codes) | Done |
| `kbli_crosswalk/` | KBLI 2020 → 2025 code conversion table | Planned |
| `pp28/` | Licensing data per KBLI code from PP 28/2025 Lampiran I (risk level, licenses, requirements, obligations, authority), one file per sector | Planned; starting with fashion/apparel |
| [`sources/`](sources/) | The official PDFs (not committed) and [`SOURCES.md`](sources/SOURCES.md) with URLs and checksums | |

## How the data links

PP 28/2025 lists its licensing rules by **KBLI 2020** codes, but the app uses **KBLI 2025**. Some codes were renumbered or deleted between editions, and some old numbers now mean something else. For example, 2020's 16214 is 2025's 16212, which was a different activity in 2020. So PP 28 rows must go through `kbli_crosswalk/`, never be matched to `kbli_2025.json` by code number alone.

```
kbli_2025.json  ◄──  kbli_2020_to_2025.json  ◄──  pp28/sectors/*.json
  (2025 codes)          (conversion table)          (2020 codes)
```

## Setup

Requires Python 3.9+.

```bash
pip3 install -r requirements.txt
```

Download the source PDFs listed in [`sources/SOURCES.md`](sources/SOURCES.md) into `sources/`, then run each parser from the repo root, e.g.:

```bash
python3 kbli/parse_kbli.py
```

See each folder's README for details.

## Author

Brandon Jones ([@letsgobjones](https://github.com/letsgobjones))
