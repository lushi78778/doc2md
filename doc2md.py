#!/usr/bin/env python3
"""Convert local DOCX files to Markdown."""

from __future__ import annotations

import argparse
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

DEFAULT_INPUT_DIR = Path("original")
DEFAULT_OUTPUT_DIR = Path("output")
FULL_WIDTH_INDENT = "\u3000\u3000"

WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": WORD_NS, "m": MATH_NS}

ET.register_namespace("w", WORD_NS)
ET.register_namespace("m", MATH_NS)


def load_conversion_dependencies():
    try:
        import mammoth
        from markdownify import markdownify
    except ImportError as exc:
        raise SystemExit(
            "Missing dependencies.\n"
            "Run:\n"
            "  python3 -m venv .venv\n"
            "  .venv/bin/pip install -r requirements.txt\n"
            "  .venv/bin/python doc2md.py"
        ) from exc

    return mammoth, markdownify


def sanitize_name(name: str, *, ascii_only: bool = False) -> str:
    name = name.strip()
    if ascii_only:
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name)
    else:
        name = re.sub(r'[\\/:*?"<>|\s]+', "-", name)
    return name.strip(".-_") or "document"


def extension_from_content_type(content_type: str) -> str:
    extensions = {
        "image/jpeg": ".jpeg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/tiff": ".tiff",
        "image/bmp": ".bmp",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }
    return extensions.get(content_type, ".png")


def save_mammoth_image(image, assets_dir: Path, image_counter: list[int]) -> dict[str, str]:
    image_counter[0] += 1
    extension = extension_from_content_type(image.content_type)
    filename = f"image-{image_counter[0]:03d}{extension}"

    with image.open() as image_bytes:
        (assets_dir / filename).write_bytes(image_bytes.read())

    return {"src": f"assets/{filename}"}


