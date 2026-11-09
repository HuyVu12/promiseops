"""Fills the challenge's AI Journal template for team NgaChainAILayer2.

Usage: python scripts/fill_ai_journal.py "<AI JOURNAL TEMPLATE.docx>" "<out.docx>"
The template is unpacked to a temporary folder, filled and repacked. Export to PDF from Word.
The content describes what happened in the Round 2 build; the team reviews and edits it before submitting.
"""

from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SDT_TEXT = [
    # Team name, AI tools
    "NgaChainAILayer2",
    "Claude Code (Claude Opus 5.5) as pair engineer and as a separate strict reviewer; its add-ons for UI critique, "
    "landing-page design and browser testing. Playwright for the automated browser test and the screenshots we "
    "reviewed. GitHub CLI for the repository. Microsoft Word to export this journal.",
    # AI strategy (max 150 words)
    "We used AI as a fast pair engineer and as a strict reviewer, never as the decision maker. Every change had to "
    "trace back to our Round 1 proposal: AI read the Round 2 brief and our deck and proposed a narrow MVP (one Swedish "
    "DC, two rules, one end-to-end journey); we chose the stack, the rule of no AI inside the product, the visual "
    "direction and the Vietnamese option. AI wrote code together with tests, and we only accepted what we could check: "
    "38 automated tests, including a real-browser run of the journey, and screenshots of every screen. Before "
    "submitting we ran a separate AI review told to be strict. It found real gaps, such as an on-time KPI that ignored "
    "overdue orders and journey times that did not match the activity log; we fixed them and added tests. "
    "Documents are generated from the running app.",
    # Reflection 1-4
    "In the build-and-check loop. AI turned our Round 1 rules into working code with tests within hours, and its "
    "browser screenshots let us review every state in both languages without clicking through each one. It was also "
    "useful as a second pair of eyes: the strict review found mismatches between our documents and the app that we "
    "had stopped noticing.",
    "We rejected automatically laid-out C4 diagrams because labels overlapped and lines crossed boxes; they are now "
    "laid out by hand from the code structure. We rejected the first stale-data rule after it produced false alarms. "
    "We declined an AI summary feature, and we changed AI's first KPI definitions, which made the demo look better "
    "than an honest measure would (for example, counting false alarms as orders saved).",
    "Keeping AI out of the product was a business decision: Round 1 asked Company A to fund explainable rules first. "
    "Decision rights (only the shift lead may expedite), the promise that can never be edited, showing EUR 25 only as "
    "a Round 1 assumption, and what the demo is allowed to claim were our calls. We also decided which review "
    "findings to fix and which to leave.",
    "AI sometimes declared work finished while the rendered screen still had overlaps or a misleading number, so "
    "screenshot review became mandatory. It writes plausible but unverified claims, so we checked every sentence in "
    "the documents against the code and the running app. Long sessions lose context, so we kept a short written "
    "product brief that every session read first.",
]

LOG_ROWS = [
    ("Scoping", "Read the Round 2 brief and our Round 1 deck; propose a narrow MVP scope and stack",
     "1 day", "3 h", "We chose the stack and 'no AI in the product'; scope checked against Round 1 slides 4-8",
     "One DC, two rules, one journey; FastAPI + SQLite"),
    ("Build", "Implement source adapter, rules, escalation, workflow, KPIs and demo harness, with tests",
     "4 days", "1 day", "A test per rule; demo run end to end against Round 1 slide 4",
     "Working MVP; stale-feed bug (9 false alarms) fixed at the root"),
    ("UI and language", "Generate UI options, build the timetable view, add English and Vietnamese",
     "3 days", "1 day", "We picked the direction from real screens; Vietnamese checked by the team",
     "Timetable UI; English and Vietnamese"),
    ("Documents", "Build the system diagram and the user journey from the running app",
     "1.5 days", "4 h", "Rejected overlapping auto-layouts; every arrow checked against code",
     "Two 2-page PDFs, times from the app"),
    ("Review and hardening", "Strict AI review of the whole submission, then fixes and a refactor",
     "2 days", "5 h", "We triaged each finding; re-ran 38 tests and the demo",
     "Overdue counts as late; cost log; scorecard; refactor"),
]

DECISIONS = [
    ("Data freshness guard",
     "First version: pause alerts only when the warehouse feed is older than 30 minutes.",
     "Screenshots of an outage showed 9 false alarms at minute 30. We asked for a root-cause rule: a missing event "
     "only counts if the feed was read after the milestone. Tests cover both cases."),
    ("Honest outcome measurement",
     "The strict review showed Outcomes at 100% on time at 14:30 while SE-1077 was past its 14:00 promise and not delivered.",
     "We changed the rule: an order past its promise without a delivery is overdue and counts as late. Percentages "
     "from fewer than 10 cases are no longer marked on or below target."),
    ("AI inside the product",
     "Offered an optional AI case summary and an ML late-risk score.",
     "We kept the product rules-only, as Round 1 argued, and made every closed exception a labelled example "
     "(GET /api/outcomes) for the risk model planned after Gate 2."),
]


def run(text: str, size: int = 18) -> str:
    return (f'<w:r><w:rPr><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
            f'<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')


def fill_sdts(xml: str) -> str:
    sdts = list(re.finditer(r"<w:sdt>.*?</w:sdt>", xml, re.S))
    assert len(sdts) == len(SDT_TEXT), (len(sdts), len(SDT_TEXT))
    out, pos = [], 0
    for m, text in zip(sdts, SDT_TEXT):
        s = m.group(0)
        s = s.replace("<w:showingPlcHdr/>", "")
        s = re.sub(r'<w:rStyle w:val="PlaceholderText"/>', "", s)
        s = s.replace("Click or tap here to enter text.", escape(text))
        out.append(xml[pos:m.start()])
        out.append(s)
        pos = m.end()
    out.append(xml[pos:])
    return "".join(out)


