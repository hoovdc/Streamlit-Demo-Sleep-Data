# Sleep Data Dashboard - Development Backlog

> **📋 Archive Note**: When items are completed, move them to `Backlog_done_01.md` (or subsequent numbered files) to keep this backlog focused on current work. Include completion date and implementation details when archiving.

## 🚧 In Progress
*No items currently in active development*

## 📋 Planned Features

### High Priority
1. **Google Drive Sync Integration**
   - Modular implementation to automatically sync sleep data from Google Drive
   - Detailed phased plan in [docs/plans/Gdrive_sync_plan.md](../plans/Gdrive_sync_plan.md)
   - Handle ZIP files containing CSV exports
   - Local storage in SQLite DB for incremental updates
   - Scope: 2025+ data only
   - Secure handling of secrets in new `secrets/` folder (excluded via .gitignore)

2. **Graceful Terminal Management**
   - Implement graceful shutdown mechanism for Streamlit server
   - Add "Stop Server" button in the dashboard
   - Automatically detect when user closes browser tab
   - Clean exit without requiring Ctrl+C force termination
   - User invited to "Press Enter" in terminal to close app
   - Proper cleanup of resources on shutdown

3. **Enhanced Data Processing**
   - Google Drive API integration for automatic file sync
   - ZIP file extraction for Sleep Cloud backups
   - Data validation and cleaning pipeline improvements
   - Historical data archiving system

### Medium Priority
4. **Advanced Predictive Analytics**
   - Sleep efficiency calculations and sleep debt tracking
   - Predictive sleep quality models
   - Trend forecasting and pattern prediction
   - Weekly/monthly statistical insights with recommendations

5. **User Experience Improvements**
   - Mobile-responsive design optimization
   - Dark/light theme toggle
   - Custom date range filtering with presets
   - Export dashboard as PDF reports

6. **Sleep Goal & Achievement System**
   - Personal sleep target setting and tracking
   - Achievement badges and progress monitoring
   - Sleep consistency scoring system
   - Personalized recommendations based on patterns

### Low Priority
7. **Performance & Scale Optimizations**
    - Incremental data loading for large datasets
    - Background data processing
    - Memory optimization for visualization
    - Advanced caching strategy improvements

8. **Data Quality & Validation Tools**
    - Automated data anomaly detection
    - Missing data interpolation options
    - Enhanced data consistency checks
    - Export data validation reports

9. **Integration & Sharing Features**
    - Integration with other health apps (Fitbit, Apple Health)
    - Multi-user support and data sharing capabilities
    - Social features for sleep community insights
    - API endpoints for external integrations

10. **UI/UX Polish**
    - Further reduce excess whitespace and improve spacing
    - Enhanced visual design system
    - Accessibility improvements (screen reader support, keyboard navigation)
    - Advanced chart customization options

## 🐛 Known Issues
- Large CSV files (>10MB) may load slowly
- Event column parsing needs optimization  
- Some edge cases in sleep phase detection

## 🔧 Technical Debt
- Add comprehensive logging framework and performance monitoring
- Pin exact dependency versions in requirements.txt
- Improve code documentation and type hints consistency
- Create automated testing pipeline and CI/CD
- Extract hardcoded strings to constants file

---

**📈 Progress Tracking**: 
- ✅ **Completed**: 16 major features (moved to Backlog_done_01.md)
- 🚧 **In Progress**: 0 items
- 📋 **High Priority**: 3 items (GDrive Sync, Terminal Management, Data Processing)
- 📋 **Medium Priority**: 3 items (Predictive Analytics, UX, Goals)
- 📋 **Low Priority**: 4 items (Performance, Quality Tools, Integration, UI Polish)
- 🐛 **Known Issues**: 3 items
- 🔧 **Technical Debt**: 5 items