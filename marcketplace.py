"""
Marketplace Décentralisée — Interface CLI Python
Sujet 3 — BC04 Blockchain

Mode : MOCK (sans connexion réseau Ethereum réelle)
       Le mock simule fidèlement le comportement du smart contract Solidity.
"""

import time
import hashlib
import random
import string
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# MOCK BLOCKCHAIN
# Simule web3.py + contrat Solidity sans connexion réseau
# ═══════════════════════════════════════════════════════════════════════════════

class MockBlockchain:
    """Simule un nœud Ethereum local avec historique de transactions."""

    def __init__(self):
        self.block_number = 1_000_000
        self.transactions: list[dict] = []

    def _new_tx_hash(self) -> str:
        raw = str(time.time()) + "".join(random.choices(string.hexdigits, k=16))
        return "0x" + hashlib.sha256(raw.encode()).hexdigest()

    def mine(self, from_addr: str, to_addr: str, value: int, fn_name: str, args: dict) -> dict:
        """Simule l'exécution d'une transaction et son minage."""
        self.block_number += 1
        gas_used = random.randint(40_000, 120_000)
        tx = {
            "hash":        self._new_tx_hash(),
            "block":       self.block_number,
            "from":        from_addr,
            "to":          to_addr,
            "value_wei":   value,
            "function":    fn_name,
            "args":        args,
            "gas_used":    gas_used,
            "timestamp":   time.time(),
            "status":      "success",
        }
        self.transactions.append(tx)
        return tx

    def mine_failed(self, from_addr: str, fn_name: str, reason: str) -> dict:
        """Simule une transaction revertée (require() échoué)."""
        tx = {
            "hash":      "0x" + "0" * 64,
            "block":     None,
            "from":      from_addr,
            "function":  fn_name,
            "reason":    reason,
            "status":    "reverted",
            "timestamp": time.time(),
        }
        self.transactions.append(tx)
        return tx


