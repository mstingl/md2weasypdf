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

```shell
python -m md2weasypdf <input_folder_or_file> <output_path> --watch
```

## Input

Input files are expected in markdown format with several markdown extensions. The markdown documents can utilize Jinja2 for templating inside the document (e. g. reusing texts).

### Options

YAML Frontmatter can be used to customize the document layout or add other options which will be passed to the template. The following example shows how a document with frontmatter section could look like:

```md
---
title: My Document Title
layout: doc1
---
Lorem ipsum...
```
