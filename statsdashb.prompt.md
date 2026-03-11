
# SQL Server Wait Statistics Dashboard - Project Documentation

## Project Overview

A professional Python-based dashboard for monitoring SQL Server wait statistics and query performance in real-time. Built with Dash/Plotly for interactive visualizations and pyodbc for SQL Server connectivity.

## ✅ Completed Features

### Dashboard Components

1. **KPI Cards (10 Metrics)**
   - CPU Waits % (Signal wait percentage)
   - IO Waits % (Page & log I/O)
   - Memory Waits % (Resource allocation)
   - Latch Waits % (Internal latches)
   - Lock Waits % (Blocking/deadlocks)
   - Other Waits % (Miscellaneous)
   - Total Wait Time (in minutes)
   - Top Wait Type (most significant wait)
   - Unique Wait Types (count of distinct types)
   - Waiting Tasks (total task count)

2. **Top Wait Types by Total Wait Time**
   - Horizontal bar chart
   - Color-coded by category (CPU/IO/Memory/Latch/Lock/Other)
   - Shows top 10 wait types with percentages

3. **Wait Category Distribution**
   - Donut chart
   - Groups waits into 6 categories
   - Interactive with hover details

4. **Average Wait Time per Task**
   - Shows which waits are most expensive per occurrence
   - Top 10 wait types ranked by average wait time

5. **Signal vs Resource Wait - Top 10**
   - Stacked horizontal bar chart
   - Separates CPU waits (signal) from resource waits
   - Critical for diagnosing CPU vs I/O issues

6. **Top Queries by Total Wait Time**
   - Interactive table with 10 queries
   - Shows query text, executions, wait time, CPU time, elapsed time
   - Tooltips show full query text
   - Formatted with alternating row colors

7. **Auto-Refresh**
   - Configurable refresh intervals: 5s, 10s, 30s, 60s, or Manual
   - Real-time status updates
   - Automatic reconnection handling

### Wait Type Categorization

Automatic categorization into meaningful groups:
- **CPU**: SOS_SCHEDULER_YIELD, CXPACKET, CXCONSUMER, THREADPOOL, SOS_WORK_DISPATCHER
- **IO**: PAGEIOLATCH_*, WRITELOG, IO_COMPLETION, ASYNC_IO_COMPLETION, BACKUPIO, LOGBUFFER
- **Memory**: RESOURCE_SEMAPHORE, MEMORY_ALLOCATION_EXT, CMEMTHREAD, SOS_RESERVEDMEMBLOCKLIST
- **Latch**: LATCH_*, PAGELATCH_*, ACCESS_METHODS_DATASET_PARENT
- **Lock**: LCK_M_* (all lock types including S, X, U, IS, IX, etc.)
- **Other**: All other wait types not in above categories

### SQL Queries Used

**Wait Statistics Query:**
```sql
SELECT TOP (?)
    wait_type,
    waiting_tasks_count,
    wait_time_ms,
    max_wait_time_ms,
    signal_wait_time_ms,
    wait_time_ms - signal_wait_time_ms AS resource_wait_time_ms,
    CAST(100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS DECIMAL(5,2)) AS [percentage]
FROM sys.dm_os_wait_stats
WHERE wait_type NOT IN (
    -- Excludes system/idle waits
    'CLR_SEMAPHORE', 'LAZYWRITER_SLEEP', 'RESOURCE_QUEUE', 'SLEEP_TASK',
    'SLEEP_SYSTEMTASK', 'SQLTRACE_BUFFER_FLUSH', 'WAITFOR', 'LOGMGR_QUEUE',
    'CHECKPOINT_QUEUE', 'REQUEST_FOR_DEADLOCK_SEARCH', 'XE_TIMER_EVENT',
    'XE_DISPATCHER_JOIN', 'XE_DISPATCHER_WAIT', 'BROKER_TO_FLUSH',
    'BROKER_TASK_STOP', 'CLR_MANUAL_EVENT', 'CLR_AUTO_EVENT',
    'DISPATCHER_QUEUE_SEMAPHORE', 'FT_IFTS_SCHEDULER_IDLE_WAIT',
    'FT_IFTSHC_MUTEX', 'HADR_FILESTREAM_IOMGR_IOCOMPLETION',
    'ONDEMAND_TASK_QUEUE', 'PREEMPTIVE_XE_GETTARGETSTATE',
    'PWAIT_ALL_COMPONENTS_INITIALIZED', 'QDS_PERSIST_TASK_MAIN_LOOP_SLEEP',
    'QDS_ASYNC_QUEUE', 'QDS_CLEANUP_STALE_QUERIES_TASK_MAIN_LOOP_SLEEP',
    'QDS_SHUTDOWN_QUEUE', 'REDO_THREAD_PENDING_WORK', 'SP_SERVER_DIAGNOSTICS_SLEEP'
)
AND wait_time_ms > 0
ORDER BY wait_time_ms DESC
```

