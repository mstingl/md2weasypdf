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
