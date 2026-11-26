"""Build both reading editions from one Markdown manuscript (Pandoc, python-docx and LibreOffice)."""
from pathlib import Path
import re
import subprocess
import tempfile

from docx import Document
from docx.shared import Mm, Pt, RGBColor
import shutil

edition = Path(__file__).resolve().parent
docs = edition.parent
parts = [docs / f"sprint-{i}" for i in range(1, 7)]
chapters = [path for part in parts for path in sorted(part.glob("[0-9]*.md"))]
if len(chapters) != 24:
    raise ValueError("Expected 24 numbered chapters")
sections = [docs / "sprint-12/reader-routes.md", *chapters]
for part in parts:
    sections.extend(sorted(part.glob("templates/*.md")))
for number in (7, 9, 10, 11, 12):
    directory = docs / f"sprint-{number}"
    sections.append(directory / "README.md")
    sections.extend(p for p in sorted(directory.glob("*.md")) if p not in sections)
sections.extend([edition / "case-a-results.md", edition / "review.md"])
anchors = {p: f"section-{n}" for n, p in enumerate(sections, 1)}
web = "https://github.com/RomanMykolaichuk/F6_research_lab/blob/sprint-13-final-edition/"
title = (edition / "README.md").read_text().splitlines()[0][2:]
content = [f'---\ntitle: "{title}"\nlang: uk\nsubtitle: "Навчально-методичний посібник · Редакція 1.0 · 26 листопада 2026"\n---\n', '# Зміст {#contents}']
for path in sections:
    heading = path.read_text().splitlines()[0][2:]
    content.append(f'- [{heading}](#{anchors[path]})')
for path in sections:
    source = path.read_text()
    def link(match):
        url = match[1]
        if "://" in url or url.startswith("#"):
            return match[0]
        target = (path.parent / url).resolve()
        if not target.exists() and target.name not in {"F6_1.0.pdf", "F6_1.0.docx"}:
            raise ValueError(f"Missing link in {path}: {url}")
        dest = "#" + anchors[target] if target in anchors else web + target.relative_to(docs.parent).as_posix()
        return "](" + dest + ")"
    source = re.sub(r"\]\(([^)]+)\)", link, source)
    source = re.sub(r"^# (.+)", lambda m: m[0] + " {#" + anchors[path] + "}", source, count=1)
    source = re.sub(r"```mermaid.*?```", "Практична проблема → огляд і прогалина → наукова задача → часткові задачі → результати → докази → висновки та межі. Якщо доказів недостатньо, поверніться до часткових задач.", source, flags=re.S)
    # Ensure Pandoc recognizes tables and lists adjacent to prose in source files.
    source = re.sub(r"(?m)^([^\n|#*\-][^\n]*)\n(?=\||- |1\. )", r"\1\n\n", source)
    content.append("\n" + source)

with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)
    manuscript = temp / "manual.md"
    manuscript.write_text("\n".join(content))
    base = ["pandoc", str(manuscript), "-f", "markdown-smart"]
    subprocess.run(base + ["-o", str(edition / "F6_1.0.docx")], check=True)
    word = edition / "F6_1.0.docx"
    document = Document(word)
    section = document.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin, section.right_margin = Mm(20), Mm(18)
    section.top_margin, section.bottom_margin = Mm(19), Mm(18)
    for name in ("Normal", "Body Text", "First Paragraph"):
        style = document.styles[name]
        style.font.name, style.font.size = "DejaVu Sans", Pt(10.5)
    heading = next(s for s in document.styles if s.style_id == "Heading1")
    heading.paragraph_format.page_break_before = True
    heading.font.color.rgb = RGBColor.from_string("245746")
    section.footer.paragraphs[0].text = "F6   ·   Методичний посібник   ·   Редакція 1.0"
    document.save(word)
    subprocess.run([shutil.which("soffice") or "libreoffice",
                    "-env:UserInstallation=" + (temp / "profile").as_uri(),
                    "--headless", "--convert-to", "pdf", "--outdir", str(edition), str(word)], check=True)
