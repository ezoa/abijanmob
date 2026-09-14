"""Module financier AbidjanMob — prototype de démonstration (AIMD 2026).

Chaîne : Paiement → Transaction comptable → { Billet de transport, Facture/reçu
client, Souche conducteur, Calcul commissions, Calcul/provision taxes, Écriture
relevé conducteur }. Tous les documents partagent des identifiants communs
(payment_id, transaction_id, ticket_id, document_id, driver_id).

Sous-modules :
- fees                — frais de paiement + commission plateforme (valeurs de démo)
- tax_engine          — moteur fiscal : règles configurables, AUCUN taux codé en dur
- fne                 — interface de certification FNE/RNE + fournisseur simulé
- documents           — numérotation et génération des documents
- documents_numbering — formats de numérotation (FAC/STB/CLR-AAAA-NNNNNN)
- store               — persistance : PostgreSQL (docker) ou mémoire (local / tests)
- service             — façade best-effort (jamais bloquante pour un paiement)
- api                 — points d'entrée HTTP du module

Tout est SIMULÉ : aucun taux fiscal ivoirien officiel, aucune certification FNE.
"""

from . import documents, fne, tax_engine  # noqa: F401
from .documents import PaymentContext, build_payment_context  # noqa: F401
from .service import (  # noqa: F401
    configure_for_tests,
    demo_day_contexts,
    get_service,
)
