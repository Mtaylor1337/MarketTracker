<!-- Project development roadmap -->

# 🚀 MarketTracker Roadmap

Development roadmap and long-term vision for the MarketTracker application.

**Last Updated:** July 14, 2026  
**Current Version:** v0.7  
**Current Sprint:** Sprint 4 – Prediction Ready Data Collection

---

# Mission Statement

Build a professional desktop market analysis platform while learning
modern software engineering, data engineering, and artificial
intelligence development practices.

The application will continuously collect market data,
organize it into high-quality datasets,
generate market predictions,
evaluate its own accuracy,
and improve over time.

---

# Project Vision

MarketTracker began as a cryptocurrency tracking application.

Its long-term goal is much larger.

MarketTracker will eventually become a self-improving market
research platform capable of:

- Collecting live market data
- Building historical datasets
- Creating predictive AI models
- Evaluating prediction accuracy
- Continuously improving those models
- Comparing competing forecasting methods

Every design decision from Version 0.7 forward should support
this long-term vision.

---

# Development Philosophy

Every feature added to MarketTracker should satisfy at least one
of these goals.

1. Improve data quality.
2. Improve prediction quality.
3. Improve visualization and analysis.

If a feature does not improve one of these three areas,
its value should be reconsidered before implementation.

---

# Current Project Status

## ✅ Sprint 1 – Foundation

Completed

- Project created
- GitHub repository
- Python environment
- SQLite database
- CoinGecko API integration
- First successful market snapshot

---

## ✅ Sprint 2 – Multi-Asset Tracking

Completed

- BTC
- ETH
- SOL
- XRP
- DOGE

- Historical snapshot storage
- Asset management
- Database moved into `/data`
- GitHub synchronization

---

## ✅ Sprint 3 – Automated Collection

Completed

- Automatic collection engine
- tracker.py
- Manual Refresh
- Start / Stop Tracking
- Progress bar
- Countdown timer
- Last Scan
- Next Scan
- Version management
- Improved dashboard layout

---

## 🚧 Sprint 4 – Prediction Ready Data Collection

Current Sprint

Current focus is improving the quality and organization
of collected market data before AI development begins.

Goals:

- Expand stored snapshot information
- Prepare database for AI training
- Improve reporting architecture
- Improve export capabilities
- Build long-term historical dataset

---

# Phase 1 — Data Acquisition

The objective of Phase 1 is not AI.

The objective is building the highest quality historical
market dataset possible.

The prediction engine is only as good as the information
it receives.

Every market collection represents one complete snapshot
of the market.

---

## Current Snapshot Data

Current database stores:

- Asset
- Price
- Timestamp

---

## Planned Snapshot Data

Future snapshot records should include:

### Identification

- Snapshot ID
- Asset ID
- Symbol
- Asset Type

### Time Information

- UTC Timestamp
- Local Timestamp
- Unix Timestamp
- Collection Interval
- Date
- Time
- Day
- Week
- Month
- Quarter

### Price Information

- Current Price
- Previous Price
- Price Difference
- Percent Change

### Market Information

- Market Cap
- Trading Volume
- Circulating Supply
- 24 Hour High
- 24 Hour Low

### Derived Features

Generated after collection.

- SMA
- EMA
- RSI
- MACD
- Bollinger Bands
- ATR
- Momentum
- Volatility
- Trend Direction

These values should be stored in a structured format that
exports cleanly to:

- SQLite
- CSV
- Excel
- Future database systems

---

# Phase 2 — AI Prediction Engine

Goal

Predict the next market interval.

Example

Using one month of BTC five-minute snapshots:

Predict

> BTC will trade near $64,215 five minutes from now.

Store the prediction.

Wait for the next market collection.

Compare prediction versus reality.

Store both.

Repeat continuously.

---

# Prediction Workflow

```text
Collect Market Data

↓

Store Snapshot

↓

Generate Prediction

↓

Store Prediction

↓

Wait for Next Collection

↓

Collect Actual Market Data

↓

Compare Prediction vs Actual

↓

Calculate Error

↓

Store Results

↓

Repeat
```

---

# Phase 3 — Continuous Learning

The prediction engine should improve over time.

Rather than training once,
the AI continuously evaluates itself.

Workflow

```text
Predict

↓

Score Prediction

↓

Accumulate Results

↓

Retrain after N Predictions

↓

Compare New Model

↓

Compare Previous Model

↓

Promote Better Model

↓

Repeat
```

Only prediction models that outperform the current
production model become active.

---

# Model Version History

Every trained model should have its own history.

Example

| Model | Algorithm | Training Rows | Accuracy |
|--------|-----------|---------------|----------|
| Model 1 | Linear Regression | 8,500 | 61% |
| Model 2 | Random Forest | 8,500 | 67% |
| Model 3 | XGBoost | 12,000 | 73% |

This allows objective comparison between
different forecasting methods.

---

# Phase 4 — Reporting & Analytics

Future dashboard features

- Historical Charts
- Multi-Asset Charts
- AI Prediction Graph
- Prediction Accuracy
- Confidence Score
- Technical Indicators
- Export to Excel
- Export to PDF
- CSV Export

---

# Phase 5 — Portfolio Intelligence

Track

- Holdings
- Average Cost
- Profit / Loss
- Portfolio Allocation

AI Analysis

- Strongest Momentum
- Highest Volatility
- Highest Confidence Prediction
- Historical Win Rate
- Trend Analysis

---

# Phase 6 — AI Research Lab

Experiment with multiple prediction methods.

Potential algorithms

- Linear Regression
- Random Forest
- XGBoost
- LightGBM
- LSTM Networks
- GRU Networks
- Transformer Models
- Reinforcement Learning

All prediction methods should be evaluated
using identical historical datasets.

---

# Version Roadmap

## Version 0.8

- Historical Graphs
- Spreadsheet Export
- PDF Export
- Improved Reporting

---

## Version 0.9

- Technical Indicators
- Better Analytics
- Enhanced Reporting

---

## Version 1.0

- Stable Desktop Release
- Documentation
- Installation Guide
- GitHub Release
- Portfolio Module

---

# Long-Term Goal

MarketTracker should eventually become an AI-assisted
market research platform that continuously learns from
its own historical data.

The system should collect data,
predict future market movement,
measure its own performance,
and improve through repeated evaluation.

Every version of MarketTracker should move one step
closer toward that vision.