# MarketTracker Changelog

All notable changes to the MarketTracker project will be documented in this file.

The format is based on the principles of **Keep a Changelog**, with additional
Builder Notes documenting major development milestones and design decisions.

---

## [0.7] - 2026-07-13

### Added

- Automatic tracking dashboard
- Start / Stop Tracking controls
- Automatic tracking countdown timer
- Tracking progress bar
- Last Scan timestamp
- Next Scan timestamp
- Centralized application version management (`config_version.py`)
- Editable Change ID field in the Project Log Manager

### Changed

- Redesigned main dashboard layout
- Separated version information from the UI into a dedicated configuration file
- Improved automatic tracking workflow and status display
- Continued restructuring of application architecture for maintainability

### Fixed

- Progress bar synchronization
- Automatic tracking timing issues
- Manual refresh cooldown behavior
- Project Log Manager Change ID field editing

### Builder Notes

Version 0.7 represents the transition from an experimental prototype into a
functional desktop application.

Development focus shifted away from simply collecting cryptocurrency prices and
toward building a long-term market analysis platform.

The user interface now communicates the application's state in real time,
laying the groundwork for future AI prediction, reporting, and analytics
features.

This version also introduced centralized version management, improving project
organization as the application continues to grow.

---

## Upcoming (Version 0.8)

### Planned

- Historical price charts
- Spreadsheet export
- PDF export
- Improved reporting tools
- Additional market data collection fields
- Database enhancements to support future AI prediction models

### Long-Term Vision

Future releases will focus on transforming MarketTracker into a
self-improving market analysis platform capable of:

- Building high-quality historical datasets
- Generating market predictions
- Evaluating prediction accuracy
- Comparing multiple AI models
- Continuously improving forecasting performance