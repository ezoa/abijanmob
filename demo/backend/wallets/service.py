"""Façade du module portefeuilles : best-effort pour l'infrastructure (un store
en panne ne bloque jamais la démo), validations métier strictes pour la
répartition (WalletError remonte à l'appelant sous forme de refus)."""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta, timezone

from analytics import db_url

from .models import CODE_LONGUEUR, PROVIDERS, SOLDES_INITIAUX, WalletError
from .store import MemoryWalletStore, PostgresWalletStore

log = logging.getLogger("wallets")

# Historique de démonstration du passager (jours passés, heure, montant,
# opérateur, ligne) : alimente « Mes dépenses » sans attendre des paiements
# réels pendant la démo. Les soldes « avant » sont reconstitués pour retomber
# exactement sur les soldes initiaux à la fin de l'historique.
_HISTORIQUE_DEMO = [
    (6, "07:42", 300, "wave", "Woro Riviera"),
    (6, "18:15", 400, "orange", "Gbaka Riviera 3 – Adjamé"),
    (5, "08:05", 400, "wave", "Gbaka Riviera 3 – Adjamé"),
    (4, "07:55", 300, "mtn", "Woro Riviera"),
    (3, "18:40", 200, "moov", "Woro Cocody"),
    (2, "08:20", 400, "orange", "Gbaka Riviera 3 – Adjamé"),
    (2, "17:50", 300, "wave", "Woro Riviera"),
    (1, "07:48", 250, "mtn", "Gbaka Abobo – Adjamé"),
]


