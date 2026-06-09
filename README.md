# doc2md

本地 DOCX 到 Markdown 转换器。

## 目录结构

```text
doc2md/
├── doc2md.py
├── requirements.txt
├── original/
│   └── example.docx
├── output/
│   └── example/
│       ├── example.md
│       └── assets/
│           ├── image-001.png
│           └── image-002.jpeg
└── README.md
```

`original` 用于存放待转换的 Word 文档。每个文档会在 `output`
下生成一个同名文件夹，Markdown 中的图片统一使用相对路径。

## 建立环境

```bash
cd /Users/lushi78778/pythonCode/doc2md
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 转换

把 `.docx` 文件放入 `original`，然后运行：

```bash
.venv/bin/python doc2md.py
```

同名文档重复转换时，会覆盖同名 Markdown 和 `assets` 内容。

## 可选参数

```bash
# 去掉正文中的加粗、斜体标记，避免出现 ** 等源码字符
.venv/bin/python doc2md.py --plain-text

# 不添加两个全角空格作为中文首行缩进
.venv/bin/python doc2md.py --no-first-line-indent

# 使用 ASCII 输出名称
.venv/bin/python doc2md.py --ascii-names

# 指定输入和输出目录
.venv/bin/python doc2md.py --input original --output output
```

## 支持范围

- 标题、正文、列表、链接和表格
- 加粗、斜体，或通过 `--plain-text` 清理行内样式
- 图片提取及 `image-001` 顺序编号
- 图片相对路径
- 中文正文首行缩进
- 常见 Word 公式转 `$...$` 或 `$$...$$`
- 同名输出覆盖

Markdown 无法完整表达 Word 的字体、字号、颜色、分页、页眉页脚和
精确页面布局。本工具优先保留内容结构与常用语义格式。

## 文档站点

项目使用 Docsify 展示 `output` 下的 Markdown 文件，并通过 GitHub
Actions 自动部署到 GitHub Pages。

本地预览：

```bash
.venv/bin/python scripts/build_docs_site.py
.venv/bin/python -m http.server 8000 --directory _site
```

浏览器访问 `http://localhost:8000`。

首次部署前，需要在 GitHub 仓库的 `Settings > Pages` 中把发布来源设为
`GitHub Actions`。之后推送 `main` 或 `master` 分支时会自动部署。
