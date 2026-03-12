# SQL Server Monitoring Dashboard (SSSD)

A comprehensive real-time Python dashboard for monitoring SQL Server performance, health, and reliability.

## Features

### 📊 Page 1: Overview Dashboard
- **Overall Health Score** - Composite system health indicator (0-100%)
- **Active Alerts** - Real-time blocking sessions count
- **Performance KPIs** - Query latency, CPU usage, memory pressure, I/O latency
- **CPU & Memory Gauges** - Visual indicators with color-coded thresholds
- **Wait Category Distribution** - Donut chart showing wait type breakdown
- **Top I/O Latency** - Database files with highest read/write latency

### ⚡ Page 2: Performance & Workload
- **Query Performance Metrics**
  - Average, 95th, and 99th percentile query duration
  - Total executions and unique query count
- **Top 10 Queries by Duration** - Slowest executing queries
- **Top 10 Queries by CPU Time** - Most CPU-intensive queries
- **Top 10 Queries by Logical Reads** - Queries with highest I/O
- **Top 10 Wait Types** - Major bottlenecks affecting performance
- **Batch Requests/Sec** - Throughput monitoring

### 💾 Page 3: Storage & I/O Health
- **I/O Latency Metrics**
  - Average read and write latency per database file
  - I/O stall time analysis
- **Database File Sizes** - Data and log file size tracking
- **Index Health**
  - Index fragmentation report (>10% threshold)
  - Unused indexes identification
  - Missing index recommendations with improvement measurements
- **Disk space and growth monitoring**

### 🔒 Page 4: Reliability & Availability
- **SQL Server Uptime** - Days and hours since last restart
- **Blocking & Concurrency**
  - Active blocking sessions with query details
  - Blocking chains and root blockers
  - Deadlock counter
- **Backup Status**
  - Last full, differential, and log backup times
  - Color-coded alerts for overdue backups (>24 hours)
  - Backup duration trends
- **Connection Statistics** - Active connections by login
- **Error tracking** - System errors and failed login attempts

### Additional Features
- **Auto-refresh** - Configurable intervals (5s, 10s, 30s, 60s, or manual)
- **Color-coded Health Indicators** - Green/Yellow/Red thresholds
- **Interactive Charts** - Hover tooltips with detailed information
- **Responsive Design** - Clean, professional UI with card-based layout

## Dashboard Pages

### Overview 
High-level system health with gauges, KPIs, and critical metrics for quick assessment.

### Performance
Deep dive into query performance, CPU usage, wait statistics, and throughput metrics.

### Storage
I/O latency analysis, file sizes, index fragmentation, and missing index recommendations.

### Reliability
Backup status, blocking sessions, uptime tracking, and connection monitoring.

## Prerequisites

- Python 3.7 or higher
- SQL Server instance with appropriate permissions
- ODBC Driver for SQL Server
- SQL Server permissions: VIEW SERVER STATE, VIEW DATABASE STATE

## Installation

1. Install required Python packages:
```bash
pip install -r requirements.txt
```

2. Install ODBC Driver for SQL Server if not already installed:
   - Download from: https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

3. Configure database connection:
   - Copy `config.example.json` to `config.json`
   - Update the connection details in `config.json`:
     ```json
     {
         "server": "your_server_instance",
         "database": "master",
         "username": "your_username",
         "password": "your_password",
         "driver": "ODBC Driver 17 for SQL Server"
     }
     ```

4. **Important**: Add `config.json` to your `.gitignore` to prevent committing credentials

## Usage

1. Run the dashboard:
```bash
python sql_wait_stats_dashboard.py
```

Or use the provided batch file (Windows):
```bash
start_dashboard.bat
```

2. Open your web browser and navigate to:
```
http://127.0.0.1:8050
```

3. Use the tab navigation to switch between dashboard pages
4. Configure the refresh interval using the dropdown in the header

## Performance Thresholds

The dashboard uses the following health thresholds:

### CPU
- 🟢 Green: < 70%
- 🟡 Yellow: 70-85%
- 🔴 Red: > 85%

