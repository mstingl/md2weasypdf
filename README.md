# md2weasypdf

Print PDFs from Markdown files and a HTML layout using [Weasyprint](https://weasyprint.org/).

## Installation

```shell
pip install md2weasypdf
```

## Usage

```shell
python -m md2weasypdf <input_folder_or_file> <output_path>
```

When a layout is not specified in the files frontmatter (see below), the `--layout` option has to be passed.

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

### Templating

Markdown files may contain Jinja2 templating, such as including other files.

In addition to just markdown files, `yaml` files are also rendered when there is a `_template.md` file present in the same or parent folder, which then uses Jinja2 to render its contents with values passed from the `yaml` file.

## Output / Layout

The document layout must be given via the command option `--layout` or in the frontmatter of the single file. As layout a directory name inside the `./layouts` directory (default, can be changed using `--layouts-dir`) is expected. In the layout directory, a `index.html.j2` or `index.html` file is expected, which is loaded as entrypoint. The file is parsed using Jinja2.

### Variables

#### Document

A document is, when `--bundle` option is used, a collection of articles, otherwise contains just one article.

The following variables are passed to the Jinja2 renderer:

- `date`: current date in ISO format
- `commit`: the current commit (with suffix `-dirty` when the working directory has uncommitted changes)
- `articles`: list of articles, will be a list of only one article when not using `--bundle` option
- `title`: the current filename of the article stripped by it's suffix, values in braces `()` removed and underscores `_` replaced with spaces ` `; or the value passed in `--title` (required and used value when `--bundle` option is set)
- `meta`: metadata as provided in the articles frontmatter and/or as passed in `--meta` (will be combined with frontmatter taking precedence)

#### Article

The article represents the single file which is used as input.

It has the following attributes for use in the document rendering:

- `title`: see above
- `content` rendered HTML, use with `| save` in Jinja2 to prevent unwanted escaping
- `source` path to the file
- `meta` see above
- `hash` git object hash of the file or, when other files were included in the article, a new hash over all used files
- `modified_date` date of last modification of the file or, when other files were included in the article, the latest date of all used files
- `has_custom_headline` indicates if the document starts with an h1 level heading

## Markdown Extensions

### Table of Contents

Insert a table of contents using `[TOC]`. The table of contents will be generated automatically based on the headlines (lines starting with one or multiple `#`) in the document.

Which levels of headlines should be included in the TOC can be defined by declaring `toc_depth` in meta passed or the articles frontmatter.

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

### Fields

Use `[>input_id]` to create a text input. To create a textarea, add `|textbox` after the input id. To create a date field, add `|YYYY-MM-DD` after the input id.

To add a placeholder, append the placeholder text within parens to the end of the input id: `[>input_id] (placeholder text)`.

### Mermaid.js

Mermaid.js can be used in code blocks with the language `mermaid`. To convert the mermaid code into an image, [mermaid-cli](https://github.com/mermaid-js/mermaid-cli) is required to be installed on the system.
