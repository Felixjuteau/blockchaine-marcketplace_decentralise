import { useState, useEffect } from "react"
import { getItems, getAccounts, getTransactions, getEvents, getStats, createItem, buyItem, updatePrice } from "./api.js"

const ETH = 10n ** 18n
const ACCOUNTS = {
  Alice:   "0xAlice__0000000000000000000000000000000",
  Bob:     "0xBob____0000000000000000000000000000000",
  Charlie: "0xCharlie0000000000000000000000000000",
  Dave:    "0xDave___0000000000000000000000000000000",
}
const ACCOUNT_NAMES = Object.fromEntries(Object.entries(ACCOUNTS).map(([name, address]) => [address, name]))

const weiToEth = (wei) => Number(typeof wei === "string" ? BigInt(wei) : BigInt(wei)) / Number(ETH)
const fmtEth = (wei) => `${weiToEth(wei).toFixed(4)} ETH`
const fmtAddr = (addr) => addr?.length > 14 ? `${addr.slice(0, 8)}…${addr.slice(-4)}` : addr
const fmtTime = (ts) => new Date(ts).toLocaleTimeString("fr-FR")

const Badge = ({ children, color = "gray" }) => {
  const palette = {
    green:  { bg: "#EAF3DE", text: "#3B6D11", border: "#639922" },
    red:    { bg: "#FCEBEB", text: "#A32D2D", border: "#E24B4A" },
    gray:   { bg: "#F1EFE8", text: "#5F5E5A", border: "#B4B2A9" },
    blue:   { bg: "#E6F1FB", text: "#185FA5", border: "#378ADD" },
    amber:  { bg: "#FAEEDA", text: "#854F0B", border: "#BA7517" },
    purple: { bg: "#EEEDFE", text: "#534AB7", border: "#7F77DD" },
  }
  const style = palette[color] || palette.gray
  return (
    <span style={{ fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 999, background: style.bg, color: style.text, border: `0.5px solid ${style.border}`, whiteSpace: "nowrap", fontFamily: "var(--font-mono)" }}>
      {children}
    </span>
  )
}

const Button = ({ children, onClick, variant = "default", disabled = false, small = false }) => {
  const styles = {
    default: { background: "transparent", color: "var(--color-text-primary)", border: "0.5px solid var(--color-border-secondary)" },
    primary: { background: "#4A90D9", color: "#fff", border: "none" },
    ghost:   { background: "transparent", color: "var(--color-text-secondary)", border: "none" },
  }
  return (
    <button onClick={onClick} disabled={disabled} style={{ ...styles[variant], padding: small ? "5px 12px" : "8px 16px", borderRadius: "var(--border-radius-md)", fontSize: small ? 12 : 14, fontWeight: 500, cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.5 : 1, transition: "opacity 0.15s", fontFamily: "var(--font-sans)" }}>
      {children}
    </button>
  )
}

const Card = ({ children, style = {} }) => (
  <div style={{ background: "var(--color-background-primary)", border: "0.5px solid var(--color-border-tertiary)", borderRadius: "var(--border-radius-lg)", padding: "1rem 1.25rem", ...style }}>
    {children}
  </div>
)

const ItemCard = ({ item, currentAccount, onBuy, onEditPrice }) => {
  const isOwner = currentAccount === item.owner
  const canBuy = item.actif && !!currentAccount && !isOwner
  return (
    <Card style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <strong style={{ fontSize: 14 }}>{item.name}</strong>
            <Badge color={item.actif ? "green" : "gray"}>{item.actif ? "actif" : "vendu"}</Badge>
          </div>
          <p style={{ margin: 0, color: "var(--color-text-secondary)", fontSize: 13 }}>{item.description}</p>
        </div>
        <div style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>{fmtEth(item.price)}</div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 12, color: "var(--color-text-secondary)", fontFamily: "var(--font-mono)" }}>{ACCOUNT_NAMES[item.owner] || fmtAddr(item.owner)}</span>
        <div style={{ display: "flex", gap: 8 }}>
          {isOwner && item.actif && <Button small onClick={() => onEditPrice(item)}>Modifier</Button>}
          {canBuy && <Button variant="primary" small onClick={() => onBuy(item)}>Acheter</Button>}
        </div>
      </div>
    </Card>
  )
}