class MockMarketplaceContract:
    """
    Émule fidèlement le smart contract Marketplace.sol.
    Même logique que Solidity : require(), events, mappings, etc.
    """

    CONTRACT_ADDRESS = "0xMOCK_Marketplace_0000000000000000000000"

    def __init__(self, blockchain: MockBlockchain):
        self._bc = blockchain
        self._next_id: int = 1

        # mapping(uint256 => Item)
        self._items: dict[int, dict] = {}
        # uint256[]
        self._item_ids: list[int] = []

        # Solde ETH simulé de chaque adresse (en wei)
        self._balances: dict[str, int] = defaultdict(lambda: 10 * 10**18)  # 10 ETH par défaut

        # Events émis
        self.events: list[dict] = []

    # ── helpers internes ───────────────────────────────────────────────────────

    def _emit(self, event_name: str, **kwargs):
        self.events.append({"event": event_name, "timestamp": time.time(), **kwargs})

    def _transfer(self, from_addr: str, to_addr: str, amount_wei: int):
        """Débit / crédit simulé."""
        if self._balances[from_addr] < amount_wei:
            raise RevertError("Solde insuffisant")
        self._balances[from_addr] -= amount_wei
        self._balances[to_addr]   += amount_wei

    def balance_of(self, addr: str) -> int:
        return self._balances[addr]

    # ── fonctions write (transact) ─────────────────────────────────────────────

    def create_item(self, caller: str, name: str, description: str, price_wei: int) -> dict:
        # require()
        if not name.strip():
            raise RevertError("Le nom ne peut pas etre vide")
        if not description.strip():
            raise RevertError("La description ne peut pas etre vide")
        if price_wei <= 0:
            raise RevertError("Le prix doit etre superieur a 0")

        item_id = self._next_id
        self._next_id += 1

        self._items[item_id] = {
            "id":          item_id,
            "name":        name,
            "description": description,
            "price":       price_wei,
            "owner":       caller,
            "actif":       True,
        }
        self._item_ids.append(item_id)

        self._emit("ItemCreated", id=item_id, item_name=name, price=price_wei, owner=caller)

        tx = self._bc.mine(
            from_addr=caller,
            to_addr=self.CONTRACT_ADDRESS,
            value=0,
            fn_name="createItem",
            args={"name": name, "description": description, "price": price_wei},
        )
        return tx

    def buy_item(self, caller: str, item_id: int) -> dict:
        if item_id not in self._items:
            raise RevertError("Annonce inexistante")

        item = self._items[item_id]

        if not item["actif"]:
            raise RevertError("Annonce inactive")
        if caller == item["owner"]:
            raise RevertError("Vous ne pouvez pas acheter votre propre objet")
        if self._balances[caller] < item["price"]:
            raise RevertError("Paiement insuffisant")

        previous_owner = item["owner"]
        price          = item["price"]

        # Re-entrancy guard : désactiver avant le transfert
        item["actif"] = False
        item["owner"] = caller

        self._transfer(caller, previous_owner, price)

        self._emit(
            "ItemPurchased",
            id=item_id,
            previous_owner=previous_owner,
            new_owner=caller,
            price=price,
        )

        tx = self._bc.mine(
            from_addr=caller,
            to_addr=self.CONTRACT_ADDRESS,
            value=price,
            fn_name="buyItem",
            args={"id": item_id},
        )
        return tx

    def update_price(self, caller: str, item_id: int, new_price_wei: int) -> dict:
        if item_id not in self._items:
            raise RevertError("Annonce inexistante")

        item = self._items[item_id]

        if not item["actif"]:
            raise RevertError("Annonce inactive")
        if caller != item["owner"]:
            raise RevertError("Seul le proprietaire peut modifier le prix")
        if new_price_wei <= 0:
            raise RevertError("Le prix doit etre superieur a 0")

        old_price    = item["price"]
        item["price"] = new_price_wei

        self._emit(
            "PriceUpdated",
            id=item_id,
            old_price=old_price,
            new_price=new_price_wei,
            owner=caller,
        )

        tx = self._bc.mine(
            from_addr=caller,
            to_addr=self.CONTRACT_ADDRESS,
            value=0,
            fn_name="updatePrice",
            args={"id": item_id, "new_price": new_price_wei},
        )
        return tx

    # ── fonctions read (call) ──────────────────────────────────────────────────

    def get_item(self, item_id: int) -> dict:
        if item_id not in self._items:
            raise RevertError("Annonce inexistante")
        return dict(self._items[item_id])

    def get_active_item_ids(self) -> list[int]:
        return [i for i in self._item_ids if self._items[i]["actif"]]

    def get_items_by_owner(self, owner: str) -> list[int]:
        return [i for i in self._item_ids if self._items[i]["owner"] == owner]

    def total_items(self) -> int:
        return self._next_id - 1


class RevertError(Exception):
    """Simule un revert Solidity (require() échoué)."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES D'AFFICHAGE
# ═══════════════════════════════════════════════════════════════════════════════

def wei_to_eth(wei: int) -> float:
    return wei / 10**18

def eth_to_wei(eth: float) -> int:
    return int(eth * 10**18)

def fmt_addr(addr: str) -> str:
    """Affiche les 6 premiers et 4 derniers caractères d'une adresse."""
    if len(addr) > 12:
        return addr[:8] + "…" + addr[-4:]
    return addr

def fmt_eth(wei: int) -> str:
    return f"{wei_to_eth(wei):.6f} ETH"

def print_separator(char="─", width=60):
    print(char * width)

def print_header(title: str):
    print_separator("═")
    print(f"  {title}")
    print_separator("═")

def print_section(title: str):
    print()
    print_separator()
    print(f"  {title}")
    print_separator()

def print_item(item: dict):
    status = "✅ Actif" if item["actif"] else "❌ Vendu"
    print(f"  ID          : #{item['id']}")
    print(f"  Nom         : {item['name']}")
    print(f"  Description : {item['description']}")
    print(f"  Prix        : {fmt_eth(item['price'])}")
    print(f"  Propriétaire: {fmt_addr(item['owner'])}")
    print(f"  Statut      : {status}")

