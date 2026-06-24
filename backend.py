import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from marcketplace import MockBlockchain, MockMarketplaceContract, ACCOUNTS, eth_to_wei, RevertError

HOST = "127.0.0.1"
PORT = 5000

bc = MockBlockchain()
contract = MockMarketplaceContract(bc)

# Données de démonstration
contract.create_item(ACCOUNTS["Alice"], "Photo NFT #001", "Photographie numérique rare", eth_to_wei(0.5))
contract.create_item(ACCOUNTS["Bob"], "Ebook Python", "Guide complet Python 3.12", eth_to_wei(0.05))
contract.create_item(ACCOUNTS["Charlie"], "Beat exclusif", "Instrumental hip-hop 120 BPM", eth_to_wei(0.12))


def json_body(body):
    try:
        return json.loads(body.decode("utf-8")) if body else {}
    except json.JSONDecodeError:
        return {}


def send_json(handler, data, status=200):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()
    handler.wfile.write(payload)


def serialize_item(item):
    return {
        "id": item["id"],
        "name": item["name"],
        "description": item["description"],
        "price": str(item["price"]),
        "owner": item["owner"],
        "actif": item["actif"],
    }


def serialize_transaction(tx):
    result = dict(tx)
    if "value_wei" in result:
        result["value_wei"] = str(result["value_wei"])
    return result


def serialize_event(evt):
    result = dict(evt)
    for key in ("price", "old_price", "new_price"):
        if key in result:
            result[key] = str(result[key])
    return result


def build_items():
    return [serialize_item(contract.get_item(item_id)) for item_id in contract._item_ids]


def build_accounts():
    return [
        {
            "name": name,
            "address": address,
            "balance": str(contract.balance_of(address)),
        }
        for name, address in ACCOUNTS.items()
    ]


def build_stats():
    total = contract.total_items()
    active = len(contract.get_active_item_ids())
    transactions = len(bc.transactions)
    return {
        "contract": MockMarketplaceContract.CONTRACT_ADDRESS,
        "block_number": bc.block_number,
        "total_items": total,
        "active_items": active,
        "sold_items": total - active,
        "transactions": transactions,
        "success": sum(1 for tx in bc.transactions if tx["status"] == "success"),
        "reverted": sum(1 for tx in bc.transactions if tx["status"] != "success"),
        "total_gas": sum(tx.get("gas_used", 0) for tx in bc.transactions),
    }


class ApiHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/items":
            send_json(self, {"items": build_items()})
            return

        if path == "/api/items/active":
            items = [serialize_item(contract.get_item(item_id)) for item_id in contract.get_active_item_ids()]
            send_json(self, {"items": items})
            return

        if path.startswith("/api/items/"):
            parts = path.strip("/").split("/")
            if len(parts) == 3 and parts[1] == "items":
                try:
                    item_id = int(parts[2])
                    item = serialize_item(contract.get_item(item_id))
                    send_json(self, {"item": item})
                except (ValueError, RevertError) as exc:
                    send_json(self, {"error": str(exc)}, status=404)
                return

        if path == "/api/accounts":
            send_json(self, {"accounts": build_accounts()})
            return

        if path == "/api/transactions":
            send_json(self, {"transactions": [serialize_transaction(tx) for tx in bc.transactions]})
            return

        if path == "/api/events":
            send_json(self, {"events": [serialize_event(evt) for evt in contract.events]})
            return

        if path == "/api/stats":
            send_json(self, {"stats": build_stats()})
            return

        send_json(self, {"error": "Endpoint non trouvé"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(content_length) if content_length > 0 else b""
        body = json_body(payload)

        if path == "/api/items":
            caller = body.get("caller")
            name = body.get("name", "").strip()
            description = body.get("description", "").strip()
            price_eth = body.get("price_eth")
            if not caller or not name or not description or price_eth is None:
                send_json(self, {"error": "caller, name, description et price_eth sont requis"}, status=400)
                return
            try:
                price = float(price_eth)
                tx = contract.create_item(caller, name, description, eth_to_wei(price))
                item = contract.get_item(contract.total_items())
                send_json(self, {"item": item, "tx": tx})
            except (ValueError, RevertError) as exc:
                tx = bc.mine_failed(caller, "createItem", str(exc))
                send_json(self, {"error": str(exc), "tx": tx}, status=400)
            return

        if path.startswith("/api/items/") and path.endswith("/buy"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                send_json(self, {"error": "ID d'annonce invalide"}, status=400)
                return
            caller = body.get("caller")
            if not caller:
                send_json(self, {"error": "caller est requis"}, status=400)
                return
            try:
                tx = contract.buy_item(caller, item_id)
                item = contract.get_item(item_id)
                send_json(self, {"item": item, "tx": tx})
            except RevertError as exc:
                tx = bc.mine_failed(caller, "buyItem", str(exc))
                send_json(self, {"error": str(exc), "tx": tx}, status=400)
            return

        if path.startswith("/api/items/") and path.endswith("/price"):
            try:
                item_id = int(path.split("/")[3])
            except ValueError:
                send_json(self, {"error": "ID d'annonce invalide"}, status=400)
                return
            caller = body.get("caller")
            new_price_eth = body.get("new_price_eth")
            if not caller or new_price_eth is None:
                send_json(self, {"error": "caller et new_price_eth sont requis"}, status=400)
                return
            try:
                new_price = float(new_price_eth)
                tx = contract.update_price(caller, item_id, eth_to_wei(new_price))
                item = contract.get_item(item_id)
                send_json(self, {"item": item, "tx": tx})
            except RevertError as exc:
                tx = bc.mine_failed(caller, "updatePrice", str(exc))
                send_json(self, {"error": str(exc), "tx": tx}, status=400)
            return

        send_json(self, {"error": "Endpoint POST non trouvé"}, status=404)

    def log_message(self, format, *args):
        # éviter les logs de chaque requête vers stderr
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), ApiHandler)
    print(f"Démarrage du backend Python sur http://{HOST}:{PORT}")
    print("Endpoints disponibles: /api/items, /api/accounts, /api/transactions, /api/events, /api/stats")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur")
        server.server_close()