### Memory (Page Life Expectancy)
- 🟢 Green: > 300 seconds
- 🟡 Yellow: 150-300 seconds
- 🔴 Red: < 150 seconds

### I/O Latency
- 🟢 Green: < 10ms
- 🟡 Yellow: 10-20ms
- 🔴 Red: > 20ms

### Backups
- 🟢 Green: < 12 hours since last full backup
- 🟡 Yellow: 12-24 hours
- 🔴 Red: > 24 hours

## Monitored Metrics

### Performance Metrics
- Query execution statistics (avg, p95, p99 duration)
- CPU utilization (SQL Server and overall)
- Memory statistics (Buffer cache hit ratio, PLE)
- Batch requests per second
- Scheduler queue length

### Storage Metrics
- I/O latency per database/file
- Database and log file sizes
- Index fragmentation levels
- Missing index recommendations
- File growth statistics

### Reliability Metrics
- SQL Server uptime
- Blocking sessions and deadlocks
- Backup age and status
- Active connections
- Error counts

## Troubleshooting

### Connection Issues
- Verify SQL Server is accessible from your machine
- Check firewall settings allow TCP/IP connections
- Ensure SQL Server authentication is enabled
- Verify user has VIEW SERVER STATE permission

### Performance Issues
- Increase refresh interval to reduce query load
- Ensure SQL Server has sufficient resources
- Check that DMVs are not being cleared frequently

### Missing Data
- Some metrics require specific SQL Server editions (Enterprise/Standard)
- Backup information comes from MSDB database
- Ensure appropriate permissions are granted

## Contributing

Feel free to submit issues or pull requests for improvements.

## License

MIT License

## Acknowledgments

Built with:
- [Plotly](https://plotly.com/) - Interactive charts
- [Dash](https://dash.plotly.com/) - Web application framework
- [Pandas](https://pandas.pydata.org/) - Data manipulation

2. Open your browser and navigate to:
```
http://127.0.0.1:8050
```

3. Use the refresh interval dropdown to control how often the dashboard updates

## Required SQL Server Permissions

The SQL Server user needs the following permissions:
- `VIEW SERVER STATE` permission to query DMVs (Dynamic Management Views)

Grant permissions with:
```sql
GRANT VIEW SERVER STATE TO [your_username];
```

## Dashboard Components

### 1. Top 5 Wait Types Over Time
Displays a line chart showing the top 5 wait types based on total wait time. This helps identify performance bottlenecks.

### 2. Wait Type Distribution
A pie chart showing the percentage distribution of different wait types, grouped with smaller types as "Others".

### 3. Average Wait Times
A bar chart comparing the average wait time per task for different wait types, useful for identifying efficiency issues.

### 4. Top Queries by Wait Time
A table listing the top 10 queries with the highest total wait time, including:
- Query text (truncated for display)
- Execution count
- Total wait time (ms)
- Total CPU time (ms)
- Total elapsed time (ms)

## Git Security

The repository includes:
- `.gitignore` - Excludes `config.json` and sensitive files from version control
- `config.example.json` - Template for configuration without actual credentials

**Never commit `config.json` with actual credentials to Git!**

## Troubleshooting

### Connection Issues
- Verify SQL Server is accessible from your machine
- Check firewall settings allow connections on SQL Server port (default 1433)
- Confirm username and password are correct
- Ensure the ODBC driver version matches your SQL Server version

### Missing Data
- Verify the user has `VIEW SERVER STATE` permission
- Check that SQL Server has been running long enough to collect wait statistics
- Run `SELECT * FROM sys.dm_os_wait_stats` manually to verify data availability

### Performance
- Adjust refresh interval if dashboard is slow
- Consider limiting the number of queries displayed
- Ensure SQL Server isn't overloaded

## Customization

You can modify the following in `sql_wait_stats_dashboard.py`:
- Number of wait types displayed (default: 5)
- Number of queries shown (default: 10)
- Excluded wait types (system/idle waits)
- Chart colors and styling
- Dashboard port (default: 8050)

## License

This project is provided as-is for monitoring SQL Server performance.
