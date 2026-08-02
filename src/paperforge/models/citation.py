from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CitationType = Literal[
    "article",
    "inproceedings",
    "book",
    "techreport",
    "misc",
    "phdthesis",
    "mastersthesis",
    "online",
]


@dataclass
class Citation:
    key: str  # BibTeX key e.g. "smith2024"
    type: CitationType = "article"
    authors: list[str] = field(default_factory=list)  # ["Smith, A.", "Jones, B."]
    title: str = ""
    year: int | None = None
    venue: str = ""  # journal name, conference name, etc.
    volume: str = ""  # journal volume
    number: str = ""  # journal issue number
    pages: str = ""  # e.g. "123--135"
    doi: str = ""  # DOI without https://doi.org/
    url: str = ""  # URL if no DOI
    publisher: str = ""  # for books
    institution: str = ""  # for techreports
    notes: str = ""
    evidence: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, data: dict[str, Any]) -> Citation:
        vol = data.get("volume")
        vol_str = "" if vol is None else str(vol)
        num = data.get("number")
        num_str = "" if num is None else str(num)
        return cls(
            key=data["key"],
            type=data.get("type", "article"),
            authors=data.get("authors", []),
            title=data.get("title", ""),
            year=data.get("year"),
            venue=data.get("venue", ""),
            volume=vol_str,
            number=num_str,
            pages=data.get("pages", ""),
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            publisher=data.get("publisher", ""),
            institution=data.get("institution", ""),
            notes=data.get("notes", ""),
            evidence=data.get("evidence", {}),
        )

    def to_yaml(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "type": self.type,
            "authors": self.authors,
            "title": self.title,
            "year": self.year,
            "venue": self.venue,
            "volume": self.volume,
            "number": self.number,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
            "publisher": self.publisher,
            "institution": self.institution,
            "notes": self.notes,
        }

    def to_bibtex(self) -> str:
        """Generate a valid BibTeX entry from this citation.

        Only includes non-empty fields.
        """
        authors_str = " and ".join(self.authors) if self.authors else "Author, A."

        venue_field = {
            "article": "journal",
            "inproceedings": "booktitle",
            "book": "publisher",
            "techreport": "institution",
            "phdthesis": "school",
            "mastersthesis": "school",
            "misc": "howpublished",
            "online": "url",
        }.get(self.type, "journal")

        fields: list[str] = [f"  author    = {{{authors_str}}}"]
        if self.title:
            fields.append(f"  title     = {{{self.title}}}")
        if self.venue:
            fields.append(f"  {venue_field:<9} = {{{self.venue}}}")
        if self.year:
            fields.append(f"  year      = {{{self.year}}}")
        if self.volume:
            fields.append(f"  volume    = {{{self.volume}}}")
        if self.number:
            fields.append(f"  number    = {{{self.number}}}")
        if self.pages:
            fields.append(f"  pages     = {{{self.pages}}}")
        if self.doi:
            fields.append(f"  doi       = {{{self.doi}}}")
        if self.url and not self.doi:
            fields.append(f"  url       = {{{self.url}}}")
        if self.notes:
            fields.append(f"  note      = {{{self.notes}}}")

        body = ",\n".join(fields)
        return f"@{self.type}{{{self.key},\n{body}\n}}"
