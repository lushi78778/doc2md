# doc2md

`doc2md` 是一个本地文档转 Markdown 工具。当前定位很明确：把 `original` 文件夹里的 `.docx` 批量转换成 Markdown，并把结果写入 `output`。

## 目录结构

```text
doc2md/
├── doc2md.py
├── original/
│   └── 待转换文档.docx
├── output/
│   └── 待转换文档/
│       ├── 待转换文档.md
│       └── assets/
│           └── image-001.png
└── README.md
```

## 安装依赖

```bash
python3 -m venv .venv
.venv/bin/pip install mammoth markdownify
```

## 使用方式

把 Word 文档放到 `original` 文件夹，然后运行：

```bash
.venv/bin/python doc2md.py
```

转换结果会生成在：

```text
output/文档名/文档名.md
```

如果同名文档重复转换，会覆盖同名 Markdown 文件。图片会按出现顺序命名，写入同级 `assets` 文件夹。

如果文档中有图片，会提取到：

```text
output/文档名/assets/
```

Markdown 中的图片路径一律使用相对路径：

```markdown
![image](assets/image-001.png)
```

## 可选参数

指定输入和输出目录：

```bash
.venv/bin/python doc2md.py --input original --output output
```

使用 ASCII 文件夹名和 Markdown 文件名：

```bash
.venv/bin/python doc2md.py --ascii-names
```

不添加中文首行缩进：

```bash
.venv/bin/python doc2md.py --no-first-line-indent
```

生成更干净的正文源码，去掉正文中的加粗和斜体标记：

```bash
.venv/bin/python doc2md.py --plain-text
```

## 当前支持

- 标题：Word `Heading 1` 到 `Heading 6` 转为 Markdown 标题
- 正文段落：转为普通 Markdown 段落
- 中文首行缩进：普通正文段落默认添加两个全角空格
- 加粗、斜体：通过成熟转换库尽量保留语义格式
- 无序列表、有序列表：保留列表结构
- 表格：尽量保留为 Markdown table
- 图片：提取到 `assets` 并使用相对路径引用
- 数学公式：将 Word 公式对象尽量转为 `$...$` 或 `$$...$$` 形式

## 格式说明

Markdown 更适合承载文档结构和语义格式，不是 Word 版式的完整替代品。标题、段落、列表、表格、链接、图片、加粗、斜体这类内容会尽量保留；字体、字号、颜色、分页、页眉页脚、精确缩进等版式信息无法在标准 Markdown 中完整表达。

如果目标平台不会渲染 Markdown 的加粗语法，可以使用 `--plain-text` 生成更干净的正文内容，避免在正文里看到 `**` 这类行内格式标记。

## 后续增强方向

- 中文文件名转拼音或英文转写
- 嵌套列表层级识别
- 超链接保留
- 脚注、批注、页眉页脚处理
- PDF、HTML、PPTX 等更多格式输入
