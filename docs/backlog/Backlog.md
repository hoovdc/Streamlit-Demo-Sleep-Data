# Sleep Data Dashboard - Development Backlog

> **📋 Archive Note**: When items are completed, move them to `Backlog_done_01.md` (or subsequent numbered files) to keep this backlog focused on current work. Include completion date and implementation details when archiving.

## 🚧 In Progress
1. **Modularize other components**
   - Extract visualization functions into separate modules
   - Create dedicated data processing module
   - Separate configuration management

## 📋 Planned Features

### High Priority
2. **Dashboard Data Display Issues** ⚠️ **URGENT**
   - Investigate and fix incorrect data display in dashboard
   - Verify timezone conversion accuracy in visualizations
   - Check data filtering and aggregation logic
   - Validate sleep duration calculations
   - Test data consistency across different chart types
   - Ensure proper handling of multiple sleep periods per day
   - Debug any date/time formatting issues in charts

3. **Graceful Terminal Management**
   - Implement graceful shutdown mechanism for Streamlit server
   - Add "Stop Server" button in the dashboard
   - Automatically detect when user closes browser tab
   - Clean exit without requiring Ctrl+C force termination
   - Proper cleanup of resources on shutdown

4. **Enhanced Data Processing**
   - Google Drive API integration for automatic file sync
   - ZIP file extraction for Sleep Cloud backups
   - Data validation and cleaning pipeline
   - Historical data archiving system

5. **Advanced Analytics**
   - Sleep efficiency calculations
   - Sleep debt tracking
   - Predictive sleep quality models
   - Weekly/monthly trend analysis

6. **User Experience Improvements**
   - Mobile-responsive design
   - Dark/light theme toggle
   - Custom date range filtering
   - Export dashboard as PDF reports

### Medium Priority
7. **Performance Optimizations**
   - Incremental data loading for large datasets
   - Background data processing
   - Memory optimization for visualization
   - Caching strategy improvements

8. **Data Quality Tools**
   - Automated data anomaly detection
   - Missing data interpolation options
   - Data consistency checks
   - Export data validation reports

### Low Priority
9. **Additional Features**
   - Sleep goal setting and tracking
   - Integration with other health apps
   - Multi-user support
   - Data sharing capabilities

## 🐛 Known Issues
- Large CSV files (>10MB) may load slowly
- Event column parsing needs optimization
- Some edge cases in sleep phase detection

## 🔧 Technical Debt
- Refactor main.py into smaller modules
- Add comprehensive unit tests  
- Improve error handling consistency
- Add logging framework
- Code documentation and type hints

---

**📈 Progress Tracking**: 
- ✅ **Completed**: 3 major features (moved to Backlog_done_01.md)
- 🚧 **In Progress**: 1 item
- 📋 **Planned**: 7 items
- 🐛 **Known Issues**: 3 items
- 🔧 **Technical Debt**: 5 items