#!/usr/bin/env python3
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "vpn_service_tz.md"
TARGET = ROOT / "docs" / "vpn_service_tz.html"


def inline(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(
        r"(?<![\"'=])(https?://[^\s<]+)",
        r'<a href="\1">\1</a>',
        text,
    )
    return text


def tag(name: str, content: str, cls: str = "") -> str:
    attr = f' class="{cls}"' if cls else ""
    return f"<{name}{attr}>{content}</{name}>"


def box(text: str, cls: str = "") -> str:
    cls = f"box {cls}".strip()
    return f'<div class="{cls}">{inline(text)}</div>'


def arrow(label: str = "") -> str:
    label_html = f"<span>{inline(label)}</span>" if label else ""
    return f'<div class="arrow">→{label_html}</div>'


def flow_product() -> str:
    return """
<section class="diagram">
  <div class="diagram-title">Схема продукта</div>
  <div class="flow-row">
    <div class="flow-col">""" + box("Admin", "accent") + """</div>
    """ + arrow() + """
    <div class="flow-col">""" + box("Control Panel") + """</div>
    """ + arrow() + """
    <div class="flow-col">""" + box("Customer Account", "accent") + """</div>
  </div>
  <div class="split-grid">
    <div class="split-left">
      """ + box("Dedicated VPN Server", "server") + """
    </div>
    <div class="split-right">
      """ + box("20 Device Slots") + """
      <div class="down-arrow">↓</div>
      """ + box("One-time Invite Links", "accent") + """
      <div class="profile-grid">
        """ + box("Apple Profile") + """
        """ + box("Android Profile") + """
        """ + box("Windows Package") + """
      </div>
    </div>
  </div>
</section>
"""


def sequence_mvp() -> str:
    rows = [
        ("Admin", "Control Panel", "Create customer"),
        ("Admin", "VPS Provider", "Create VPS manually"),
        ("Admin", "Control Panel", "Add server IP and region"),
        ("Control Panel", "Customer VPN Server", "Run provisioning"),
        ("Customer VPN Server", "Control Panel", "Provisioning OK"),
        ("Control Panel", "Customer", "Customer cabinet is ready"),
        ("Customer", "Control Panel", "Create invite link"),
        ("Control Panel", "Customer", "One-time invite URL"),
        ("Customer", "Device User", "Send invite URL"),
        ("Device User", "Control Panel", "Open invite URL"),
        ("Control Panel", "Control Panel", "Check slot limit and token status"),
        ("Control Panel", "Control Panel", "Issue certificate and profile"),
        ("Control Panel", "Device User", "Download profile package"),
        ("Device User", "Customer VPN Server", "Connect VPN"),
        ("Customer VPN Server", "Control Panel", "Metrics and last seen"),
    ]
    body = []
    for i, (src, dst, action) in enumerate(rows, 1):
        body.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{inline(src)}</td>"
            f"<td>{inline(action)}</td>"
            f"<td>{inline(dst)}</td>"
            "</tr>"
        )
    return """
<section class="diagram">
  <div class="diagram-title">Основной сценарий MVP</div>
  <table class="sequence">
    <thead><tr><th>#</th><th>Источник</th><th>Действие</th><th>Получатель</th></tr></thead>
    <tbody>""" + "".join(body) + """</tbody>
  </table>
</section>
"""


def flow_architecture() -> str:
    return """
<section class="diagram">
  <div class="diagram-title">Product architecture</div>
  <div class="flow-row two-start">
    <div class="flow-col">""" + box("Customer Portal", "accent") + """</div>
    <div class="flow-col">""" + box("Admin Panel", "accent") + """</div>
  </div>
  <div class="down-arrow">↓</div>
  <div class="centered">""" + box("API Gateway") + """</div>
  <div class="down-arrow">↓</div>
  <div class="centered">""" + box("Backend Service", "accent") + """</div>
  <div class="architecture-grid">
    """ + box("PostgreSQL") + """
    """ + box("Redis Queue") + """
    """ + box("Metrics Service") + """
  </div>
  <div class="architecture-grid">
    """ + box("Provisioning Worker") + """
    """ + box("PKI Worker") + """
    """ + box("Package Worker") + """
  </div>
  <div class="architecture-grid">
    """ + box("VPS Provider", "server") + """
    """ + box("Certificate Authority", "server") + """
    """ + box("Temporary Package Storage", "server") + """
  </div>
  <div class="down-arrow">↓</div>
  <div class="centered">""" + box("Customer VPN Servers", "server") + """</div>
</section>
"""


def render_mermaid(source: str) -> str:
    if "Admin" in source and "20 Device Slots" in source:
        return flow_product()
    if source.strip().startswith("sequenceDiagram"):
        return sequence_mvp()
    if "Customer Portal" in source and "PKI Worker" in source:
        return flow_architecture()
    return "<pre class=\"diagram-code\"><code>" + html.escape(source) + "</code></pre>"


