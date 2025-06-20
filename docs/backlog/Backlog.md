# Sleep Data Dashboard - Development Backlog

> **📋 Archive Note**: When items are completed, move them to `Backlog_done_01.md` (or subsequent numbered files) to keep this backlog focused on current work. Include completion date and implementation details when archiving.

## 🚧 In Progress
**1. UI/UX Restructure & Modernization**
   - **Goal**: Reorganize the dashboard layout for improved clarity and user experience based on `UI_restructure.md`.
   - Implement new tab structure: "Sleep Duration & Trends", "Sleep Quality & Metrics", "Sleep Patterns & Timing".
   - Consolidate related analytics and insights into logical tabs.
   - Modernize visual design and ensure consistent styling.

## 📋 Planned Features

### High Priority
2. **Session State & Performance**
   - Create session state manager class
   - Centralize state initialization and validation
   - Implement data processing pipeline with caching

3. **Graceful Terminal Management**
   - Implement graceful shutdown mechanism for Streamlit server
   - Add "Stop Server" button in the dashboard
   - Automatically detect when user closes browser tab
   - Clean exit without requiring Ctrl+C force termination
   - User invited to "Press Enter" in terminal to close app
   - Proper cleanup of resources on shutdown

### Medium Priority
4. **Advanced Sleep Analytics**
   - ✅ **10-day moving variance analysis** - Track sleep consistency trends over rolling windows
   - ✅ **Extreme outliers detection** - List of 10 all-time most unusual sleep periods with analysis
   - ✅ **Recording frequency analysis** - Number of recorded sleep periods per date with gaps identification
   - ✅ **Variability (in X.X hrs) per day of week**
   - Sleep efficiency calculations and sleep debt tracking
   - Weekly/monthly trend analysis with statistical insights

5. **Enhanced Data Processing**
   - Google Drive API integration for automatic file sync
   - ZIP file extraction for Sleep Cloud backups
   - Data validation and cleaning pipeline
   - Historical data archiving system

6. **Timezone Processing Improvements**
   - Extract complex timezone logic to dedicated tested module
   - Add timezone validation and fallback logic
   - Create timezone configuration management
   - Handle edge cases in multi-timezone travel scenarios

7. **User Experience Improvements**
   - Mobile-responsive design optimization
   - Dark/light theme toggle
   - Custom date range filtering with presets
   - Export dashboard as PDF reports

### Low Priority
8. **Code Quality & Documentation**
   - Add comprehensive unit tests for core functions
   - Create integration tests for end-to-end workflows
   - Implement centralized error handling utilities
   - Add comprehensive docstrings with documented examples
   - Create design system constants for consistent styling

9. **Performance Optimizations**
    - Incremental data loading for large datasets
    - Background data processing
    - Memory optimization for visualization
    - Advanced caching strategy improvements

10. **Data Quality Tools**
    - Automated data anomaly detection
    - Missing data interpolation options
    - Data consistency checks
    - Export data validation reports

11. **Additional Features**
    - Sleep goal setting and tracking
    - Integration with other health apps
    - Multi-user support and data sharing capabilities
    - Hardcoded strings extraction to constants file

12. **UI/UX Improvements**
    - Reduce excess whitespace above the title "Sleep Data Dashboard" to ~0.8cm
    - Reduce vertical spacing between paragraphs and components across all tabs
    - Make content fill the window horizontally (current CSS attempts ineffective)
    - Improve visual spacing and layout consistency

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
- ✅ **Completed**: 5 major features (moved to Backlog_done_01.md)
- 🚧 **In Progress**: 1 item (UI/UX Restructure)
- 📋 **High Priority**: 2 items (Session State, Terminal Management)
- 📋 **Medium Priority**: 4 items (Advanced Analytics, Data Processing, Timezone, UX)
- 📋 **Low Priority**: 5 items (Quality, Performance, Tools, Features, UI/UX)
- 🐛 **Known Issues**: 3 items
- 🔧 **Technical Debt**: 5 items