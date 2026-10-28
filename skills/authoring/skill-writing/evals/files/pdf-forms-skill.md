---
name: pdf-forms
description: Helps with documents, forms, files, PDFs, Word, DOCX, contracts, invoices and any paperwork the user needs to fill in or read.
license: MIT
metadata:
  author: example
  version: "1.2.0"
---

# PDF forms

Fill PDF forms with `pdftk`; it keeps the form fields editable, unlike printing to PDF.

1. List the fields: `pdftk form.pdf dump_data_fields`.
2. Write an FDF with the values, then `pdftk form.pdf fill_form values.fdf output filled.pdf`.

## Gotchas

- Field names are case-sensitive and often differ from the visible labels.
