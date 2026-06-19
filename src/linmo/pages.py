from __future__ import annotations


def parse_pages(spec: str) -> list[int]:
    """Parse a 1-based page selection such as '41', '1-3', or '1,3,5'."""
    pages: list[int] = []
    seen: set[int] = set()

    for part in spec.split(","):
        token = part.strip()
        if not token:
            raise ValueError("page selection contains an empty item")

        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start = _parse_positive_int(start_text.strip(), "range start")
            end = _parse_positive_int(end_text.strip(), "range end")
            if end < start:
                raise ValueError(f"page range must be ascending: {token}")
            values = range(start, end + 1)
        else:
            values = [_parse_positive_int(token, "page")]

        for page in values:
            if page not in seen:
                pages.append(page)
                seen.add(page)

    return pages


def _parse_positive_int(value: str, label: str) -> int:
    if not value:
        raise ValueError(f"missing {label}")
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc
    if number < 1:
        raise ValueError(f"{label} must be >= 1: {value!r}")
    return number