export default function App() {
  const [items, setItems] = useState([])
  const [accounts, setAccounts] = useState([])
  const [transactions, setTransactions] = useState([])
  const [events, setEvents] = useState([])
  const [stats, setStats] = useState(null)
  const [currentAccount, setCurrentAccount] = useState(null)
  const [newItem, setNewItem] = useState({ name: "", description: "", price: "" })
  const [editItem, setEditItem] = useState(null)
  const [editPrice, setEditPrice] = useState("")
  const [loading, setLoading] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = "success") => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const [itemsRes, accountsRes, txRes, eventsRes, statsRes] = await Promise.all([getItems(), getAccounts(), getTransactions(), getEvents(), getStats()])
      setItems(itemsRes.items)
      setAccounts(accountsRes.accounts)
      setTransactions(txRes.transactions)
      setEvents(eventsRes.events)
      setStats(statsRes.stats)
      if (!currentAccount && accountsRes.accounts.length) {
        setCurrentAccount(accountsRes.accounts[0].address)
      }
    } catch (error) {
      showToast(error.message || "Erreur de chargement", "error")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const activeItems = items.filter((item) => item.actif)
  const myItems = currentAccount ? items.filter((item) => item.owner === currentAccount) : []
  const receipts = transactions.length
  const okCount = transactions.filter((tx) => tx.status === "success").length
  const errCount = receipts - okCount

  const handleCreate = async () => {
    const price = parseFloat(newItem.price)
    if (!currentAccount || !newItem.name.trim() || !newItem.description.trim() || isNaN(price) || price <= 0) {
      return showToast("Remplissez tous les champs correctement", "error")
    }
    try {
      await createItem(currentAccount, newItem.name, newItem.description, price)
      showToast("Annonce créée")
      setNewItem({ name: "", description: "", price: "" })
      loadData()
    } catch (error) {
      showToast(error.message, "error")
    }
  }

  const handleBuy = async (item) => {
    if (!currentAccount) return showToast("Choisissez un compte", "error")
    try {
      await buyItem(currentAccount, item.id)
      showToast("Achat réussi")
      loadData()
    } catch (error) {
      showToast(error.message, "error")
    }
  }

  const handleUpdatePrice = async () => {
    const price = parseFloat(editPrice)
    if (!currentAccount || !editItem || isNaN(price) || price <= 0) return showToast("Prix invalide", "error")
    try {
      await updatePrice(currentAccount, editItem.id, price)
      showToast("Prix mis à jour")
      setEditItem(null)
      setEditPrice("")
      loadData()
    } catch (error) {
      showToast(error.message, "error")
    }
  }

  return (
    <div style={{ padding: 20, maxWidth: 1080, margin: "0 auto", fontFamily: "var(--font-sans)" }}>
      <h1>Marketplace Décentralisée</h1>
      <div style={{ marginBottom: 16, display: "flex", gap: 12, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <strong>Compte :</strong>
          <select value={currentAccount || ""} onChange={(e) => setCurrentAccount(e.target.value)}>
            {accounts.map((account) => (
              <option key={account.address} value={account.address}>{account.name}</option>
            ))}
          </select>
        </div>
        <div style={{ display: "inline-flex", gap: 8 }}>
          <Badge color="green">OK {okCount}</Badge>
          <Badge color="red">Err {errCount}</Badge>
        </div>
      </div>

      {loading ? <Card><p>Chargement...</p></Card> : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <h2>Catalogue</h2>
            {activeItems.length === 0 ? <Card><p>Aucune annonce active</p></Card> : activeItems.map((item) => <ItemCard key={item.id} item={item} currentAccount={currentAccount} onBuy={handleBuy} onEditPrice={(item) => { setEditItem(item); setEditPrice(weiToEth(item.price).toFixed(4)) }} />)}
          </div>
          <div>
            <h2>Ajouter une annonce</h2>
            <Card>
              <div style={{ display: "grid", gap: 12 }}>
                <div>
                  <label>Nom</label>
                  <input value={newItem.name} onChange={(e) => setNewItem((prev) => ({ ...prev, name: e.target.value }))} style={{ width: "100%" }} />
                </div>
                <div>
                  <label>Description</label>
                  <textarea value={newItem.description} onChange={(e) => setNewItem((prev) => ({ ...prev, description: e.target.value }))} rows={3} style={{ width: "100%" }} />
                </div>
                <div>
                  <label>Prix ETH</label>
                  <input type="number" value={newItem.price} onChange={(e) => setNewItem((prev) => ({ ...prev, price: e.target.value }))} style={{ width: "100%" }} />
                </div>
                <Button variant="primary" onClick={handleCreate}>Créer</Button>
              </div>
            </Card>

            <h2 style={{ marginTop: 24 }}>Vos objets</h2>
            {myItems.length === 0 ? <Card><p>Aucun objet</p></Card> : myItems.map((item) => <ItemCard key={item.id} item={item} currentAccount={currentAccount} onBuy={() => {}} onEditPrice={(item) => { setEditItem(item); setEditPrice(weiToEth(item.price).toFixed(4)) }} />)}
          </div>
        </div>
      )}

      <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
        <Card>
          <h3>Stats</h3>
          <p>Total annonces : {stats?.total_items ?? "–"}</p>
          <p>Actives : {stats?.active_items ?? "–"}</p>
          <p>Transactions : {stats?.transactions ?? "–"}</p>
        </Card>
        <Card>
          <h3>Derniers événements</h3>
          {events.slice(0, 4).map((evt) => (
            <div key={`${evt.event}-${evt.timestamp}`} style={{ marginBottom: 8 }}>
              <strong>{evt.event}</strong><br />
              <small>{fmtTime(evt.timestamp)}</small>
            </div>
          ))}
        </Card>
      </div>

      {editItem && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
          <Card style={{ width: 440 }}>
            <h3>Modifier prix de {editItem.name}</h3>
            <div style={{ display: "grid", gap: 12 }}>
              <input value={editPrice} onChange={(e) => setEditPrice(e.target.value)} type="number" step="0.001" />
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <Button onClick={() => setEditItem(null)}>Annuler</Button>
                <Button variant="primary" onClick={handleUpdatePrice}>Enregistrer</Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {toast && (
        <div style={{ position: "fixed", right: 20, bottom: 20, padding: 12, background: toast.type === "error" ? "#FDE8E8" : "#E6F7E7", border: `1px solid ${toast.type === "error" ? "#E24B4A" : "#639922"}`, borderRadius: 12 }}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
