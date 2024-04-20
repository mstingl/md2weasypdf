# md2weasypdf

Print PDFs from Markdown Files using Weasyprint

## Installation

```shell
pip install md2weasypdf
```

## Usage

```shell
python -m md2weasypdf <input_folder_or_file> <output_path>
```

### Watch Mode

The watch mode is intended for creation of layouts. The given layouts directory and input directory will be watched for changes.

For VSCode the extension [vscode-pdf](https://marketplace.visualstudio.com/items?itemName=tomoki1207.pdf) can be recommended, as it refreshes the displayed PDF automatically.

```shell
python -m md2weasypdf <input_folder_or_file> <output_path> --watch
```

## Input

Input files are expected in markdown format with several markdown extensions. The markdown documents can utilize Jinja2 for templating inside the document (e. g. reusing texts).

### Bundling

The bundling feature allows to bundle multiple documents into one PDF. This is useful when you want to create one PDF file from multiple source files. The bundling feature is enabled by adding the `--bundle` flag to the command. The specified input folder will be searched recursively for `*.md` files, files starting with an underscore will be ignored.

When using the bundle option, a layout has to be specified using `--layout` and a title for the whole document using `--title`.

### Options

YAML Frontmatter can be used to customize the document layout or add other options which will be passed to the template. The following example shows how a document with frontmatter section could look like:

```md
---
title: My Document Title
layout: doc1
---
Lorem ipsum...
```

## Markdown Extensions

### Table of Contents

Insert a table of contents using `[TOC]`. The table of contents will be generated automatically based on the headlines (lines starting with one or multiple `#`) in the document.

### Table of Abbreviations

Insert a table of abbreviations using `[TOA]`. The table of abbreviations will be generated automatically based on defined abbreviations (using `*[Abbreviation]: Explanation`) in the document.

### Footnotes

Footnotes let you reference relevant information without disrupting the flow of what you're trying to say:

```md
Here's a simple footnote,[^1] and here's a longer one.[^bignote]

[^1]: This is the first footnote.

[^bignote]: Here's one with multiple paragraphs and code.

    Indent paragraphs to include them in the footnote.

    `{ my code }`

    Add as many paragraphs as you like.
```

It is possible to reference to the same footnote by using the same footnote label.

### Subscript

Use tildes `~` around text to create a subscript formatting.

### Checkboxes

Use `[ ]` to create a checkbox. Use `[x]` to mark a checkbox as checked.

### Input Fields

Use `[>input_id]` to create a text input. To create a textarea, add `|textarea` after the input id. To create a date field, add `|YYYY-MM-DD` after the input id.

To add a placeholder, append the placeholder text within parens to the end of the input id: `[>input_id] (placeholder text)`.