def parse_table(lines: list[str], start: int) -> tuple[str, int]:
    table_lines = []
    i = start
    while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
        table_lines.append(lines[i].strip())
        i += 1
    header = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = table_lines[2:]
    out = ["<table>", "<thead><tr>"]
    for cell in header:
        out.append(f"<th>{inline(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        for cell in [c.strip() for c in row.strip("|").split("|")]:
            out.append(f"<td>{inline(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out), i


def markdown_to_html(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_type: str | None = None
    i = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append("<p>" + inline(" ".join(paragraph)) + "</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            close_list()
            lang = stripped[3:].strip()
            block: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            code = "\n".join(block)
            if lang == "mermaid":
                out.append(render_mermaid(code))
            else:
                out.append(
                    f'<pre class="code"><code>{html.escape(code)}</code></pre>'
                )
            continue

        if not stripped:
            flush_paragraph()
            close_list()
            i += 1
            continue

        if stripped == "---":
            flush_paragraph()
            close_list()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            flush_paragraph()
            close_list()
            table_html, i = parse_table(lines, i)
            out.append(table_html)
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        bullet = re.match(r"^-\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            if list_type != "ul":
                close_list()
                out.append("<ul>")
                list_type = "ul"
            out.append(f"<li>{inline(bullet.group(1))}</li>")
            i += 1
            continue

        ordered = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ordered:
            flush_paragraph()
            if list_type != "ol":
                close_list()
                out.append("<ol>")
                list_type = "ol"
            out.append(f"<li>{inline(ordered.group(1))}</li>")
            i += 1
            continue

        close_list()
        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    close_list()
    return "\n".join(out)


CSS = """
:root {
  --ink: #15181d;
  --muted: #5d6878;
  --line: #d7dde8;
  --soft: #f5f7fb;
  --soft-2: #eef3f8;
  --accent: #1b6f8f;
  --accent-2: #0b4f6c;
  --server: #244833;
}

@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: white;
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
}

main {
  max-width: 980px;
  margin: 0 auto;
}

h1 {
  margin: 0 0 22px;
  padding: 26px 0 20px;
  border-bottom: 3px solid var(--accent);
  color: #0d2634;
  font-size: 28pt;
  line-height: 1.08;
  letter-spacing: -0.02em;
}

h2 {
  break-after: avoid;
  margin: 28px 0 10px;
  padding-top: 8px;
  border-top: 1px solid var(--line);
  color: #102a3a;
  font-size: 17pt;
  line-height: 1.2;
}

h3 {
  break-after: avoid;
  margin: 18px 0 8px;
  color: #163b4c;
  font-size: 12.5pt;
  line-height: 1.3;
}

p {
  margin: 7px 0;
}

ul, ol {
  margin: 7px 0 12px 20px;
  padding: 0;
}

li {
  margin: 3px 0;
}

code {
  padding: 1px 4px;
  border-radius: 4px;
  background: #eef2f5;
  color: #24323b;
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 0.92em;
}

a {
  color: var(--accent-2);
  text-decoration: none;
}

hr {
  margin: 18px 0;
  border: 0;
  border-top: 1px solid var(--line);
}

table {
  width: 100%;
  margin: 10px 0 16px;
  border-collapse: collapse;
  break-inside: avoid;
  font-size: 9.4pt;
}

th {
  background: #eaf0f6;
  color: #122b3a;
  font-weight: 700;
}

th, td {
  padding: 7px 8px;
  border: 1px solid var(--line);
  vertical-align: top;
}

tbody tr:nth-child(even) td {
  background: #fafbfd;
}

.code, .diagram-code {
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #f5f7f9;
  white-space: pre-wrap;
  break-inside: avoid;
}

.diagram {
  margin: 16px 0 22px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbfd 0%, #ffffff 100%);
  break-inside: avoid;
}

.diagram-title {
  margin-bottom: 12px;
  color: var(--accent-2);
  font-weight: 800;
  font-size: 11pt;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.flow-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin: 8px 0 16px;
}

.flow-col {
  flex: 0 1 190px;
}

.two-start {
  gap: 28px;
}

.box {
  min-height: 44px;
  padding: 12px 14px;
  border: 1px solid #b9c8d6;
  border-radius: 12px;
  background: white;
  color: #15242d;
  text-align: center;
  font-weight: 700;
  box-shadow: 0 4px 12px rgba(28, 53, 75, 0.07);
}

.box.accent {
  border-color: #91bbcf;
  background: #e9f5f9;
  color: #0c4a63;
}

.box.server {
  border-color: #9eb8a8;
  background: #eef7f0;
  color: #244833;
}

.arrow {
  min-width: 24px;
  color: var(--accent);
  text-align: center;
  font-weight: 900;
  font-size: 16pt;
}

.arrow span {
  display: block;
  font-size: 7.5pt;
  font-weight: 600;
}

.down-arrow {
  margin: 6px 0;
  color: var(--accent);
  text-align: center;
  font-weight: 900;
  font-size: 16pt;
}

.split-grid {
  display: grid;
  grid-template-columns: 1fr 1.6fr;
  gap: 18px;
  align-items: center;
}

.split-left {
  display: flex;
  align-items: center;
  justify-content: center;
}

.split-right {
  padding: 8px;
  border-left: 2px dashed #c8d4df;
}

.profile-grid,
.architecture-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 10px;
}

.centered {
  max-width: 360px;
  margin: 0 auto;
}

.sequence {
  font-size: 8.8pt;
}

.sequence th:nth-child(1),
.sequence td:nth-child(1) {
  width: 36px;
  text-align: center;
}

@media print {
  h1, h2, h3, table, .diagram {
    break-inside: avoid;
  }
}
"""


def main() -> None:
    body = markdown_to_html(SOURCE.read_text(encoding="utf-8"))
    html_doc = f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Техническое задание: персональный VPN-сервис</title>
  <style>{CSS}</style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""
    TARGET.write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