# Paragraph properties that come after <w:spacing> in the schema order of <w:pPr> (ECMA-376).
_AFTER_SPACING = ("w:ind", "w:contextualSpacing", "w:mirrorIndents", "w:suppressOverlap", "w:jc",
                  "w:textDirection", "w:textAlignment", "w:textboxTightWrap", "w:outlineLvl", "w:divId",
                  "w:cnfStyle", "w:rPr", "w:sectPr", "w:pPrChange")
CELL_SPACING = '<w:spacing w:before="60" w:after="60" w:line="260" w:lineRule="auto"/>'


def with_row_prop(row: str, prop: str) -> str:
    """Add a row property (<w:tblHeader/>, <w:cantSplit/>) to <w:trPr>, creating it in schema order."""
    tag = prop.split()[0].rstrip("/>")
    if tag in row:
        return row
    m = re.search(r"<w:trPr>", row)
    if m:
        return row[:m.end()] + prop + row[m.end():]
    head = re.match(r"<w:tr(?: [^>]*)?>(?:<w:tblPrEx>.*?</w:tblPrEx>)?", row, re.S)
    return row[:head.end()] + f"<w:trPr>{prop}</w:trPr>" + row[head.end():]


def with_cell_spacing(cell: str) -> str:
    """Give every paragraph in a table cell breathing room above and below."""
    def fix(m: re.Match) -> str:
        para = m.group(0)
        if para.endswith("/>") and "</w:p>" not in para:
            open_tag = para[:-2] + ">"
            return f"{open_tag}<w:pPr>{CELL_SPACING}</w:pPr></w:p>"
        ppr = re.search(r"<w:pPr>(.*?)</w:pPr>", para, re.S)
        if not ppr:
            open_end = para.index(">") + 1
            return para[:open_end] + f"<w:pPr>{CELL_SPACING}</w:pPr>" + para[open_end:]
        inner = re.sub(r"<w:spacing\b[^>]*/>", "", ppr.group(1))
        cut = min([i for i in (inner.find("<" + t) for t in _AFTER_SPACING) if i >= 0], default=len(inner))
        inner = inner[:cut] + CELL_SPACING + inner[cut:]
        return para[:ppr.start(1)] + inner + para[ppr.end(1):]

    return re.sub(r"<w:p(?: [^>]*)?/>|<w:p(?: [^>]*)?>.*?</w:p>", fix, cell, flags=re.S)


def fill_table(xml: str, index: int, rows: list[tuple[str, ...]]) -> str:
    tables = list(re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S))
    t = tables[index]
    tbl = t.group(0)
    trs = list(re.finditer(r"<w:tr[ >].*?</w:tr>", tbl, re.S))
    new_tbl, pos = [], 0
    for ri, tr in enumerate(trs):
        new_tbl.append(tbl[pos:tr.start()])
        row = tr.group(0)
        # The header row repeats on every page; no row is split across a page break.
        row = with_row_prop(row, "<w:tblHeader/>" if ri == 0 else "<w:cantSplit/>")
        if ri >= 1 and ri - 1 < len(rows):
            values = rows[ri - 1]
            cells = list(re.finditer(r"<w:tc>.*?</w:tc>", row, re.S))
            new_row, cpos = [], 0
            for ci, c in enumerate(cells):
                new_row.append(row[cpos:c.start()])
                cell = c.group(0)
                # put text into the first paragraph of the cell
                selfclosed = re.search(r"<w:p( [^>]*)?/>", cell)
                if selfclosed and (cell.find("</w:p>") == -1 or selfclosed.start() < cell.find("<w:p ") + 1):
                    cell = cell[:selfclosed.start()] + f"<w:p{selfclosed.group(1) or ''}>{run(values[ci])}</w:p>" + cell[selfclosed.end():]
                else:
                    cell = re.sub(r"(<w:p[ >].*?)(</w:p>)", lambda m: m.group(1) + run(values[ci]) + m.group(2), cell, count=1, flags=re.S)
                new_row.append(with_cell_spacing(cell))
                cpos = c.end()
            new_row.append(row[cpos:])
            row = "".join(new_row)
        new_tbl.append(row)
        pos = tr.end()
    new_tbl.append(tbl[pos:])
    return xml[:t.start()] + "".join(new_tbl) + xml[t.end():]


def main() -> None:
    template, out = Path(sys.argv[1]), Path(sys.argv[2])
    root = Path(tempfile.mkdtemp(prefix="journal-"))
    with zipfile.ZipFile(template) as z:
        z.extractall(root)
    doc = root / "word" / "document.xml"
    xml = doc.read_text(encoding="utf8")
    xml = fill_sdts(xml)
    xml = xml.replace('<w:rPr><w:color w:val="FF0000"/></w:rPr><w:t>English preferred</w:t>', '<w:t>English</w:t>')
    xml = xml.replace(">English preferred<", ">English<")
    xml = fill_table(xml, 1, LOG_ROWS)
    xml = fill_table(xml, 2, DECISIONS)
    doc.write_text(xml, encoding="utf8")
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(root.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(root).as_posix())
    words = len(SDT_TEXT[2].split())
    if words > 150:
        raise SystemExit(f"AI strategy has {words} words; the template allows 150")
    print(out, "strategy words:", words)


if __name__ == "__main__":
    main()