class WalletService:
    def __init__(self, primary: MemoryWalletStore | PostgresWalletStore):
        self.primary = primary
        self.fallback = MemoryWalletStore()

    def _stores(self) -> list:
        return [self.primary, self.fallback]

    # ----------------------------------------------------------- démarrage

    def on_startup(self) -> None:
        for store in self._stores():
            try:
                store.ensure_ready()
                self._seed_demo_history(store)
            except Exception:  # noqa: BLE001 — jamais bloquant
                log.exception("wallets: initialisation — store suivant")

    def _seed_demo_history(self, store) -> None:
        if store.history_seeded():
            return
        soldes = dict(SOLDES_INITIAUX)
        for _, _, montant, operateur, _ in _HISTORIQUE_DEMO:
            soldes[operateur] += montant
        now = datetime.now(timezone.utc)
        lignes = []
        for jours, hhmm, montant, operateur, ligne in sorted(_HISTORIQUE_DEMO):
            h, m = map(int, hhmm.split(":"))
            ts = (now - timedelta(days=jours)).replace(hour=h, minute=m, second=0, microsecond=0)
            soldes[operateur] -= montant
            lignes.append(
                {
                    "ts": ts,
                    "provider": operateur,
                    "amount": montant,
                    "balance_after": soldes[operateur],
                    "ticket_id": None,
                    "line_name": ligne,
                    "kind": "seed",
                }
            )
        store.insert_history(lignes)

    # ----------------------------------------------------------- opérations

    def unlock(self, pin: str) -> dict:
        """Déverrouillage par code secret (simulation : 4 chiffres quelconques,
        comme le code de paiement). Les soldes ne sortent jamais sans ce code."""
        pin = (pin or "").strip()
        if len(pin) != CODE_LONGUEUR or not pin.isdigit():
            raise WalletError(f"Code secret à {CODE_LONGUEUR} chiffres requis")
        for store in self._stores():
            try:
                balances = store.balances()
                return {
                    "account": "Compte démo AbidjanMob",
                    "pin_ok": True,
                    "balances": {
                        p: {"label": PROVIDERS[p], "balance": balances[p]} for p in PROVIDERS
                    },
                    "total": sum(balances.values()),
                    "disclaimer": "Soldes simulés (prototype) : aucun compte mobile money"
                    " réel n'est accessible.",
                }
            except Exception:  # noqa: BLE001
                log.exception("wallets: déverrouillage — store suivant")
        raise WalletError("Portefeuilles indisponibles")

    def prepare_split(self, fare: int, splits: list) -> list[dict]:
        """Validation pure de la répartition, avant tout effet de bord."""
        if not splits:
            raise WalletError("Répartition vide")
        vus: set[str] = set()
        total = 0
        for s in splits:
            provider = s.provider if hasattr(s, "provider") else s["provider"]
            amount = s.amount if hasattr(s, "amount") else s["amount"]
            if provider not in PROVIDERS:
                raise WalletError("Opérateur mobile money inconnu")
            if provider in vus:
                raise WalletError("Opérateur en double dans la répartition")
            vus.add(provider)
            if not isinstance(amount, int) or amount <= 0:
                raise WalletError("Montant invalide (entier positif en FCFA requis)")
            total += amount
        if total != fare:
            raise WalletError("La répartition doit totaliser exactement le montant du trajet")
        return [
            {
                "provider": (s.provider if hasattr(s, "provider") else s["provider"]),
                "amount": (s.amount if hasattr(s, "amount") else s["amount"]),
            }
            for s in splits
        ]

    def pay_split(self, ticket_id: str, line_name: str, fare: int, splits: list) -> dict | None:
        """Débite les portefeuilles (atomique par store). Retourne la répartition
        affichable, ou None si aucune infrastructure n'a répondu (best-effort :
        le paiement ne doit jamais échouer pour une panne de store)."""
        valides = self.prepare_split(fare, splits)
        for store in self._stores():
            try:
                detail = store.debit(ticket_id, line_name, valides)
                return {
                    "splits": [
                        {"provider": PROVIDERS[d["provider"]], "amount": d["amount"]}
                        for d in detail
                    ]
                }
            except WalletError:
                raise
            except Exception:  # noqa: BLE001 — le paiement ne doit jamais échouer
                log.exception("wallets: débit %s — store suivant", ticket_id)
        return None

    def reset(self) -> dict | None:
        for store in self._stores():
            try:
                balances = store.reset()
                return {
                    "account": "Compte démo AbidjanMob",
                    "balances": {
                        p: {"label": PROVIDERS[p], "balance": balances[p]} for p in PROVIDERS
                    },
                    "total": sum(balances.values()),
                }
            except Exception:  # noqa: BLE001
                log.exception("wallets: réinitialisation — store suivant")
        return None

    def history(self, limit: int = 50) -> list[dict] | None:
        for store in self._stores():
            try:
                return store.transactions(limit)
            except Exception:  # noqa: BLE001
                log.exception("wallets: historique — store suivant")
        return None

    def spending_summary(self) -> dict | None:
        """Bilan des dépenses de transport du passager par période (jour,
        semaine, mois, trimestre) : totaux, paiements, répartition par
        opérateur. Agrégation en Python sur le journal (volume de démo faible,
        identique pour les stores mémoire et PostgreSQL)."""
        for store in self._stores():
            try:
                tx = store.transactions(limit=1000)
                break
            except Exception:  # noqa: BLE001
                log.exception("wallets: bilan dépenses — store suivant")
        else:
            return None
        now = datetime.now(timezone.utc)
        aujourdhui = now.date()
        bornes = {
            "day": datetime.combine(aujourdhui, time.min, tzinfo=timezone.utc),
            "week": datetime.combine(aujourdhui - timedelta(days=6), time.min, tzinfo=timezone.utc),
            "month": datetime.combine(aujourdhui.replace(day=1), time.min, tzinfo=timezone.utc),
            "quarter": datetime.combine(
                aujourdhui.replace(month=(aujourdhui.month - 1) // 3 * 3 + 1, day=1),
                time.min,
                tzinfo=timezone.utc,
            ),
        }
        periodes = {nom: {"count": 0, "total": 0, "by_provider": {}} for nom in bornes}
        periodes["all"] = {"count": 0, "total": 0, "by_provider": {}}
        for t in tx:
            if t["kind"] == "topup":
                continue  # un rechargement n'est pas une dépense de transport
            ts = datetime.fromisoformat(t["ts"])
            operateur = PROVIDERS.get(t["provider"], t["provider"])
            cibles = [nom for nom, debut in bornes.items() if ts >= debut]
            for cible in ["all", *cibles]:
                p = periodes[cible]
                p["count"] += 1
                p["total"] += t["amount"]
                p["by_provider"][operateur] = p["by_provider"].get(operateur, 0) + t["amount"]
        for p in periodes.values():
            p["by_provider"] = dict(sorted(p["by_provider"].items(), key=lambda kv: -kv[1]))
        return {
            "account": "Compte démo AbidjanMob",
            "periods": periodes,
            "disclaimer": "Dépenses simulées (prototype) : l'historique de démonstration"
            " est inclus.",
        }

    def topup(self, pin: str, provider: str, amount: int) -> dict | None:
        """Recharge un portefeuille virtuel depuis le « vrai » compte de
        l'opérateur (simulation : le compte réel n'est jamais débité, les APIs
        PSP arriveront avec le MVP)."""
        pin = (pin or "").strip()
        if len(pin) != CODE_LONGUEUR or not pin.isdigit():
            raise WalletError(f"Code secret à {CODE_LONGUEUR} chiffres requis")
        if provider not in PROVIDERS:
            raise WalletError("Opérateur mobile money inconnu")
        if not isinstance(amount, int) or not 1 <= amount <= 1_000_000:
            raise WalletError("Montant de rechargement invalide (1 à 1 000 000 FCFA)")
        for store in self._stores():
            try:
                balances = store.topup(provider, amount)
                return {
                    "account": "Compte démo AbidjanMob",
                    "provider": provider,
                    "label": PROVIDERS[provider],
                    "credited": amount,
                    "balances": {
                        p: {"label": PROVIDERS[p], "balance": balances[p]} for p in PROVIDERS
                    },
                    "total": sum(balances.values()),
                    "message": (
                        f"Rechargement simulé depuis votre compte {PROVIDERS[provider]} réel :"
                        f" +{amount} F crédités sur AbidjanMob-{PROVIDERS[provider]}."
                    ),
                }
            except WalletError:
                raise
            except Exception:  # noqa: BLE001
                log.exception("wallets: rechargement — store suivant")
        return None


_SERVICE: WalletService | None = None
_TEST_MODE = False


def get_service() -> WalletService:
    global _SERVICE
    if _SERVICE is None:
        primary: MemoryWalletStore | PostgresWalletStore
        if db_url() and not _TEST_MODE:
            primary = PostgresWalletStore()
        else:
            primary = MemoryWalletStore()
        _SERVICE = WalletService(primary)
    return _SERVICE


def configure_for_tests() -> None:
    """Force le store mémoire (tests pytest, aucune base requise)."""
    global _SERVICE, _TEST_MODE
    _TEST_MODE = True
    _SERVICE = None
