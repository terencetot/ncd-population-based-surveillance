#!/usr/bin/env python3
"""
Generic table extractor for GATS/GYTS WHO fact-sheet PDFs.

The stat table on the second page is laid out in two side-by-side columns.
Each sub-section starts with a header row like "OVERALL (%) BOYS (%) GIRLS (%)"
(GYTS) or "OVERALL (%) MEN (%) WOMEN (%)" (GATS) — but some GATS sub-sections
use different column semantics (e.g. "OVERALL (%) CURRENT SMOKERS (%)
NON-SMOKERS (%)"), so column names are read from the header text itself
rather than assumed.

Approach: pull words with position + font size from the page, drop the small
superscript footnote-reference digits (a different, smaller font size than
body text), split the page into a left half and a right half (two visual
columns), cluster words into rows by y-position within each half, then in
each row split off trailing numeric tokens from the leading label text.
A row whose text matches "<name> (%) <name> (%) ..." becomes the active
header for that half-page until the next header row.
"""
import re

import pdfplumber

NUMERIC_RE = re.compile(r"^(<?\d[\d,]*\.?\d*\*?|--|-)%?$")
HEADER_RE = re.compile(r"([A-Za-z][A-Za-z /,.\-]*?)\s*\(%\)")


def _body_words(page):
    """
    Keep label/data/header text, drop superscript footnote-reference digits
    and the big page/section titles. Fact sheets observed so far: body text
    ~6.9-7pt, column headers ~6pt, superscripts ~4.5-4.6pt, titles 12pt+.
    """
    words = page.extract_words(extra_attrs=["size"])
    return [w for w in words if 5.3 <= w["size"] <= 9.5]


def _cluster_rows(words, y_tol=2.2):
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    rows, cur, cur_top = [], [], None
    for w in words:
        if cur_top is None or abs(w["top"] - cur_top) <= y_tol:
            cur.append(w)
            cur_top = w["top"] if cur_top is None else cur_top
        else:
            rows.append(cur)
            cur, cur_top = [w], w["top"]
    if cur:
        rows.append(cur)
    return rows


def _parse_row(words):
    """Split a row's words into (label, [numbers]) — up to 3 trailing numeric tokens."""
    toks = [w["text"] for w in sorted(words, key=lambda w: w["x0"])]
    nums = []
    while toks and NUMERIC_RE.match(toks[-1]) and len(nums) < 3:
        nums.insert(0, toks.pop())
    label = " ".join(toks).strip(" :-")
    return label, nums


LARGE_GAP = 15.0  # pt: a gap this big is always a new block, whatever the text case


def _group_blocks(lines):
    """
    A single indicator's label often wraps across 2-3 physical lines, with the
    percentage values sitting on whichever line falls at the wrapped label's
    vertical centre. Absolute line-to-line pixel gaps turned out to vary by
    PDF template (a threshold tuned on one country's fact sheet silently
    over-merged distinct one-line indicators in another's), so block
    boundaries are primarily decided by text case: WHO fact-sheet indicator
    labels always start a new sentence with a capital letter, while wrapped
    continuation fragments consistently start lowercase (verified against
    several countries' fact sheets: "prevented from...", "their age", "from
    a store, shop..." all continue a capitalised line above). A large
    absolute gap still forces a break regardless, as a backstop.
    """
    blocks, cur, prev_top = [], [], None
    for row_words in lines:
        top = row_words[0]["top"]
        frag_label, _ = _parse_row(row_words)
        starts_new = not cur
        if not starts_new:
            gap = top - prev_top
            if gap >= LARGE_GAP:
                starts_new = True
            elif frag_label and frag_label[0].isupper():
                starts_new = True
        if starts_new:
            if cur:
                blocks.append(cur)
            cur = []
        cur.append(row_words)
        prev_top = top
    if cur:
        blocks.append(cur)
    return blocks


