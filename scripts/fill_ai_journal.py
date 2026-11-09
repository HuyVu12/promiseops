"""Fills the AI Journal template (unpacked docx) for team NgaChainAILayer2 and repacks it.

Usage: python fill_ai_journal.py <unpacked_dir> <out.docx>
Content reflects what actually happened in the Round 2 build session; the team should review it.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SDT_TEXT = [
    # Team name, AI tools
    "NgaChainAILayer2",
    "Claude Code (Claude Opus 5.5) as the main pair-engineer, with skills: impeccable (UI critique, polish, design-direction roll), "
    "taste-skill (landing page, palette and type deal), c4-architecture and Mermaid CLI (diagrams), webapp-testing with Playwright "
    "(browser checks and E2E test), docx. GitHub CLI for the repository.",
    # AI strategy (max 150 words)
    "We treated AI as a fast pair-engineer, not as the decision maker. Every technical decision had to trace back to our Round 1 "
    "proposal: AI first read the Round 2 brief and our proposal, then proposed a narrow MVP (one Swedish DC, two exception rules, "
    "one end-to-end journey). The team made the binding choices: stack (FastAPI + SQLite, server-rendered UI), no AI inside the "
    "product, the visual direction, and a Vietnamese language option. AI wrote code together with automated tests (unit, HTTP and "
    "a real-browser E2E test), and we required it to look at real screenshots after every change instead of trusting its own code. "
    "That visual check found a real bug: a paused data feed produced nine false alarms. Diagrams, journey and journal were drafted "
    "by AI from the running app, then checked by us against what the MVP actually does.",
    # Reflection 1-4
    "Speed of the build-test loop. AI turned our Round 1 rules into working code with 22 automated tests in a few hours, and its "
    "browser screenshots let us review layout, wording and both languages without clicking through every state ourselves. It also "
    "generated many design options (11 themes, then 4 direction cards), so we chose from real screens instead of describing a look.",
    "We rejected Mermaid's automatic C4 layout because labels overlapped, and had the diagrams laid out explicitly. We rejected the "
    "first stale-data rule (a 30-minute threshold only) after screenshots showed false alarms, and replaced it with 'a missing event "
    "counts only if the feed was read after the milestone'. We also declined AI's optional idea of an AI summary feature, and asked "
    "for Vietnamese, which the first build did not have.",
    "Keeping AI out of the product was a business judgment: our Round 1 case argued for explainable rules first, and adding AI late "
    "would contradict it. Choosing a stack judges could run with one command, the visual direction, and decision rights (only the "
    "shift lead may expedite; the promise can never be edited) were ours. So was what the demo is allowed to claim: no invented "
    "customers or results, every number labelled as an assumption.",
    "AI sometimes judged its own output as finished when the rendered screen still had overlaps or misleading markers, so we made "
    "screenshot review mandatory. The local sandbox blocked some package installs, which shaped tool choices. AI also tends to make "
    "plausible but unverified claims, so we checked every statement in the documents against the code and the running app.",
]

LOG_ROWS = [
    ("Scoping", "Read the Round 2 brief and our Round 1 proposal; propose a narrow MVP scope and stack",
     "3 h", "20 min", "Team chose the stack and that the product has no AI; scope checked against proposal sections 6-8",
     "One DC, two rules, one journey; FastAPI + SQLite, server-rendered"),
    ("Build", "Implement adapter, rules engine, escalation, workflow, KPI and demo harness with tests",
     "2 days", "2.5 h", "22 automated tests incl. real-browser E2E; team ran the demo locally",
     "Working MVP; stale-feed false-alarm bug found by screenshots and fixed"),
    ("UI design", "Generate and compare UI options; redesign as a timetable; add English/Vietnamese",
     "1.5 days", "3 h", "Team picked the direction (Timetable layout + Orienteering idea) and required Vietnamese; reviewed screens",
     "Timetable UI with NOW line, bilingual, contrast and layout checks passed"),
    ("Architecture docs", "Draft C4 context and component diagrams and the user journey from the running app",
     "6 h", "1 h", "Rejected auto-layout with overlapping labels; checked every arrow is a real MVP interaction",
     "System Diagram.pdf and User Journey.pdf, 2 pages each"),
    ("Landing and journal", "Build the landing page with the taste-skill; draft this journal and the video script",
     "5 h", "1.5 h", "Team reviews copy for claims, edits the journal and records the narration",
     "Landing page at /, journal draft, scene-by-scene video script"),
]

DECISIONS = [
    ("Data freshness guard",
     "First version: stop alerts only when the warehouse feed is older than 30 minutes.",
     "Screenshots of a feed outage showed 9 false alarms at exactly 30 minutes. We asked for a root-cause fix: a missing event only "
     "counts if the feed was read after the milestone. Added tests for both cases."),
    ("AI inside the product",
     "Recommended no AI in the core flow (consistent with Round 1); offered an optional human-approved AI case summary.",
     "We kept the product rules-based and explainable, as argued in Round 1, and kept AI for engineering work only. No API keys in the demo."),
    ("Visual direction",
     "Produced 11 themes, then rolled 4 direction cards (Archipelago Timetable, Departure Board, Orienteering Course, category standard).",
     "We combined the Timetable layout with the Orienteering course idea and asked for a Vietnamese option; AI rebuilt the UI to that brief."),
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


def fill_table(xml: str, index: int, rows: list[tuple[str, ...]]) -> str:
    tables = list(re.finditer(r"<w:tbl>.*?</w:tbl>", xml, re.S))
    t = tables[index]
    tbl = t.group(0)
    trs = list(re.finditer(r"<w:tr[ >].*?</w:tr>", tbl, re.S))
    new_tbl, pos = [], 0
    for ri, tr in enumerate(trs):
        new_tbl.append(tbl[pos:tr.start()])
        row = tr.group(0)
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
                new_row.append(cell)
                cpos = c.end()
            new_row.append(row[cpos:])
            row = "".join(new_row)
        new_tbl.append(row)
        pos = tr.end()
    new_tbl.append(tbl[pos:])
    return xml[:t.start()] + "".join(new_tbl) + xml[t.end():]


def main() -> None:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
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
    print(out, "strategy words:", words)


if __name__ == "__main__":
    main()
