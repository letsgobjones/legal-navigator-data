#
#  parse_kbli.py
#  legal-navigator-data
#
#  Created by Brandon Jones (https://github.com/letsgobjones) on 2026-09-30.
#

"""Parse the KBLI 2025 PDF (BPS) into a flat, validated JSON file.

Reads span fonts/positions with PyMuPDF instead of plain text, so page
headers/footers and the diagonal watermark can be dropped reliably and
titles/descriptions/bullets are separated by layout, not guesswork.

Usage:
    python3 parse_kbli.py [path/to/kbli.pdf]

Outputs (next to this script):
    kbli_2025.json     {meta, entries}
    review_report.md   warnings to check against the PDF

Exits non-zero (and writes no JSON) on hard errors: broken hierarchy,
duplicate codes, wrong category count.
"""

import datetime
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

__author__ = "Brandon Jones (https://github.com/letsgobjones)"

PARSER_VERSION = "1.0"
HERE = Path(__file__).resolve().parent
DEFAULT_PDF = HERE.parent / "sources" / "kbli_2025" / "klasifikasi-baku-lapangan-usaha-indonesia--kbli--2025--2.pdf"

# Detailed-description section (1-based PDF page numbers).
FIRST_PAGE = 247
# Printed page number = PDF page - offset (PDF 247 is printed "231").
PRINTED_OFFSET = 16

CODE_X_MAX = 90          # codes sit at the left margin (x ~ 71)
BODY_BOTTOM = 670        # footer starts below this y
TITLE_LINE_GAP = 15      # a title's wrapped line follows within this gap
PARAGRAPH_GAP = 15       # larger gaps start a new paragraph
BULLET_GLYPHS = {"-", "−", "–", "•"}

LEVELS = {1: "kategori", 2: "golonganPokok", 3: "golongan", 4: "subgolongan", 5: "kelompok"}
LEVEL_WORDS = r"(kategori|golongan pokok|golongan|subgolongan|kelompok)"


# --------------------------------------------------------------------------
# 1. Extract body lines
# --------------------------------------------------------------------------

def extract_lines(doc):
    """Yield body lines as dicts: page, x, y0, y1, text, first_font, is_bullet."""
    for pno in range(FIRST_PAGE - 1, len(doc)):
        page = doc[pno]
        rows = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                if line["dir"] != (1.0, 0.0):          # rotated watermark
                    continue
                spans = [s for s in line["spans"]
                         if s["text"].strip() and "Open Sans" not in s["font"]]
                if not spans or spans[0]["bbox"][1] > BODY_BOTTOM:
                    continue
                rows.append(spans)

        # Merge spans that sit on the same visual line (code + title share a
        # baseline; bullets are slightly offset vertically).
        rows.sort(key=lambda sp: (round(sp[0]["bbox"][1]), sp[0]["bbox"][0]))
        merged = []
        for spans in rows:
            y0 = spans[0]["bbox"][1]
            if merged and abs(merged[-1]["y0"] - y0) <= 3.5:
                merged[-1]["spans"].extend(spans)
            else:
                merged.append({"y0": y0, "spans": list(spans)})

        for m in merged:
            spans = sorted(m["spans"], key=lambda s: s["bbox"][0])
            first = spans[0]
            first_text = first["text"].strip()
            is_bullet = first_text in BULLET_GLYPHS and len(spans) > 1
            text_spans = spans[1:] if is_bullet else spans
            yield {
                "page": pno + 1,
                "x": first["bbox"][0],
                "y0": min(s["bbox"][1] for s in text_spans),
                "y1": max(s["bbox"][3] for s in text_spans),
                "spans": text_spans,
                "text": join_spans(text_spans),
                "is_bullet": is_bullet,
            }


def join_spans(spans):
    out = ""
    for s in spans:
        t = s["text"]
        if out and not out.endswith(" ") and not t.startswith(" "):
            # Adjacent spans with a visible horizontal gap are separate words.
            prev = spans[spans.index(s) - 1]
            if s["bbox"][0] - prev["bbox"][2] > 1.5:
                out += " "
        out += t
    return re.sub(r"\s+", " ", out).strip()


# --------------------------------------------------------------------------
# 2. Build entries
# --------------------------------------------------------------------------

def is_category_heading(line):
    s = line["spans"][0]
    return ("Bold" in s["font"] and s["size"] > 10
            and re.fullmatch(r"[A-V]", s["text"].strip()) is not None)


def is_code_line(line):
    s = line["spans"][0]
    return (line["x"] < CODE_X_MAX and not line["is_bullet"]
            and re.fullmatch(r"\d{2,5}", s["text"].strip()) is not None
            and "Bold" not in s["font"] and len(line["spans"]) > 1)


