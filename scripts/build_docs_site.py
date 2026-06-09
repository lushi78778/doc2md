#!/usr/bin/env python3
"""Build the static Docsify payload used by GitHub Pages."""

from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
SITE_DIR = ROOT / "_site"


def markdown_documents() -> list[Path]:
    return sorted(
        path
        for path in OUTPUT_DIR.rglob("*.md")
        if path.is_file()
    )


def sidebar_content(documents: list[Path]) -> str:
    lines = ["- [项目说明](README.md)", "", "- 转换文档"]

    if not documents:
        lines.append("  - 暂无文档")
    else:
        for document in documents:
            relative_path = document.relative_to(ROOT).as_posix()
            encoded_path = quote(relative_path, safe="/")
            title = document.stem.replace("[", r"\[").replace("]", r"\]")
            lines.append(f"  - [{title}]({encoded_path})")

    return "\n".join(lines) + "\n"


def build_site() -> None:
    documents = markdown_documents()

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    for filename in ("index.html", "README.md", ".nojekyll"):
        shutil.copy2(ROOT / filename, SITE_DIR / filename)

    if OUTPUT_DIR.exists():
        shutil.copytree(OUTPUT_DIR, SITE_DIR / "output")

    sidebar = sidebar_content(documents)
    (ROOT / "_sidebar.md").write_text(sidebar, encoding="utf-8")
    (SITE_DIR / "_sidebar.md").write_text(sidebar, encoding="utf-8")

    print(f"Built {SITE_DIR} with {len(documents)} document(s).")


if __name__ == "__main__":
    build_site()