**Query Wait Statistics:**
```sql
SELECT TOP (?)
    qs.sql_handle,
    SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
        ((CASE qs.statement_end_offset
            WHEN -1 THEN DATALENGTH(st.text)
            ELSE qs.statement_end_offset
        END - qs.statement_start_offset)/2) + 1) AS query_text,
    qs.execution_count,
    qs.total_worker_time / 1000 AS total_cpu_time_ms,
    qs.total_elapsed_time / 1000 AS total_elapsed_time_ms,
    (qs.total_elapsed_time - qs.total_worker_time) / 1000 AS total_wait_time_ms,
    qs.total_logical_reads,
    qs.total_physical_reads,
    qs.creation_time,
    qs.last_execution_time
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
WHERE qs.total_elapsed_time > qs.total_worker_time
ORDER BY total_wait_time_ms DESC
```

## 📁 Files Created

### Core Application
- **sql_wait_stats_dashboard.py** - Main Dash application (391 lines)
  - SQLServerWaitStats class for database operations
  - Dash layout with KPI cards and charts
  - Auto-refresh callbacks
  - Wait type categorization logic

### Configuration & Security
- **config.json** - Database connection settings (NOT in Git)
- **config.example.json** - Template for configuration
- **.gitignore** - Excludes sensitive files (config.json, __pycache__, .env)

### Dependencies & Setup
- **requirements.txt** - Python package dependencies
  - pyodbc>=4.0.35
  - pandas>=1.5.0
  - plotly>=5.11.0
  - dash>=2.7.0

- **install.bat** - Windows installer for dependencies
- **setup.py** - Configuration validator and connection tester
- **start_dashboard.bat** - One-click dashboard launcher

### Documentation
- **README.md** - Comprehensive documentation with features, setup, troubleshooting
- **QUICK_START.md** - Step-by-step setup guide with common issues and solutions
- **statsdashb.prompt.md** - This file (project documentation)

## 🔧 Technical Fixes Applied

### Issue 1: Jupyter Integration Error
**Problem:** Dash tried to initialize Jupyter comm in non-Jupyter environment
```
NotImplementedError: Cannot create comm
```

**Solution:** Mock the comm module before Dash import
```python
import sys
from unittest.mock import MagicMock
sys.modules['comm'] = MagicMock()
```

### Issue 2: Deprecated API
**Problem:** `app.run_server()` was replaced by `app.run()`
```
dash.exceptions.ObsoleteAttributeException: app.run_server has been replaced by app.run
```

**Solution:** Updated to use modern API
```python
app.run(debug=True, host='127.0.0.1', port=8050)
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   install.bat
   ```

2. **Configure database:**
   - Copy `config.example.json` to `config.json`
   - Update with your SQL Server credentials:
   ```json
   {
       "server": "localhost",
       "database": "master",
       "username": "your_username",
       "password": "your_password",
       "driver": "ODBC Driver 17 for SQL Server"
   }
   ```

3. **Grant permissions (on SQL Server):**
   ```sql
   GRANT VIEW SERVER STATE TO [your_username];
   ```

