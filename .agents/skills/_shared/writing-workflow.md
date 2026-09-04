# Shared Writing Workflow — MathModel Project Adaptation

Adapted from QuantumBFS/sci-brain (MIT). Use from `survey`, `paper-reviewer`, and the supporting `paper-writer` rulebook.

- Resolve the project KB with `python .agents/skills/download-ref/helpers/resolve_kb.py`.
- Prefer `.knowledge/NOTES.md`, `.knowledge/INDEX.md`, and `.knowledge/references.bib`.
- Never invent BibTeX or claim contents from metadata alone.
- Use only Crossref, OpenAlex, Semantic Scholar, arXiv, publisher open pages, institutional repositories, or authorized user files.
- For mathematical-modeling papers, `5writing` controls structure, Typst, competition formatting, and G5–G7 approvals.
- `survey` must not bypass `mathmodel-learning` approval for reusable paper/method cards.
- Compile Typst outputs, check unresolved citations, and report skipped verification.

Scope cited references with:

```sh
python .agents/skills/download-ref/helpers/scope_refs.py --notes "$KB/NOTES.md" --bib "$KB/references.bib"
```

For Typst mechanics, read `.agents/skills/_shared/typst-reference.md` and defer to `typst-author` when rules differ.
