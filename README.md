# 🏛️ Canton Network — Featured Apps Directory

> 🌐 **Live Dashboard**: [nguyenguyen206.github.io/canton-featured-data/canton_apps_viewer.html](https://nguyenguyen206.github.io/canton-featured-data/canton_apps_viewer.html)
> 
> 🔄 **Auto-updated daily** via GitHub Actions

A comprehensive directory of all **Featured App Requests** submitted to the Canton Network tokenomics forum.

## 📊 Overview

- **201 Featured Apps** scraped from [lists.sync.global/g/tokenomics](https://lists.sync.global/g/tokenomics/topics)
- Categories: DeFi, Swap/DEX, Wallet, Oracle, Bridge, Exchange, Explorer, Lending, RWA, Prediction Market, and more
- Data includes: Project name, App name, Website URL, Description

## 📁 Files

| File | Description |
|------|-------------|
| `canton_apps_viewer.html` | 🎨 Premium web UI to browse & search all apps |
| `featured_apps.json` | 📦 Raw data in JSON format |
| `featured_apps.csv` | 📊 Data in CSV format (Excel-compatible) |
| `scrape_featured_apps.py` | 🔧 Python scraper script |

## 🚀 Usage

### View the Dashboard
```bash
# Start a local server
cd featured_apps
python -m http.server 8888

# Open in browser
# http://localhost:8888/canton_apps_viewer.html
```

### Re-scrape Data
```bash
pip install requests beautifulsoup4
python scrape_featured_apps.py
```

## 🎨 Dashboard Features

- 🌑 Dark mode with glassmorphism design
- 🔍 Real-time search across all fields
- 🏷️ Auto-categorization (DeFi, Swap, Wallet, Oracle, etc.)
- 📋 Grid & List view toggle
- 📊 Stats overview
- 📥 CSV export
- 🪟 Detail modal on click

## 📈 Category Breakdown

| Category | Description |
|----------|-------------|
| Swap / DEX | Decentralized exchanges, AMMs, atomic swaps |
| DeFi | Yield, vaults, staking, perpetuals, options |
| Wallet | Self-custody wallets, multi-sig |
| Oracle | Price feeds, data providers |
| Bridge | Cross-chain bridges, interoperability |
| Exchange | CEX integrations, on/off ramps |
| Explorer | Block explorers, analytics dashboards |
| Lending | Lending protocols, credit lines |
| Stablecoin | Stablecoins, synthetic dollars |
| RWA | Real world asset tokenization |
| Prediction | Prediction markets |
| Payment | Payment solutions, billing |
| Gaming | Games, social apps, NFTs |
| Infrastructure | Validators, APIs, compliance tools |

## 📝 License

Data sourced from publicly available Canton Network forum submissions.

