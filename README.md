# Marketplace Décentralisée (BC04)

Ce projet est une démonstration d’une marketplace décentralisée simulée avec deux parties :

- un backend Python (`backend.py`) qui expose une API REST simulant un smart contract Ethereum mock,
- une interface frontend React/Vite dans `marketplace-dapp/` qui consomme cette API.

## Structure du projet

- `marcketplace.py` : logique Python de simulation de blockchain et de contrat Marketplace.
- `backend.py` : serveur HTTP Python qui expose les endpoints REST.
- `marketplace-dapp/` : application React avec Vite.
- `marketplace-dapp/src/api.js` : client API pour appeler le backend Python.
- `marketplace-dapp/vite.config.js` : configuration Vite avec proxy vers le backend.

## Prérequis

- Python 3.11+ (ou 3.x compatible)
- Node.js 18+ / npm

## Installation

### 1. Installer les dépendances React

Ouvrez un terminal dans `marketplace-dapp` :

```bash
cd marketplace-dapp
npm install
```

### 2. Vérifier Python

Assurez-vous que Python est installé :

```bash
python --version
```

## Démarrage

### 1. Lancer le backend Python

Dans le dossier racine du projet :

```bash
python backend.py
```

Le serveur Python écoute par défaut sur :

- `http://127.0.0.1:5000`

### 2. Lancer le frontend React

Dans un autre terminal, depuis `marketplace-dapp` :

```bash
npm run dev
```

Ensuite, ouvrez le site indiqué par Vite (généralement `http://localhost:5173`).

## Fonctionnalités

### Backend

Le backend expose les endpoints :

- `GET /api/items`
- `GET /api/accounts`
- `GET /api/transactions`
- `GET /api/events`
- `GET /api/stats`
- `POST /api/items`
- `POST /api/items/{id}/buy`
- `POST /api/items/{id}/price`

### Frontend

L’interface React permet de :

- afficher le catalogue des annonces actives,
- créer une annonce,
- acheter un objet,
- modifier le prix d’une annonce possédée,
- consulter les transactions et les events.

## Notes importantes

- Le backend simule un contrat et des soldes : il n’y a pas de vraie blockchain.
- Le frontend utilise un proxy Vite pour rediriger `/api` vers le serveur Python.
- Si le frontend ne s’affiche pas, vérifiez d’abord que `backend.py` est bien lancé.

## Améliorations possibles

- ajouter une vraie base de données pour persister les annonces,
- utiliser FastAPI ou Flask pour un backend plus robuste,
- déployer le frontend et le backend séparément.

