<!-- Project development roadmap -->

# 🚀 MarketTracker Roadmap

Development roadmap and project milestones for the MarketTracker application.

**Last Updated:** July 4, 2026  
**Current Version:** v0.3  
**Current Sprint:** Sprint 3 – Automated Collection

---

## Mission Statement

Build a useful desktop application while learning professional software development practices, one feature at a time.

---

## Project Vision

MarketTracker is a desktop application for tracking cryptocurrencies
(and eventually stocks) over time.

The application periodically downloads market prices,
stores historical data in SQLite,
and provides reporting, charting,
alerts, and portfolio analysis.

The long-term goal is to build a polished desktop application while
learning professional software development practices along the way.

---

## Current Project Status

### ✅ Sprint 1 – Foundation

- [x] Project created
- [x] GitHub repository
- [x] Python environment
- [x] SQLite database
- [x] CoinGecko API integration
- [x] First successful snapshot

### ✅ Sprint 2 – Multi-Asset Tracking

- [x] BTC
- [x] ETH
- [x] SOL
- [x] XRP
- [x] DOGE

- [x] Historical snapshot storage
- [x] Asset management
- [x] Snapshot viewer
- [x] Database moved into `/data`
- [x] GitHub synchronization

### 🚧 Sprint 3 – Automated Collection

### Completed

- [x] `run_collection()` architecture
- [x] `tracker.py`
- [x] Automatic collection loop
- [x] Graceful Ctrl+C shutdown

### Next

- [ ] Configurable collection interval
- [ ] Read settings from `config.py`
- [ ] Logging

---

## Lessons Learned

- Separate the application engine from the user interface.
- Reusable functions are easier to maintain than duplicated code.
- Commit working milestones frequently.

---

## Future Roadmap

### Version 0.4 – Configurable Scheduler

- [ ] User-selectable collection interval
- [ ] Read settings from `config.py`
- [ ] Display next scheduled collection time

---

### Version 0.5 – Reporting

- [ ] Export historical data to Excel
- [ ] Export historical data to PDF
- [ ] Daily and weekly summaries
- [ ] High / Low price reports

---

### Version 0.6 – Charts

- [ ] Historical price charts
- [ ] Multiple asset comparison
- [ ] Moving averages
- [ ] Live updating graphs

---

### Version 0.7 – Desktop GUI

- [ ] Main dashboard
- [ ] Live prices
- [ ] Start / Stop tracking
- [ ] Asset management
- [ ] Settings page
- [ ] Export buttons

---

### Version 0.8 – Portfolio Tracking

- [ ] Track personal holdings
- [ ] Profit / Loss calculations
- [ ] Average purchase price
- [ ] Portfolio allocation charts

---

### Version 0.9 – Notifications

- [ ] Price alerts
- [ ] Goal notifications
- [ ] Desktop notifications
- [ ] Daily summary notifications

---

### Version 1.0 – Initial Release

- [ ] Stable desktop application
- [ ] Complete documentation
- [ ] Installation guide
- [ ] Versioned release on GitHub

---