def print_tx(tx: dict):
    if tx.get("status") == "success":
        print(f"  ✅ Transaction minée")
        print(f"  Hash  : {tx['hash'][:20]}…")
        print(f"  Block : #{tx['block']}")
        print(f"  Gas   : {tx['gas_used']:,} units")
    else:
        print(f"  ❌ Transaction revertée : {tx.get('reason', '?')}")

def input_int(prompt: str) -> int | None:
    try:
        return int(input(prompt).strip())
    except ValueError:
        print("  ⚠️  Veuillez entrer un nombre entier.")
        return None

def input_float(prompt: str) -> float | None:
    try:
        return float(input(prompt).strip())
    except ValueError:
        print("  ⚠️  Veuillez entrer un nombre décimal (ex: 0.05).")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# GESTION DES COMPTES (simulation de portefeuilles)
# ═══════════════════════════════════════════════════════════════════════════════

ACCOUNTS = {
    "Alice":   "0xAlice__0000000000000000000000000000000",
    "Bob":     "0xBob____0000000000000000000000000000000",
    "Charlie": "0xCharlie0000000000000000000000000000000",
    "Dave":    "0xDave___0000000000000000000000000000000",
}

def select_account() -> tuple[str, str] | None:
    """Demande à l'utilisateur de choisir un compte."""
    print_section("Choisir un compte")
    names = list(ACCOUNTS.keys())
    for i, name in enumerate(names, 1):
        print(f"  [{i}] {name}  ({fmt_addr(ACCOUNTS[name])})")
    print(f"  [0] Retour")

    choice = input_int("\n  Votre choix : ")
    if choice is None or choice == 0:
        return None
    if 1 <= choice <= len(names):
        name = names[choice - 1]
        return name, ACCOUNTS[name]
    print("  ⚠️  Choix invalide.")
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIONS CLI
# ═══════════════════════════════════════════════════════════════════════════════

def action_ajouter(contract: MockMarketplaceContract, bc: MockBlockchain):
    print_section("Ajouter une annonce")

    result = select_account()
    if not result:
        return
    name_acc, addr = result

    print(f"\n  Compte : {name_acc} | Solde : {fmt_eth(contract.balance_of(addr))}")
    print()

    item_name = input("  Nom de l'objet      : ").strip()
    item_desc = input("  Description         : ").strip()
    price_eth = input_float("  Prix (en ETH)       : ")
    if price_eth is None:
        return
    price_wei = eth_to_wei(price_eth)

    try:
        tx = contract.create_item(addr, item_name, item_desc, price_wei)
        item_id = contract.total_items()
        print(f"\n  ✅ Annonce #{item_id} créée avec succès !")
        print_tx(tx)
    except RevertError as e:
        tx = bc.mine_failed(addr, "createItem", str(e))
        print(f"\n  ❌ Erreur Solidity : {e}")
        print_tx(tx)


def action_catalogue(contract: MockMarketplaceContract):
    print_section("Catalogue des annonces actives")

    active_ids = contract.get_active_item_ids()

    if not active_ids:
        print("  Aucune annonce active pour le moment.")
        return

    print(f"  {len(active_ids)} annonce(s) disponible(s)\n")

    for item_id in active_ids:
        print_separator("·")
        item = contract.get_item(item_id)
        print_item(item)

    print_separator("·")


def action_acheter(contract: MockMarketplaceContract, bc: MockBlockchain):
    print_section("Acheter un objet")

    active_ids = contract.get_active_item_ids()
    if not active_ids:
        print("  Aucune annonce active.")
        return

    # Afficher catalogue rapide
    print("  Annonces disponibles :")
    for item_id in active_ids:
        item = contract.get_item(item_id)
        print(f"    #{item_id} — {item['name']} — {fmt_eth(item['price'])} — vendeur : {fmt_addr(item['owner'])}")

    print()
    item_id = input_int("  ID de l'annonce à acheter (0 = annuler) : ")
    if item_id is None or item_id == 0:
        return

    result = select_account()
    if not result:
        return
    name_acc, addr = result

    try:
        item = contract.get_item(item_id)
        print(f"\n  Achat de : {item['name']}")
        print(f"  Prix     : {fmt_eth(item['price'])}")
        print(f"  Acheteur : {name_acc} | Solde avant : {fmt_eth(contract.balance_of(addr))}")
        confirm = input("\n  Confirmer l'achat ? (o/n) : ").strip().lower()
        if confirm != "o":
            print("  Achat annulé.")
            return

        tx = contract.buy_item(addr, item_id)
        print(f"\n  ✅ Achat effectué ! Vous êtes maintenant propriétaire de « {item['name']} »")
        print(f"  Solde après : {fmt_eth(contract.balance_of(addr))}")
        print_tx(tx)

    except RevertError as e:
        tx = bc.mine_failed(addr, "buyItem", str(e))
        print(f"\n  ❌ Erreur Solidity : {e}")
        print_tx(tx)


