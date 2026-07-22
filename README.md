# MarketTracker

MarketTracker is a desktop Python application for monitoring cryptocurrency market data, collecting market snapshots, and reviewing historical market trends.

## Current Status

The application now includes a dedicated Market Snapshots navigation page that presents the latest market snapshot records in a dedicated table view. The UI keeps the existing Dashboard and Reports workflows intact while adding a more polished snapshots experience.

## Recent UI Improvements

- Added a new Market Snapshots page button and page flow in the main navigation
- Added a dedicated market snapshot table page that matches the existing visual style
- Added search, filter, sort, and empty-state support for snapshot browsing
- Added clickable table header sort controls and live active-sort indicators
- Kept Portfolio and Alerts unchanged as planned areas
- Refined the filter-row layout for better responsiveness on narrower windows

## Notes

- Dashboard behavior and Reports behavior were preserved.
- The implementation is centered in the Tkinter UI layer in `ui.py` and the reports page remains in `reports.py`.
