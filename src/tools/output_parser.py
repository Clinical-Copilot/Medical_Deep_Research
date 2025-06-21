import collections.abc as cabc
from typing import Any
import re


def dict2md(obj, level=1) -> str:
    """
    Render (usually) ``payload["results"]`` into Markdown.

    Rules
    -----
    * Keys whose value is ``None`` are skipped.
    * Every dict key becomes a heading using ``level`` hash marks (## when
      ``level==2``).
    * A list of dicts is **not** turned into a table; each element is rendered
      in sequence.
    * A list of scalars is rendered as a comma‑separated line.
    * Long *warnings* strings are post‑processed:
        - phrases that end with ':' are promoted one level deeper as sub‑
          headings (### …).
        - the glyphs ``■`` and ``•`` become Markdown bullets (``-``).
    """

    def _format_scalar(value: Any, sub_level: int) -> str:
        if not isinstance(value, str):
            return str(value)

        # bullets
        txt = re.sub(r"[■•]\s*", "\n- ", value)

        # promote "Mini headings:" such as "Allergy alert:"
        def _subheading(match: re.Match) -> str:
            title = match.group(1).strip()
            return f'\n{"#"*sub_level} {title}\n'

        txt = re.sub(r"([A-Z][A-Za-z0-9’\'\- ]{2,}):", _subheading, txt)
        return txt

    md_lines = []

    # --------------------------- dict ---------------------------
    if isinstance(obj, dict):
        for k, v in obj.items():
            if v is None:
                continue  # omit empty sections

            md_lines.append(f'{"#"*level} {k}')
            md_lines.append(dict2md(v, level + 1).rstrip())
            md_lines.append("")  # blank line between key sections

    # --------------------------- list ---------------------------
    elif isinstance(obj, cabc.Sequence) and not isinstance(obj, (str, bytes)):
        if obj and all(isinstance(e, dict) for e in obj):
            # iterate through each dict (no table)
            for idx, element in enumerate(obj, 1):
                # Top‑level heading for each list entry
                md_lines.append(f"# Entry {idx}")
                md_lines.append(dict2md(element, level).rstrip())
                md_lines.append("")  # blank line between entries
        else:
            # list of scalars -> comma‑separated
            flat = ", ".join(str(x) for x in obj)
            md_lines.append(_format_scalar(flat, level))

    # -------------------------- scalar --------------------------
    else:
        md_lines.append(_format_scalar(obj, level + 1))

    return "\n".join(md_lines)