def action_modifier_prix(contract: MockMarketplaceContract, bc: MockBlockchain):
    print_section("Modifier le prix d'une annonce")

    result = select_account()
    if not result:
        return
    name_acc, addr = result

    my_ids = contract.get_items_by_owner(addr)
    active_my = [i for i in my_ids if contract.get_item(i)["actif"]]

    if not active_my:
        print(f"  {name_acc} n'a aucune annonce active à modifier.")
        return

    print(f"\n  Vos annonces actives :")
    for item_id in active_my:
        item = contract.get_item(item_id)
        print(f"    #{item_id} — {item['name']} — {fmt_eth(item['price'])}")

    item_id = input_int("\n  ID à modifier (0 = annuler) : ")
    if item_id is None or item_id == 0:
        return

    new_price_eth = input_float("  Nouveau prix (en ETH) : ")
    if new_price_eth is None:
        return
    new_price_wei = eth_to_wei(new_price_eth)

    try:
        tx = contract.update_price(addr, item_id, new_price_wei)
        print(f"\n  ✅ Prix mis à jour : {fmt_eth(new_price_wei)}")
        print_tx(tx)
    except RevertError as e:
        tx = bc.mine_failed(addr, "updatePrice", str(e))
        print(f"\n  ❌ Erreur Solidity : {e}")
        print_tx(tx)


def action_mes_objets(contract: MockMarketplaceContract):
    print_section("Mes objets")

    result = select_account()
    if not result:
        return
    name_acc, addr = result

    my_ids = contract.get_items_by_owner(addr)

    print(f"\n  Compte : {name_acc} | Solde : {fmt_eth(contract.balance_of(addr))}")

    if not my_ids:
        print(f"  {name_acc} ne possède aucun objet.")
        return

    print(f"\n  {len(my_ids)} objet(s) :\n")
    for item_id in my_ids:
        print_separator("·")
        item = contract.get_item(item_id)
        print_item(item)
    print_separator("·")


def action_historique(bc: MockBlockchain):
    print_section("Historique des transactions")

    if not bc.transactions:
        print("  Aucune transaction enregistrée.")
        return

    print(f"  {len(bc.transactions)} transaction(s)\n")

    for i, tx in enumerate(reversed(bc.transactions[-10:]), 1):
        status_icon = "✅" if tx["status"] == "success" else "❌"
        hash_short  = tx["hash"][:14] + "…" if len(tx["hash"]) > 14 else tx["hash"]
        block_info  = f"Block #{tx['block']}" if tx.get("block") else "Non miné"
        print(f"  {status_icon} [{i:02d}] {tx['function']:15s} | {hash_short} | {block_info}")

    if len(bc.transactions) > 10:
        print(f"\n  … et {len(bc.transactions) - 10} transaction(s) plus ancienne(s)")


def action_events(contract: MockMarketplaceContract):
    print_section("Events émis par le contrat")

    if not contract.events:
        print("  Aucun event émis.")
        return

    print(f"  {len(contract.events)} event(s)\n")

    icons = {
        "ItemCreated":   "📦",
        "ItemPurchased": "🛒",
        "PriceUpdated":  "✏️ ",
    }

    for evt in reversed(contract.events):
        icon = icons.get(evt["event"], "📡")
        ts   = time.strftime("%H:%M:%S", time.localtime(evt["timestamp"]))
        print(f"  {icon} [{ts}] {evt['event']}", end="")

        if evt["event"] == "ItemCreated":
            print(f"  → #{evt['id']} « {evt['item_name']} » | {fmt_eth(evt['price'])}")
        elif evt["event"] == "ItemPurchased":
            print(f"  → #{evt['id']} | {fmt_addr(evt['previous_owner'])} → {fmt_addr(evt['new_owner'])}")
        elif evt["event"] == "PriceUpdated":
            print(f"  → #{evt['id']} | {fmt_eth(evt['old_price'])} → {fmt_eth(evt['new_price'])}")
        else:
            print()


