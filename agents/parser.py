"""Shared parsing utilities for agent LLM responses."""

from __future__ import annotations

import re

# Matches leading list markers such as "- ", "• ", "* ", "1. ", "2) " etc.
_LIST_MARKER_RE = re.compile(r"^(?:[-•*]\s+|\d+[.)]\s+)")


def _strip_list_marker(text: str) -> str:
    """Remove a leading list-item marker if present, otherwise return as-is."""
    return _LIST_MARKER_RE.sub("", text)


def parse_sections(response: str, headings: list[str]) -> dict[str, list[str]]:
    """
    Split *response* into sections using *headings* as delimiters.

    Handles both styles:
    - Heading on its own line followed by content lines::

          ARTIFACTS:
          - app:latest

    - Heading with inline content::

          BUILD STATUS: SUCCESS

    Returns a dict mapping each heading to a list of non-empty content strings.
    """
    sections: dict[str, list[str]] = {h: [] for h in headings}
    current_section: str | None = None

    for line in response.splitlines():
        stripped = line.strip()
        matched_heading: str | None = None
        inline_content: str = ""

        for heading in headings:
            if stripped.upper().startswith(heading):
                matched_heading = heading
                # Capture any content on the same line after the heading.
                after = stripped[len(heading):].lstrip(": \t")
                if after:
                    inline_content = after
                break

        if matched_heading is not None:
            current_section = matched_heading
            if inline_content:
                clean = _strip_list_marker(inline_content)
                if clean:
                    sections[current_section].append(clean)
            continue

        if current_section and stripped:
            clean = _strip_list_marker(stripped)
            if clean:
                sections[current_section].append(clean)

    return sections
