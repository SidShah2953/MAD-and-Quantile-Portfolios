#!/usr/bin/env python3
"""Lightweight PDF QA checks for the paper.

Runs non-visual checks useful for a “publisher pass”:
- PDF outlines/bookmarks present and sane
- Figure/Table caption numbering and basic consistency (text-based heuristics)
- Detect float-only pages (caption present but very little body text)

Usage:
  python Paper/scripts/audit_pdf.py Paper/LaTeX/main.pdf
    python Paper/scripts/audit_pdf.py --pdf Paper/LaTeX/main.pdf
"""

from __future__ import annotations

if __package__ is None or __package__ == "":
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


def _flatten_outlines(outlines: Any, depth: int = 0, acc: list[tuple[int, str]] | None = None) -> list[tuple[int, str]]:
    if acc is None:
        acc = []
    if outlines is None:
        return acc

    for item in outlines:
        if isinstance(item, list):
            _flatten_outlines(item, depth + 1, acc)
            continue

        title = getattr(item, "title", None)
        if title is None and isinstance(item, str):
            title = item
        acc.append((depth, str(title) if title is not None else ""))

    return acc


def _find_gaps(nums: Iterable[int]) -> list[int]:
    nums = sorted(set(nums))
    if not nums:
        return []
    lo, hi = nums[0], nums[-1]
    return [n for n in range(lo, hi + 1) if n not in nums]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path, nargs="?", help="Path to the PDF (positional)")
    parser.add_argument("--pdf", dest="pdf_opt", type=Path, default=None, help="Path to the PDF (flag)")
    parser.add_argument("--tex", type=Path, default=None, help="Optional TeX source to scan for TODO/draft/??")
    parser.add_argument("--short-page-words", type=int, default=60)
    parser.add_argument("--min-image-width", type=int, default=600)
    parser.add_argument("--min-image-height", type=int, default=400)
    args = parser.parse_args()

    pdf_path: Path | None = args.pdf_opt or args.pdf
    if pdf_path is None:
        raise SystemExit("Missing PDF path. Provide a positional argument or use --pdf.")
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")

    # Imports are local so the script fails gracefully if deps are missing.
    from pypdf import PdfReader
    import pdfplumber

    reader = PdfReader(str(pdf_path))

    outlines = None
    try:
        outlines = reader.outline
    except Exception:
        try:
            outlines = reader.outlines
        except Exception:
            outlines = None

    flat = _flatten_outlines(outlines)

    print(f"PDF: {pdf_path}")
    try:
        size_mb = pdf_path.stat().st_size / 1024 / 1024
        print(f"File size: {size_mb:.2f} MB")
    except Exception:
        pass
    print(f"Pages: {len(reader.pages)}")
    print(f"Bookmarks: {len(flat)}")

    # ---- Metadata and page size sanity ----
    meta = reader.metadata or {}
    meta_keys = ["/Title", "/Author", "/Creator", "/Producer", "/CreationDate", "/ModDate"]
    present = {k: str(meta.get(k)) for k in meta_keys if meta.get(k)}
    if present:
        print("\nMetadata (present fields):")
        for k, v in present.items():
            print(f"  {k}: {v}")

    sizes = Counter()
    for p in reader.pages:
        mb = p.mediabox
        w_pt = float(mb.width)
        h_pt = float(mb.height)
        sizes[(round(w_pt, 2), round(h_pt, 2))] += 1
    print("\nPage sizes (points and inches):")
    for (w_pt, h_pt), count in sizes.items():
        w_in, h_in = w_pt / 72.0, h_pt / 72.0
        print(f"  {count} pages: {w_pt} x {h_pt} pt ({w_in:.2f} x {h_in:.2f} in)")
    if flat:
        print(f"Max bookmark depth: {max(d for d, _ in flat)}")
        print("\nBookmark preview (first 40):")
        for depth, title in flat[:40]:
            ind = "  " * depth
            print(f"  {ind}{title or '<EMPTY>'}")

    suspicious = [(d, t) for d, t in flat if (not t.strip()) or re.search(r"\?\?|undefined", t, re.I)]
    if suspicious:
        print("\nSuspicious bookmark titles (review):")
        for d, t in suspicious[:50]:
            print("  " + "  " * d + repr(t))

    # ---- Text extraction and caption heuristics ----
    # Some PDF text extractors may drop the space between the label and number (e.g., "Table2").
    fig_re = re.compile(r"\bFigure\s*(\d+)\b")
    tab_re = re.compile(r"\bTable\s*(\d+)\b")

    # Caption heuristics:
    # 1) Many caption styles render "Figure 1:" / "Table 2.".
    # 2) Some styles omit punctuation; in that case captions usually occur very early on the page.
    fig_cap_punct_re = re.compile(r"\bFigure\s*(\d+)\s*[:\.]" )
    tab_cap_punct_re = re.compile(r"\bTable\s*(\d+)\s*[:\.]" )
    fig_cap_early_re = re.compile(r"\bFigure\s*(\d+)\b")
    tab_cap_early_re = re.compile(r"\bTable\s*(\d+)\b")

    fig_mentions: dict[int, set[int]] = defaultdict(set)
    tab_mentions: dict[int, set[int]] = defaultdict(set)
    fig_caps: dict[int, set[int]] = defaultdict(set)
    tab_caps: dict[int, set[int]] = defaultdict(set)

    page_texts: list[str] = []

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = re.sub(r"\s+", " ", text).strip()
            page_texts.append(text)

            for m in fig_re.finditer(text):
                fig_mentions[int(m.group(1))].add(page_num)
            for m in tab_re.finditer(text):
                tab_mentions[int(m.group(1))].add(page_num)

            # Punctuation-based caption detection.
            for m in fig_cap_punct_re.finditer(text):
                fig_caps[int(m.group(1))].add(page_num)
            for m in tab_cap_punct_re.finditer(text):
                tab_caps[int(m.group(1))].add(page_num)

            # Early-on-page fallback caption detection (helps when caption style omits colon/dot).
            early = text[:300]
            for m in fig_cap_early_re.finditer(early):
                fig_caps[int(m.group(1))].add(page_num)
            for m in tab_cap_early_re.finditer(early):
                tab_caps[int(m.group(1))].add(page_num)

    # ---- Placeholder / draft artifact scan ----
    scan_patterns = {
        "double question marks (??)": re.compile(r"\?\?"),
        "TODO/FIXME/XXX": re.compile(r"\b(TODO|FIXME|XXX)\b", re.I),
        "draft": re.compile(r"\bdraft\b", re.I),
    }
    print("\nText artifact scan (PDF-extracted text):")
    for label, rx in scan_patterns.items():
        pages = [i for i, t in enumerate(page_texts, start=1) if rx.search(t)]
        print(f"  {label}: {pages if pages else 'OK'}")

    if args.tex is not None and args.tex.exists():
        tex = args.tex.read_text(encoding="utf-8", errors="replace")
        print("\nText artifact scan (TeX source):")
        for label, rx in scan_patterns.items():
            print(f"  {label}: {'FOUND' if rx.search(tex) else 'OK'}")

    def _print_series(label: str, series: dict[int, set[int]], caps: dict[int, set[int]]) -> None:
        if not series:
            print(f"\n{label}: none detected via text extraction")
            return
        print(f"\n{label} mentions (number -> pages | caption-like pages):")
        for n in sorted(series):
            print(f"  {label[:-1]} {n}: pages {sorted(series[n])} | caption-like {sorted(caps.get(n, set()))}")

    _print_series("Figures", fig_mentions, fig_caps)
    _print_series("Tables", tab_mentions, tab_caps)

    fig_nums = sorted(fig_caps)
    tab_nums = sorted(tab_caps)
    print("\nCaption numbering (caption-like occurrences):")
    print(f"  Figure captions: {fig_nums}")
    print(f"  Figure gaps: {_find_gaps(fig_nums)}")
    print(f"  Table captions: {tab_nums}")
    print(f"  Table gaps: {_find_gaps(tab_nums)}")

    # Float-only / caption-orphan heuristic: caption-like occurrence on a very short-text page.
    def is_short_page(text: str) -> bool:
        return len(text.split()) < args.short_page_words

    caption_pages: set[int] = set()
    for pages in fig_caps.values():
        caption_pages |= pages
    for pages in tab_caps.values():
        caption_pages |= pages

    short_caption_pages = sorted(p for p in caption_pages if is_short_page(page_texts[p - 1]))
    if short_caption_pages:
        print("\nPages with a Figure/Table caption but little other text (often float-only pages; visually verify):")
        print("  " + ", ".join(map(str, short_caption_pages)))

    # ---- Link annotation sanity ----
    link_annots = 0
    uri_actions = 0
    for p in reader.pages:
        annots = p.get("/Annots")
        if not annots:
            continue
        try:
            annots = annots.get_object()
        except Exception:
            pass
        for a in annots or []:
            try:
                obj = a.get_object()
            except Exception:
                continue
            if obj.get("/Subtype") == "/Link":
                link_annots += 1
            action = obj.get("/A")
            if action and action.get("/S") == "/URI" and action.get("/URI"):
                uri_actions += 1
    print("\nLinks:")
    print(f"  Link annotations: {link_annots}")
    print(f"  URI actions: {uri_actions}")

    # ---- Fonts (embedding heuristic) ----
    # This is a heuristic: it checks for FontFile/FontFile2/FontFile3 in the FontDescriptor.
    font_embedded = Counter()
    seen_fonts: set[str] = set()
    for p in reader.pages:
        res = p.get("/Resources") or {}
        try:
            res = res.get_object()
        except Exception:
            pass
        font_dict = res.get("/Font") or {}
        try:
            font_dict = font_dict.get_object()
        except Exception:
            pass
        for _, fref in font_dict.items():
            try:
                fobj = fref.get_object()
            except Exception:
                continue
            base = str(fobj.get("/BaseFont") or "")
            if base:
                seen_fonts.add(base)
            fd = fobj.get("/FontDescriptor")
            embedded = None
            if fd:
                try:
                    fdobj = fd.get_object()
                    embedded = any(k in fdobj for k in ["/FontFile", "/FontFile2", "/FontFile3"])
                except Exception:
                    embedded = None
            if embedded is True:
                font_embedded["embedded"] += 1
            elif embedded is False:
                font_embedded["not_embedded"] += 1
            else:
                font_embedded["unknown"] += 1
    print("\nFonts (heuristic):")
    print(f"  Unique BaseFonts: {len(seen_fonts)}")
    print(f"  Font descriptor embedding status (per-page font entries): {dict(font_embedded)}")

    # ---- Images (resolution proxy via pixel dimensions) ----
    img_sizes = Counter()
    small_images: list[tuple[int, int, int]] = []
    for page_idx, p in enumerate(reader.pages, start=1):
        res = p.get("/Resources") or {}
        try:
            res = res.get_object()
        except Exception:
            pass
        xobj = res.get("/XObject")
        if not xobj:
            continue
        try:
            xobj = xobj.get_object()
        except Exception:
            continue
        for _, oref in xobj.items():
            try:
                o = oref.get_object()
            except Exception:
                continue
            if o.get("/Subtype") != "/Image":
                continue
            w = int(o.get("/Width", 0) or 0)
            h = int(o.get("/Height", 0) or 0)
            if not (w and h):
                continue
            img_sizes[(w, h)] += 1
            if w < args.min_image_width or h < args.min_image_height:
                small_images.append((page_idx, w, h))

    if img_sizes:
        print("\nImages (pixel sizes; proxy for resolution):")
        for (w, h), count in img_sizes.most_common(10):
            print(f"  {count}x: {w} x {h}")
        if small_images:
            print("  Potentially low-res images (heuristic; visually verify):")
            for page_idx, w, h in small_images[:25]:
                print(f"    page {page_idx}: {w} x {h}")
    else:
        print("\nImages: none detected via XObject scan (unexpected for figure-heavy PDFs).")

    # Basic section existence checks
    refs_pages = [i for i, t in enumerate(page_texts, start=1) if re.search(r"\bReferences\b", t)]
    if refs_pages:
        print(f"\nReferences heading detected on pages: {refs_pages}")
    else:
        print("\nReferences heading not detected via text extraction (may be a font/extraction limitation).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
