# kbli_parse

Turns the official KBLI 2025 PDF from BPS (`klasifikasi-baku-lapangan-usaha-indonesia--kbli--2025--2.pdf`) into a clean, flat JSON file for the Legal Navigator iOS app.

The parser reads each piece of text's **font and position** in the PDF (with PyMuPDF), not plain extracted text. That's how it reliably tells codes, titles, descriptions, and bullets apart, and drops page headers, footers, and the diagonal `https://www.bps.go.id` watermark.

## Quick start

Requires Python 3.9+.

```bash
pip3 install -r requirements.txt
```

The PDF is expected one folder up (`../klasifikasi-baku-lapangan-usaha-indonesia--kbli--2025--2.pdf`):

```bash
python3 parse_kbli.py
```

Or pass the PDF path explicitly:

```bash
python3 parse_kbli.py path/to/kbli.pdf
```

It takes a few seconds. Expected output:

```
Wrote 2443 entries {'kategori': 22, 'golonganPokok': 87, 'golongan': 257, 'subgolongan': 519, 'kelompok': 1558}; 14 warnings -> review_report.md
```

## Output files

| File | What it is |
|---|---|
| `kbli_2025.json` | The data the app uses. |
| `review_report.md` | Warnings to check by hand against the PDF (page numbers included). |

## JSON format

```json
{
  "meta": {
    "edition": "KBLI 2025",
    "source": "klasifikasi-baku-lapangan-usaha-indonesia--kbli--2025--2.pdf",
    "publisher": "Badan Pusat Statistik",
    "parserVersion": "1.0",
    "generatedAt": "2026-09-30",
    "counts": { "kategori": 22, "golonganPokok": 87, "golongan": 257, "subgolongan": 519, "kelompok": 1558 }
  },
  "entries": [ … one object per code … ]
}
```

`entries` is a **flat list**, with one entry per code at every level. The app builds the tree from `parent` and `children`.

```json
{
  "code": "01111",
  "level": "kelompok",
  "title": "PERTANIAN JAGUNG",
  "parent": "0111",
  "children": [],
  "description": "Kelompok ini mencakup kegiatan pertanian jagung, … Kelompok ini tidak mencakup pertanian jagung manis, lihat kelompok 01133.",
  "includes": ["Kelompok ini mencakup kegiatan pertanian jagung, …"],
  "alsoIncludes": ["Kelompok ini juga mencakup kegiatan penanaman jagung untuk menghasilkan benih berupa biji."],
  "excludes": ["Kelompok ini tidak mencakup pertanian jagung manis, lihat kelompok 01133."],
  "references": [
    { "code": "01133", "section": "excludes", "text": "Kelompok ini tidak mencakup pertanian jagung manis, lihat kelompok 01133." }
  ],
  "seeChild": null,
  "source": { "pdfPages": [248], "printedPages": [232] }
}
```

| Field | Meaning |
|---|---|
| `code` | KBLI code: a letter `A`–`V` for kategori, or 2–5 digits. Unique. |
| `level` | `kategori`, `golonganPokok` (2 digits), `golongan` (3), `subgolongan` (4), `kelompok` (5). |
| `title` | Official title, including titles that wrap over two lines in the PDF. |
| `parent` | Parent code. `null` for kategori. |
| `children` | Child codes, in book order. |
| `description` | The **full text exactly as in the PDF**. Bullet items start with `- ` on their own line. |
| `includes` / `alsoIncludes` / `excludes` | The same text split by the book's own markers: "mencakup", "juga mencakup", "tidak mencakup". |
| `references` | Codes mentioned in the text ("lihat subgolongan 0130"), with the section they appeared in (`includes`, `alsoIncludes`, `excludes`, or `description`) and the exact sentence. |
| `seeChild` | Set when the entry only says "Lihat kelompok X", meaning its content lives in a code below it. Otherwise `null`. |
| `source` | Where the entry appears. `pdfPages` = page in the PDF file; `printedPages` = page number printed in the book. |

### Text rules

The data must be traceable to the government source, so the parser **never rewords anything**. The only changes are:
- lines that wrap mid-sentence are joined back together;
- page headers, footers, page numbers, and the watermark are removed.

The book's own typos and spacing (e.g. `aluminium oksida , lihat …`) are kept as printed.

The section lists only use the exact phrases above. A sentence like "…tidak termasuk di sini…" stays in `description` only.

## Validation

The script checks its own output every run.

**Hard errors: the script stops and does not write the JSON.**
- duplicate codes
- a `parent` or `children` code that doesn't exist
- a code that doesn't start with its parent's code
- a kategori count other than 22

**Warnings: the JSON is written, and each warning goes to `review_report.md`.**
- references to codes that don't exist in KBLI 2025
- "Lihat …" pointing to a code that isn't below the entry
- empty descriptions, leftover page noise, titles that aren't uppercase

The 14 warnings from the current PDF have all been checked. They're errors in the book itself, not the parser:
- **12 references** to codes that don't exist in KBLI 2025 (2229, 4630, 4942, …), probably left over from KBLI 2020. They're kept as printed; the app should treat them as dead links.
- **304** says "Lihat subgolongan 304", pointing to itself. It should be 3040. `seeChild` is left `null` so the app can't loop.
- **8552** has no description in the book; its content is under its only child, 85520.

If a new run shows **new** warnings, open the PDF page listed in the report and check whether it's the book or the parser.

## When a new edition (or corrected PDF) comes out

These constants at the top of `parse_kbli.py` depend on the PDF's layout:

| Constant | Current value | What it is |
|---|---|---|
| `FIRST_PAGE` | `247` | First PDF page of the detailed section (where "A PERTANIAN, KEHUTANAN, DAN PERIKANAN" starts). |
| `PRINTED_OFFSET` | `16` | PDF page minus printed page number. |
| `CODE_X_MAX` | `90` | Codes sit at the left margin (x ≈ 71). |
| `BODY_BOTTOM` | `670` | Anything below this y is the footer. |

Also update the expected kategori count in `validate()` (22) and bump `PARSER_VERSION` if you change the parser.

If the new PDF looks different, inspect a page's layout like this:

```python
import fitz
page = fitz.open("kbli.pdf")[246]   # 0-based index
for b in page.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l["spans"]:
            print(round(s["bbox"][0]), round(s["bbox"][1]), s["size"], s["font"], repr(s["text"]))
```

## Using it in Swift

```swift
struct KBLIFile: Codable { let meta: Meta; let entries: [KBLIEntry] }

struct Meta: Codable {
    let edition, source, publisher, parserVersion, generatedAt: String
    let counts: [String: Int]
}

struct KBLIEntry: Codable, Identifiable, Hashable {
    enum Level: String, Codable { case kategori, golonganPokok, golongan, subgolongan, kelompok }
    struct Reference: Codable, Hashable { let code, section, text: String }
    struct Source: Codable, Hashable { let pdfPages, printedPages: [Int] }

    var id: String { code }
    let code: String
    let level: Level
    let title: String
    let parent: String?
    let children: [String]
    let description: String
    let includes, alsoIncludes, excludes: [String]
    let references: [Reference]
    let seeChild: String?
    let source: Source
}

let file = try JSONDecoder().decode(KBLIFile.self, from: data)
let byCode: [String: KBLIEntry] = Dictionary(uniqueKeysWithValues: file.entries.map { ($0.code, $0) })
```

## Author

Brandon Jones ([@letsgobjones](https://github.com/letsgobjones))
