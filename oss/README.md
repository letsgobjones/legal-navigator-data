# oss

Licensing data per KBLI 2025 code, taken from the public OSS RBA KBLI pages (`https://oss.go.id/id/kbli`). OSS is the government's licensing system; the legal basis is PP No. 28 Tahun 2025.

## How it works

For each code in [`../scope/creative_subsectors.json`](../scope/creative_subsectors.json), `fetch_oss.py`:

1. searches OSS for the code (the same request the oss.go.id search box makes) to get its page id;
2. fetches the public detail page `https://oss.go.id/id/kbli/detail/<id>` and reads the structured data embedded in it;
3. saves a dated snapshot in `raw/<code>.json` (and the gzipped page in `raw/pages/`, which is gitignored).

It never logs in and only reads public pages, waiting 1.5 seconds between requests to keep the load on OSS light (about 3 seconds per code). Text is copied exactly as OSS returns it.

## Running

From the repo root:

```bash
python3 oss/fetch_oss.py                       # fetch codes that have no snapshot yet, then build
```
```bash
python3 oss/fetch_oss.py --refresh             # re-fetch every code
```
```bash
python3 oss/fetch_oss.py --refresh --only=14111,74113   # re-fetch just these codes
```
```bash
python3 oss/fetch_oss.py --reextract           # re-read saved pages (no network), then build
```
```bash
python3 oss/fetch_oss.py --offline             # rebuild the JSON from existing snapshots only
```

After a refresh, `git diff oss/` shows exactly what OSS changed.

## Output files

| File | What it is |
|---|---|
| `oss_licensing.json` | The data the app uses: `{meta, entries}` |
| `raw/<code>.json` | Snapshot of what OSS returned for that code, with URL and fetch time |
| `review_report.md` | Warnings, plus a risk table by code and business scale |

## Fields

One entry per KBLI 2025 code:

| Field | Meaning |
|---|---|
| `code`, `title` | KBLI 2025 code, and its title from `kbli/kbli_2025.json` |
| `subsectors` | `fesyen` and/or `kriya`, from the scope file |
| `conversion` | How this code relates to KBLI 2020, as OSS shows it: `label` (e.g. *Tetap*, *Berubah*, *Digabung menjadi satu kode*), `ratio` (`1:1`, `N:1`, …), the exact `text` (e.g. *"Kode 90021 berubah menjadi 74113 pada KBLI 2025."*), and `from2020`, the 2020 code OSS links to (for merges, only the first one) |
| `scopes[]` | OSS's *ruang lingkup*: how the code is split into activities. `"Seluruh"` means one scope covering the whole code |
| `scopes[].sector`, `.ministry` | The licensing sector and its ministry |
| `scopes[].rows[]` | One row per business scale |
| `pbUmku[]` | Supporting licenses (*Perizinan Berusaha Untuk Menunjang Kegiatan Usaha*) that may apply to the code |
| `source` | `url`, `ossId` (the detail page id) and `fetchedAt` |

Each row in `scopes[].rows[]`:

| Field | Meaning |
|---|---|
| `scale` / `scaleLabel` | `mikro`, `kecil`, `menengah`, `besar` / OSS's label (*Usaha Mikro*, …) |
| `risk` / `riskLabel` | `rendah`, `menengahRendah`, `menengahTinggi`, `tinggi` / OSS's label |
| `licenses` | License types, e.g. `["Sertifikat Standar"]`. **Empty means OSS lists no license beyond the base registration (NIB)** |
| `requirements[]` | *Persyaratan*: conditions to meet before the license is issued, each `{text, deadline}` |
| `obligations[]` | *Kewajiban*: ongoing duties after licensing, each `{text, deadline}` |
| `authority[]` | *Kewenangan*: who issues it, depending on the situation, each `{parameter, authority}` |
| `landArea`, `issuanceTime`, `validity` | As OSS gives them, with units; `null` when not set |

In `pbUmku[]`, rich-text fields keep both a plain `text` version and the original `html` from OSS.

### `ossCode`

`ossCode` is **OSS's own internal ID** for a record, copied as-is from OSS's `kode` field. It is not a KBLI code and is not meant for users. It is kept so a record can be matched between fetches (to show what OSS changed) and traced back to OSS.

OSS does not document its format. The patterns below were observed across all fetched codes and are for reading the data only. **The app should never split `ossCode` to get meaning; use the `scale` and `sector` fields instead.**

- **On a row**, e.g. `13122-02-06`: KBLI code `13122`, business scale `02` (01 Mikro, 02 Kecil, 03 Menengah, 04 Besar), and a running row number `06` across all of the code's scopes. 13122 has 3 scopes × 4 scales, so its rows run `-01`–`-12`: rows 1–4 for the first scope, 5–8 for the second, 9–12 for the third.
- **On a PB UMKU**, e.g. `012000000018`: the first three digits match the issuing sector's OSS code (`012` Kementerian Pertahanan, `018` Pertanian, `024` Kesehatan, `063` Obat dan Makanan, `085` Badan Pengawas Tenaga Nuklir, `090` Perdagangan); the rest is a sequence number.

## Things to know

- **OSS is a live website**, not a signed document, and its data can change. Every value comes with the date it was fetched. Re-fetch before relying on it for a release.
- **PB UMKU lists what *may* apply.** Some look surprising for small businesses (e.g. clothing manufacturing 14111 lists defense-industry licenses, presumably for military uniform makers). The data copies OSS exactly; how to present "may apply" licenses is an app design decision.
- **The scope is provisional.** See [`../scope/creative_subsectors.json`](../scope/creative_subsectors.json).