def action_stats(contract: MockMarketplaceContract, bc: MockBlockchain):
    print_section("Statistiques du contrat")

    total    = contract.total_items()
    actives  = len(contract.get_active_item_ids())
    vendus   = total - actives
    nb_tx    = len(bc.transactions)
    nb_ok    = sum(1 for t in bc.transactions if t["status"] == "success")
    nb_err   = nb_tx - nb_ok
    total_gas = sum(t.get("gas_used", 0) for t in bc.transactions if t.get("gas_used"))

    print(f"  Contrat      : {fmt_addr(MockMarketplaceContract.CONTRACT_ADDRESS)}")
    print(f"  Block actuel : #{bc.block_number:,}")
    print()
    print(f"  Annonces totales  : {total}")
    print(f"  ├─ Actives        : {actives}")
    print(f"  └─ Vendues        : {vendus}")
    print()
    print(f"  Transactions      : {nb_tx}")
    print(f"  ├─ Succès         : {nb_ok}")
    print(f"  ├─ Erreurs        : {nb_err}")
    print(f"  └─ Gas total      : {total_gas:,} units")


# ═══════════════════════════════════════════════════════════════════════════════
# MENU PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

MENU = [
    ("Voir le catalogue",          action_catalogue),
    ("Ajouter une annonce",        action_ajouter),
    ("Acheter un objet",           action_acheter),
    ("Modifier le prix",           action_modifier_prix),
    ("Mes objets",                 action_mes_objets),
    ("Historique des transactions",action_historique),
    ("Events du contrat",          action_events),
    ("Statistiques",               action_stats),
    ("Quitter",                    None),
]

def main():
    bc       = MockBlockchain()
    contract = MockMarketplaceContract(bc)

    print_header("Marketplace Décentralisée — BC04 Blockchain")
    print("  Réseau : 🟡 MOCK (simulation locale)")
    print(f"  Contrat: {fmt_addr(MockMarketplaceContract.CONTRACT_ADDRESS)}")
    print(f"  Comptes: {', '.join(ACCOUNTS.keys())} (10 ETH chacun)")

    # Données de démonstration
    contract.create_item(ACCOUNTS["Alice"],   "Photo NFT #001", "Photographie numérique rare",   eth_to_wei(0.5))
    contract.create_item(ACCOUNTS["Bob"],     "Ebook Python",   "Guide complet Python 3.12",     eth_to_wei(0.05))
    contract.create_item(ACCOUNTS["Charlie"], "Beat exclusif",  "Instrumental hip-hop 120 BPM",  eth_to_wei(0.12))
    print("\n  ✅ 3 annonces de démonstration chargées.\n")

    while True:
        print_section("Menu principal")
        for i, (label, _) in enumerate(MENU, 1):
            prefix = "🚪" if label == "Quitter" else f"[{i}]"
            print(f"  {prefix} {label}")

        choice = input_int("\n  Votre choix : ")
        if choice is None:
            continue

        if choice == len(MENU):
            print("\n  À bientôt !\n")
            break

        if 1 <= choice <= len(MENU) - 1:
            label, fn = MENU[choice - 1]
            # Passer les bons arguments selon la fonction
            import inspect
            sig  = inspect.signature(fn)
            params = list(sig.parameters.keys())

            if params == ["contract", "bc"]:
                fn(contract, bc)
            elif params == ["contract"]:
                fn(contract)
            elif params == ["bc"]:
                fn(bc)
            else:
                fn(contract, bc)
        else:
            print("  ⚠️  Choix invalide.")

    # Résumé final
    print_section("Résumé de la session")
    action_stats(contract, bc)
    print()


if __name__ == "__main__":
    main()