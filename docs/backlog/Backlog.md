# Sleep Data Dashboard - Development Backlog

> **📋 Archive Note**: When items are completed, move them to `Backlog_done_01.md` (or subsequent numbered files) to keep this backlog focused on current work. Include completion date and implementation details when archiving.

## 🚧 In Progress
1. **Code Structure Cleanup (Phase 1)**
   - Split monolithic main.py (921 lines) into modular structure
   - Create src/data_loader.py, src/visualizations.py, src/tabs/ modules
   - Extract data processing pipeline with caching
   - Build chart factory functions for reusable visualizations

## 📋 Planned Features

### High Priority
2. **Code Modularization Completion**
   - Eliminate duplicate data processing across tabs
   - Create single data preparation pipeline
   - Implement lazy loading for expensive computations
   - Standardize chart styling and configuration

3. **Session State & Performance**
   - Create session state manager class
   - Centralize state initialization and validation
   - Implement data processing pipeline with caching
   - Optimize pandas operations for large datasets

4. **Graceful Terminal Management**
   - Implement graceful shutdown mechanism for Streamlit server
   - Add "Stop Server" button in the dashboard
   - Automatically detect when user closes browser tab
   - Clean exit without requiring Ctrl+C force termination
   - Proper cleanup of resources on shutdown

### Medium Priority
5. **Advanced Sleep Analytics**
   - **10-day moving variance analysis** - Track sleep consistency trends over rolling windows
   - **Extreme outliers detection** - List of 10 all-time most unusual sleep periods with analysis
   - **Recording frequency analysis** - Number of recorded sleep periods per date with gaps identification
   - Sleep efficiency calculations and sleep debt tracking
   - Weekly/monthly trend analysis with statistical insights

6. **Enhanced Data Processing**
   - Google Drive API integration for automatic file sync
   - ZIP file extraction for Sleep Cloud backups
   - Data validation and cleaning pipeline
   - Historical data archiving system

7. **Timezone Processing Improvements**
   - Extract complex timezone logic to dedicated tested module
   - Add timezone validation and fallback logic
   - Create timezone configuration management
   - Handle edge cases in multi-timezone travel scenarios

8. **User Experience Improvements**
   - Mobile-responsive design optimization
   - Dark/light theme toggle
   - Custom date range filtering with presets
   - Export dashboard as PDF reports

### Low Priority
9. **Code Quality & Documentation**
   - Add comprehensive unit tests for core functions
   - Create integration tests for end-to-end workflows
   - Implement centralized error handling utilities
   - Add comprehensive docstrings with documented examples
   - Create design system constants for consistent styling

10. **Performance Optimizations**
    - Incremental data loading for large datasets
    - Background data processing
    - Memory optimization for visualization
    - Advanced caching strategy improvements

11. **Data Quality Tools**
    - Automated data anomaly detection
    - Missing data interpolation options
    - Data consistency checks
    - Export data validation reports

12. **Additional Features**
    - Sleep goal setting and tracking
    - Integration with other health apps
    - Multi-user support and data sharing capabilities
    - Hardcoded strings extraction to constants file

## 🐛 Known Issues
- Large CSV files (>10MB) may load slowly
- Event column parsing needs optimization
- Some edge cases in sleep phase detection

## 🔧 Technical Debt
- Complete main.py refactoring into smaller modules
- Add logging framework and performance monitoring
- Pin exact dependency versions in requirements.txt
- Improve code documentation and type hints
- Create automated testing pipeline

---

**📈 Progress Tracking**: 
- ✅ **Completed**: 3 major features (moved to Backlog_done_01.md)
- 🚧 **In Progress**: 1 item (Code Structure Cleanup)
- 📋 **High Priority**: 3 items (Modularization, Performance, Terminal Management)
- 📋 **Medium Priority**: 4 items (Advanced Analytics, Data Processing, Timezone, UX)
- 📋 **Low Priority**: 4 items (Quality, Performance, Tools, Features)
- 🐛 **Known Issues**: 3 items
- 🔧 **Technical Debt**: 5 items