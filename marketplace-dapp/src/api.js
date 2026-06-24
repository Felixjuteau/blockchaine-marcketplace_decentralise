const API_BASE = "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Erreur réseau");
  }
  return data;
}

export async function getItems() {
  return request("/items");
}

export async function getAccounts() {
  return request("/accounts");
}

export async function getTransactions() {
  return request("/transactions");
}

export async function getEvents() {
  return request("/events");
}

export async function getStats() {
  return request("/stats");
}

export async function createItem(caller, name, description, priceEth) {
  return request("/items", {
    method: "POST",
    body: JSON.stringify({ caller, name, description, price_eth: priceEth }),
  });
}

export async function buyItem(caller, itemId) {
  return request(`/items/${itemId}/buy`, {
    method: "POST",
    body: JSON.stringify({ caller }),
  });
}

export async function updatePrice(caller, itemId, newPriceEth) {
  return request(`/items/${itemId}/price`, {
    method: "POST",
    body: JSON.stringify({ caller, new_price_eth: newPriceEth }),
  });
}