def build_entries(lines):
    entries, current = [], None
    in_title, last_y1, last_page = False, None, None

    def start(code, title, page, y1):
        nonlocal current, in_title, last_y1, last_page
        current = {"code": code, "title": title, "pages": {page}, "blocks": []}
        entries.append(current)
        in_title, last_y1, last_page = True, y1, page

    for line in lines:
        if is_category_heading(line):
            start(line["spans"][0]["text"].strip(), join_spans(line["spans"][1:]),
                  line["page"], line["y1"])
            continue
        if is_code_line(line):
            start(line["spans"][0]["text"].strip(), join_spans(line["spans"][1:]),
                  line["page"], line["y1"])
            continue
        if current is None:
            continue

        same_page = line["page"] == last_page
        gap = line["y0"] - last_y1 if same_page else None

        if in_title and same_page and gap < TITLE_LINE_GAP and not line["is_bullet"] \
                and line["text"] == line["text"].upper():
            current["title"] += " " + line["text"]
        else:
            in_title = False
            current["pages"].add(line["page"])
            blocks = current["blocks"]
            if line["is_bullet"]:
                blocks.append({"type": "bullet", "text": line["text"]})
            elif blocks and (gap is None or gap < PARAGRAPH_GAP) \
                    and not (blocks[-1]["type"] == "bullet" and line["x"] < 125):
                # Continuation of the previous paragraph/bullet (also across pages).
                blocks[-1]["text"] = join_text(blocks[-1]["text"], line["text"])
            else:
                blocks.append({"type": "para", "text": line["text"]})
        last_y1, last_page = line["y1"], line["page"]

    return entries


def join_text(a, b):
    # Keep hyphenated compounds split across lines intact ("buah-" + "buahan").
    if a.endswith("-") and not a.endswith(" -"):
        return a + b
    return a + " " + b


# --------------------------------------------------------------------------
# 3. Structure each entry (sections, references, seeChild)
# --------------------------------------------------------------------------

# The book's own section markers. Only these exact phrases are used; other
# wording ("tidak termasuk di sini") stays in `description` only, so the
# split never goes beyond what the text literally says.
MARKER_RE = re.compile(r"\b(tidak\s+mencakup|juga\s+mencakup|mencakup)\b", re.IGNORECASE)
SECTION_KEY = {"mencakup": "includes", "juga mencakup": "alsoIncludes", "tidak mencakup": "excludes"}

REF_RE = re.compile(
    rf"\b{LEVEL_WORDS}\s+((?:[A-V]|\d{{2,5}})(?:\s*(?:,|dan|atau|s\.?d\.?|sampai dengan|-|–)\s*(?:[A-V]|\d{{2,5}}))*)",
    re.IGNORECASE,
)


def split_sentences(text):
    return [s for s in re.split(r"(?<=[.;])\s+(?=[A-Z])", text) if s]


def sentence_sections(sentence):
    """Sections named by the markers in a sentence, in order of appearance."""
    return [SECTION_KEY[re.sub(r"\s+", " ", m.group(1).lower())] for m in MARKER_RE.finditer(sentence)]


def structure(entry):
    """Split an entry's blocks into the book's sections.

    - A prose sentence goes into the section(s) its own marker names;
      sentences without a marker stay in `description` only.
    - A bullet belongs to the last marker of the paragraph right above its
      list ("Kelompok ini tidak mencakup" -> excludes). A list under a
      paragraph with no marker stays in `description` only.
    - A marker sentence with no content of its own (a list heading such as
      "Subgolongan ini mencakup") is not added as an item.
    """
    sections = {"includes": [], "alsoIncludes": [], "excludes": []}
    references = []
    active = None
    desc_parts = []

    for block in entry["blocks"]:
        text = block["text"]
        if block["type"] == "bullet":
            desc_parts.append("- " + text)
            if active:
                sections[active].append(text)
            add_refs(references, text, active or "description")
            continue

        desc_parts.append(text)
        active = None
        for sentence in split_sentences(text):
            sentence = sentence.strip()
            kinds = sentence_sections(sentence)
            is_heading = re.search(r"mencakup\s*:?\s*$", sentence, re.IGNORECASE)
            if kinds:
                active = kinds[-1]
                if not is_heading:
                    for kind in dict.fromkeys(kinds):
                        sections[kind].append(sentence)
            add_refs(references, sentence, kinds[-1] if kinds else "description")

    description = "\n".join(desc_parts)
    see = re.fullmatch(r"Lihat\s+(?:kelompok|subgolongan|golongan)\s+(\d{3,5})\.?", description.strip(),
                       re.IGNORECASE)
    return {
        "description": description,
        **sections,
        "references": references,
        "seeChild": see.group(1) if see else None,
    }


def add_refs(references, text, section):
    for m in REF_RE.finditer(text):
        codes = re.findall(r"\b(?:[A-V]|\d{2,5})\b", m.group(2))
        for code in codes:
            ref = {"code": code, "section": section, "text": text.strip()}
            if ref not in references:
                references.append(ref)


# --------------------------------------------------------------------------
# 4. Finalize, validate, write
# --------------------------------------------------------------------------

def level_of(code):
    return 1 if code.isalpha() else len(code)


