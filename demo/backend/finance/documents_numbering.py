"""Numérotation des documents financiers (formats dédiés, uniques par séquence)."""

from __future__ import annotations


def format_document_number(year: int, seq: int) -> str:
    """Facture / reçu client : FAC-AAAA-NNNNNN."""
    return f"FAC-{year}-{seq:06d}"


def format_stub_number(year: int, seq: int) -> str:
    """Souche conducteur : STB-AAAA-NNNNNN."""
    return f"STB-{year}-{seq:06d}"


def format_closure_number(year: int, seq: int) -> str:
    """Clôture de journée : CLR-AAAA-NNNNNN."""
    return f"CLR-{year}-{seq:06d}"