def qname(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"


def omml_to_markdown(element: ET.Element | None) -> str:
    if element is None:
        return ""

    tag = element.tag
    if tag == qname(MATH_NS, "t"):
        return element.text or ""

    if tag == qname(MATH_NS, "sSub"):
        base = omml_to_markdown(element.find("m:e", NS))
        subscript = omml_to_markdown(element.find("m:sub", NS))
        return f"{base}_{{{subscript}}}"

    if tag == qname(MATH_NS, "sSup"):
        base = omml_to_markdown(element.find("m:e", NS))
        superscript = omml_to_markdown(element.find("m:sup", NS))
        return f"{base}^{{{superscript}}}"

    if tag == qname(MATH_NS, "sSubSup"):
        base = omml_to_markdown(element.find("m:e", NS))
        subscript = omml_to_markdown(element.find("m:sub", NS))
        superscript = omml_to_markdown(element.find("m:sup", NS))
        return f"{base}_{{{subscript}}}^{{{superscript}}}"

    if tag == qname(MATH_NS, "f"):
        numerator = omml_to_markdown(element.find("m:num", NS))
        denominator = omml_to_markdown(element.find("m:den", NS))
        return f"\\frac{{{numerator}}}{{{denominator}}}"

    if tag == qname(MATH_NS, "rad"):
        degree = omml_to_markdown(element.find("m:deg", NS))
        expression = omml_to_markdown(element.find("m:e", NS))
        if degree:
            return f"\\sqrt[{degree}]{{{expression}}}"
        return f"\\sqrt{{{expression}}}"

    if tag == qname(MATH_NS, "d"):
        expression = omml_to_markdown(element.find("m:e", NS))
        return f"({expression})"

    if tag == qname(MATH_NS, "nary"):
        operator = omml_to_markdown(element.find("m:chr", NS)) or "\\sum"
        subscript = omml_to_markdown(element.find("m:sub", NS))
        superscript = omml_to_markdown(element.find("m:sup", NS))
        expression = omml_to_markdown(element.find("m:e", NS))
        limits = ""
        if subscript:
            limits += f"_{{{subscript}}}"
        if superscript:
            limits += f"^{{{superscript}}}"
        return f"{operator}{limits} {expression}".strip()

    return "".join(omml_to_markdown(child) for child in element)


def make_text_run(text: str) -> ET.Element:
    run = ET.Element(qname(WORD_NS, "r"))
    text_element = ET.SubElement(run, qname(WORD_NS, "t"))
    text_element.set(qname(XML_NS, "space"), "preserve")
    text_element.text = text
    return run


def replace_math_in_parent(parent: ET.Element, math_tag: str, *, display: bool) -> None:
    children = list(parent)
    for index, child in enumerate(children):
        replace_math_in_parent(child, math_tag, display=display)
        if child.tag != math_tag:
            continue

        formula = omml_to_markdown(child).strip()
        if not formula:
            continue

        delimiter = "$$" if display else "$"
        parent.remove(child)
        parent.insert(index, make_text_run(f"{delimiter}{formula}{delimiter}"))


def docx_with_markdown_math(docx_path: Path, temp_dir: Path) -> Path:
    converted_path = temp_dir / docx_path.name

    with zipfile.ZipFile(docx_path, "r") as source:
        root = ET.fromstring(source.read("word/document.xml"))
        replace_math_in_parent(
            root,
            qname(MATH_NS, "oMathPara"),
            display=True,
        )
        replace_math_in_parent(
            root,
            qname(MATH_NS, "oMath"),
            display=False,
        )
        document_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(
            converted_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as target:
            for item in source.infolist():
                data = (
                    document_xml
                    if item.filename == "word/document.xml"
                    else source.read(item.filename)
                )
                target.writestr(item, data)

    return converted_path


def should_indent_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return False

    structural_prefixes = (
        "#",
        "- ",
        "* ",
        "+ ",
        ">",
        "|",
        "!",
        "<",
        "$",
        "```",
        "---",
        "***",
    )
    if stripped.startswith(structural_prefixes):
        return False
    if re.match(r"\d+[.)]\s+", stripped):
        return False
    if re.match(r"^\[.+\]\(#.+\)$", stripped):
        return False
    return not line.startswith(FULL_WIDTH_INDENT)


def add_first_line_indent(markdown: str) -> str:
    return "\n".join(
        f"{FULL_WIDTH_INDENT}{line}" if should_indent_line(line) else line
        for line in markdown.split("\n")
    )


def clean_math_content(content: str) -> str:
    return re.sub(r"\\([_{}\[\]^])", r"\1", content)


def clean_math_spans(markdown: str) -> str:
    def clean_display(match: re.Match) -> str:
        return f"$${clean_math_content(match.group(1))}$$"

    def clean_inline(match: re.Match) -> str:
        return f"${clean_math_content(match.group(1))}$"

    markdown = re.sub(r"\$\$(.+?)\$\$", clean_display, markdown, flags=re.DOTALL)
    return re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", clean_inline, markdown)


def strip_inline_emphasis(markdown: str) -> str:
    lines: list[str] = []
    in_code_block = False

    for line in markdown.split("\n"):
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block
            lines.append(line)
            continue

        if in_code_block or line.lstrip().startswith(("#", "|")):
            lines.append(line)
            continue

        line = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", line)
        line = line.replace("**", "")
        lines.append(line)

    return "\n".join(lines)


def normalize_markdown(
    markdown: str,
    *,
    first_line_indent: bool = True,
    keep_inline_format: bool = True,
) -> str:
    markdown = markdown.replace("\r\n", "\n")
    markdown = re.sub(r"\*{4,}", "**", markdown)
    markdown = clean_math_spans(markdown)
    if not keep_inline_format:
        markdown = strip_inline_emphasis(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    if first_line_indent:
        markdown = add_first_line_indent(markdown)
    return markdown.strip() + "\n"


def convert_docx(
    docx_path: Path,
    output_dir: Path,
    *,
    ascii_names: bool = False,
    first_line_indent: bool = True,
    keep_inline_format: bool = True,
) -> Path:
    mammoth, markdownify = load_conversion_dependencies()
    doc_name = sanitize_name(docx_path.stem, ascii_only=ascii_names)
    doc_output_dir = output_dir / doc_name
    assets_dir = doc_output_dir / "assets"

    doc_output_dir.mkdir(parents=True, exist_ok=True)
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    image_counter = [0]
    convert_image = mammoth.images.img_element(
        lambda image: save_mammoth_image(image, assets_dir, image_counter)
    )
    style_map = """
    p[style-name='Title'] => h1:fresh
    p[style-name='Subtitle'] => p:fresh
    p[style-name='Heading 1'] => h1:fresh
    p[style-name='Heading 2'] => h2:fresh
    p[style-name='Heading 3'] => h3:fresh
    p[style-name='Heading 4'] => h4:fresh
    p[style-name='Heading 5'] => h5:fresh
    p[style-name='Heading 6'] => h6:fresh
    """

    with tempfile.TemporaryDirectory() as temp_dir_name:
        converted_docx = docx_with_markdown_math(docx_path, Path(temp_dir_name))
        with converted_docx.open("rb") as docx_file:
            result = mammoth.convert_to_html(
                docx_file,
                convert_image=convert_image,
                style_map=style_map,
            )

    markdown = markdownify(
        result.value,
        heading_style="ATX",
        bullets="-",
        strip=["span"],
    )

    md_path = doc_output_dir / f"{doc_name}.md"
    md_path.write_text(
        normalize_markdown(
            markdown,
            first_line_indent=first_line_indent,
            keep_inline_format=keep_inline_format,
        ),
        encoding="utf-8",
    )
    return md_path


def find_docx_files(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.glob("*.docx")
        if path.is_file() and not path.name.startswith("~$")
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert local DOCX files to Markdown.")
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Input directory containing .docx files. Default: original",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for Markdown folders. Default: output",
    )
    parser.add_argument(
        "--ascii-names",
        action="store_true",
        help="Use ASCII-only folder and Markdown file names.",
    )
    parser.add_argument(
        "--no-first-line-indent",
        action="store_true",
        help="Do not add two full-width spaces before normal paragraphs.",
    )
    parser.add_argument(
        "--plain-text",
        action="store_true",
        help="Remove inline bold and italic Markdown markers from body text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.input.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)

    docx_files = find_docx_files(args.input)
    if not docx_files:
        print(f"No .docx files found in {args.input}")
        return 0

    for docx_path in docx_files:
        md_path = convert_docx(
            docx_path,
            args.output,
            ascii_names=args.ascii_names,
            first_line_indent=not args.no_first_line_indent,
            keep_inline_format=not args.plain_text,
        )
        print(f"Converted: {docx_path} -> {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