def finalize(raw):
    entries, category = [], None
    for r in raw:
        lvl = level_of(r["code"])
        if lvl == 1:
            category = r["code"]
            parent = None
        elif lvl == 2:
            parent = category
        else:
            parent = r["code"][:-1]
        pages = sorted(r["pages"])
        entries.append({
            "code": r["code"],
            "level": LEVELS[lvl],
            "title": re.sub(r"\s+", " ", r["title"]).strip(),
            "parent": parent,
            "children": [],
            **structure(r),
            "source": {"pdfPages": pages, "printedPages": [p - PRINTED_OFFSET for p in pages]},
        })
    by_code = {}
    for e in entries:
        by_code.setdefault(e["code"], e)
    for e in entries:
        if e["parent"] in by_code:
            by_code[e["parent"]]["children"].append(e["code"])
    # "Lihat kelompok X" may point to a grandchild (291 -> 29100). A pointer
    # that isn't a real descendant (a typo in the book) is dropped here and
    # reported; the verbatim sentence stays in `description`.
    for e in entries:
        target = e["seeChild"]
        if target and not (target in by_code and target != e["code"]
                           and is_descendant(by_code[target], e["code"], by_code)):
            e["badSeeChild"] = target
            e["seeChild"] = None
    return entries


def is_descendant(node, ancestor_code, by_code):
    while node["parent"]:
        if node["parent"] == ancestor_code:
            return True
        node = by_code.get(node["parent"], {"parent": None})
    return False


def validate(entries):
    errors, warnings = [], []
    codes = [e["code"] for e in entries]
    by_code = {}
    for e in entries:
        if e["code"] in by_code:
            errors.append(f"Duplicate code {e['code']} (pages {e['source']['pdfPages']})")
        by_code[e["code"]] = e

    cats = [e for e in entries if e["level"] == "kategori"]
    if len(cats) != 22:
        errors.append(f"Expected 22 kategori, found {len(cats)}: {[c['code'] for c in cats]}")

    for e in entries:
        p = e["parent"]
        if e["level"] != "kategori":
            if p not in by_code:
                errors.append(f"{e['code']}: parent {p} does not exist")
            elif e["level"] != "golonganPokok" and not e["code"].startswith(p):
                errors.append(f"{e['code']}: does not start with parent {p}")
        for c in e["children"]:
            if c not in by_code:
                errors.append(f"{e['code']}: child {c} does not exist")

        where = f"{e['code']} (PDF p. {', '.join(map(str, e['source']['pdfPages']))})"
        if e["title"] != e["title"].upper():
            warnings.append(("Title not fully uppercase", where, e["title"]))
        if not e["description"]:
            warnings.append(("Empty description", where, ""))
        if re.search(r"bps\.go\.id|Klasifikasi Baku Lapangan Usaha Indonesia \(KBLI\) 2025", e["description"]):
            warnings.append(("Page noise in description", where, e["description"][:120]))
        if re.search(r"mencakup", e["description"], re.IGNORECASE) and \
                not (e["includes"] or e["alsoIncludes"] or e["excludes"]):
            warnings.append(("Section marker found but nothing split", where, e["description"][:120]))
        for r in e["references"]:
            if r["code"] not in by_code:
                warnings.append(("Reference to unknown code", where, f"{r['code']}: {r['text'][:120]}"))
        if "badSeeChild" in e:
            warnings.append(("'Lihat …' points to a code that is not below this entry (seeChild left null)",
                             where, f"{e.pop('badSeeChild')}: {e['description']}"))
        if e["level"] in ("subgolongan", "golongan", "golonganPokok", "kategori") and not e["children"]:
            warnings.append(("Non-leaf level has no children", where, ""))
    return errors, warnings


def write_report(path, warnings, counts):
    lines = ["# KBLI 2025 parse — review report", "",
             f"Generated {datetime.date.today().isoformat()} by parse_kbli.py v{PARSER_VERSION}.", "",
             "Counts: " + ", ".join(f"{k} {v}" for k, v in counts.items()), "",
             f"**{len(warnings)} warnings.** Check each against the PDF page listed.", ""]
    by_kind = {}
    for kind, where, detail in warnings:
        by_kind.setdefault(kind, []).append((where, detail))
    for kind, items in by_kind.items():
        lines += [f"## {kind} ({len(items)})", ""]
        lines += [f"- **{w}** — {d}" if d else f"- **{w}**" for w, d in items]
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    doc = fitz.open(pdf_path)
    entries = finalize(build_entries(extract_lines(doc)))
    errors, warnings = validate(entries)

    counts = {lvl: sum(e["level"] == lvl for e in entries) for lvl in LEVELS.values()}
    write_report(HERE / "review_report.md", warnings, counts)

    if errors:
        print(f"{len(errors)} hard errors — JSON not written:", file=sys.stderr)
        for e in errors[:50]:
            print("  " + e, file=sys.stderr)
        sys.exit(1)

    out = {
        "meta": {
            "edition": "KBLI 2025",
            "source": pdf_path.name,
            "publisher": "Badan Pusat Statistik",
            "parserVersion": PARSER_VERSION,
            "generatedAt": datetime.date.today().isoformat(),
            "counts": counts,
        },
        "entries": entries,
    }
    (HERE / "kbli_2025.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(entries)} entries {counts}; {len(warnings)} warnings -> review_report.md")


if __name__ == "__main__":
    main()
