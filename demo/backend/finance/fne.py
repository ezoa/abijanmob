"""Préparation à la certification FNE/RNE (facturation normalisée électronique).

Interface de service `InvoiceCertificationProvider` + fournisseur simulé
`MockFNEProvider`. Le futur adaptateur de l'API DGI (facturation normalisée —
https://www.fne.dgi.gouv.ci/facturation.php) se branchera ici : implémenter
l'interface puis remplacer le fournisseur retourné par
`get_certification_provider()`.

Le prototype N'APPELLE JAMAIS l'API DGI, ne fabrique aucun QR « officiel » FNE,
n'utilise aucun secret, et ne mentionne jamais « facture certifiée ».
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class InvoiceCertificationProvider(ABC):
    """Service de certification d'une facture électronique (interface)."""

    @abstractmethod
    def certify(self, document: dict) -> dict:
        """Soumet un document à la certification.

        Retourne {"status": ..., "reference": ..., "message": ...} où status
        appartient à models.FNE_STATUSES.
        """


class MockFNEProvider(InvoiceCertificationProvider):
    """Fournisseur simulé : la certification n'est pas activée dans le prototype."""

    STATUS = "not_certified_demo"
    MESSAGE = "Certification FNE non activée dans le prototype"

    def certify(self, document: dict) -> dict:
        return {"status": self.STATUS, "reference": None, "message": self.MESSAGE}


_PROVIDER: InvoiceCertificationProvider = MockFNEProvider()


def get_certification_provider() -> InvoiceCertificationProvider:
    """Point d'injection du futur adaptateur API DGI (non appelé dans le prototype)."""
    return _PROVIDER