def extract_stat_rows(pdf_path, page_index=1):
    """
    Returns a list of dicts: {label, cols: [colname,...], values: [num,...]}
    one per data row found on the given page (default: second page, 0-indexed).
    """
    out = []
    with pdfplumber.open(pdf_path) as pdf:
        if page_index >= len(pdf.pages):
            return out
        page = pdf.pages[page_index]
        words = _body_words(page)
        if not words:
            return out
        mid_x = page.width / 2
        for half_words in (
            [w for w in words if w["x0"] < mid_x],
            [w for w in words if w["x0"] >= mid_x],
        ):
            current_cols = None
            for block in _group_blocks(_cluster_rows(half_words)):
                label_parts, nums = [], []
                for row_words in block:
                    frag_label, frag_nums = _parse_row(row_words)
                    if frag_label:
                        label_parts.append(frag_label)
                    if frag_nums:
                        nums = frag_nums
                label = " ".join(label_parts).strip()
                if not label:
                    continue
                header_match = HEADER_RE.findall(label)
                if len(header_match) >= 2 and not nums:
                    current_cols = [h.strip().upper() for h in header_match]
                    continue
                if nums and current_cols:
                    out.append({
                        "label": label,
                        "cols": current_cols[:len(nums)] if len(current_cols) >= len(nums) else current_cols,
                        "values": nums,
                    })
    return out


def _clean_label(label):
    # Strip a lone leading/trailing footnote-ish leftover word fragment is rare
    # once superscripts are filtered by size; just normalise whitespace.
    return re.sub(r"\s+", " ", label).strip()


def _parse_num(tok):
    if tok in ("--", "-"):
        return None
    tok = tok.replace(",", "").rstrip("*").lstrip("<")
    try:
        return float(tok)
    except ValueError:
        return None


def _col_role(col, overall_key, m_key, f_key):
    """
    A column header string may carry a stray section-title prefix picked up
    by the same row-cluster (e.g. "SMOKED TOBACCO OVERALL"), so match the
    wanted key as a whole word anywhere in the string rather than requiring
    an exact match.
    """
    for key, role in ((overall_key, "b"), (m_key, "m"), (f_key, "f")):
        if re.search(r"\b" + re.escape(key) + r"\b", col):
            return role
    return None


def extract_sex_disaggregated(pdf_path, page_index=1, overall_key="OVERALL", m_key="BOYS", f_key="GIRLS"):
    """
    Filter extract_stat_rows() down to rows whose header carries the three
    wanted column roles (overall/male/female) — and return
    {fragment_label: {"b": x, "m": y, "f": z}}.

    `fragment_label` may be a partial/contaminated OCR-of-layout label (a
    multi-line label's continuation, or an adjacent section title picked up
    by the same row cluster) — match it against a canonical indicator
    vocabulary downstream rather than trusting it verbatim.
    """
    rows = extract_stat_rows(pdf_path, page_index)
    result = {}
    for r in rows:
        cols = r["cols"]
        if len(cols) != len(r["values"]):
            continue
        roles = [_col_role(c, overall_key, m_key, f_key) for c in cols]
        if set(roles) != {"b", "m", "f"}:
            continue
        colmap = dict(zip(roles, r["values"]))
        label = _clean_label(r["label"])
        if not label or len(label) < 4:
            continue
        result[label] = {
            "b": _parse_num(colmap.get("b")),
            "m": _parse_num(colmap.get("m")),
            "f": _parse_num(colmap.get("f")),
        }
    return result


if __name__ == "__main__":
    import sys
    import json
    path = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 else "GYTS"
    if kind == "GATS":
        data = extract_sex_disaggregated(path, overall_key="OVERALL", m_key="MEN", f_key="WOMEN")
    else:
        data = extract_sex_disaggregated(path, overall_key="OVERALL", m_key="BOYS", f_key="GIRLS")
    print(json.dumps(data, indent=2, ensure_ascii=False))