4. **Test configuration:**
   ```bash
   python setup.py
   ```

5. **Start dashboard:**
   ```bash
   start_dashboard.bat
   ```

6. **Open browser:**
   ```
   http://127.0.0.1:8050
   ```

## 🎨 Design Features

### Professional UI
- Dark header (#1a1a2e) with white content cards
- Color-coded wait categories
- Modern card-based layout with shadows
- Responsive grid system
- Clean typography (Arial, sans-serif)
- Alternating table rows for readability

### Color Scheme
- CPU (Red): #FF6B6B
- IO (Teal): #4ECDC4
- Memory (Blue): #45B7D1
- Latch (Green): #96CEB4
- Lock (Yellow): #FFEAA7
- Other (Gray): #DFE6E9
- Status (Purple/Pink/Light Blue): Various accent colors

### Interactive Features
- Hover tooltips on all charts
- Full query text on table hover
- Responsive refresh controls
- Real-time status in header
- Formatted numbers with thousands separators

## 📊 Performance Insights

### Understanding the Dashboard

**High CPU Waits (Red):**
- Signal wait percentage
- Indicates CPU pressure
- Consider query optimization or more CPU resources

**High IO Waits (Teal):**
- Page latches and log writes
- Indicates disk bottleneck
- Consider faster disks, more memory, or index optimization

**High Memory Waits (Blue):**
- Resource semaphore waits
- Indicates memory pressure
- Consider adding memory or optimizing queries

**Signal vs Resource Chart:**
- Signal (teal) = CPU time waiting for CPU
- Resource (red) = Time waiting for resources (disk, network, locks)
- Helps identify if issues are CPU-bound or resource-bound

## 🔐 Security Best Practices

1. **Never commit config.json** - Contains credentials
2. **Use .gitignore** - Already configured to exclude sensitive files
3. **Use config.example.json** - Share structure, not credentials
4. **Principle of least privilege** - Grant only VIEW SERVER STATE permission
5. **Consider Windows Authentication** - More secure than SQL authentication

## 🛠️ Customization Options

### Modify Dashboard
- Change KPI cards in layout
- Adjust chart types and colors
- Change auto-refresh intervals
- Modify wait type categories
- Adjust number of displayed items

### Extend Functionality
- Add historical data storage
- Implement alerting thresholds
- Export data to CSV/Excel
- Add more SQL Server DMV queries
- Create custom wait type filters

## 📚 Resources

- SQL Server DMVs: https://docs.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/
- Dash Documentation: https://dash.plotly.com/
- Plotly Charts: https://plotly.com/python/
- SQL Server Wait Types: https://www.sqlskills.com/help/waits/

## 📝 Notes

- Dashboard shows cumulative stats since SQL Server start
- To reset stats: `DBCC SQLPERF('sys.dm_os_wait_stats', CLEAR);`
- Some wait types are normal and expected
- Focus on top waits and trends over time
- Compare signal vs resource waits to diagnose issues

## 🎯 Project Status

**Status:** ✅ COMPLETED

All requested features implemented:
- ✅ Professional KPI dashboard
- ✅ Wait statistics visualization
- ✅ Query performance monitoring
- ✅ Auto-refresh functionality
- ✅ Category-based analysis
- ✅ Signal vs Resource breakdown
- ✅ Secure configuration management
- ✅ Comprehensive documentation
- ✅ Windows deployment scripts
- ✅ Professional UI/UX design

**Tested With:**
- Python 3.x (Anaconda distribution)
- SQL Server (various versions)
- Windows environment
- Chrome browser

**Known Limitations:**
- Shows cumulative statistics (not time-series history)
- Requires VIEW SERVER STATE permission
- Windows-focused (batch files for Windows)
- No built-in authentication for dashboard access

**Future Enhancements:**
- Add time-series data collection and graphing
- Implement alerting via email/SMS
- Add export functionality (PDF reports)
- Multi-server monitoring
- Authentication for dashboard access
- Mobile-responsive improvements
- Customizable color schemes via config.json
