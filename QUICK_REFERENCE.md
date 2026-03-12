# SSSD Quick Reference Guide

## Dashboard Access
- URL: http://127.0.0.1:8050/
- Start: `python sql_wait_stats_dashboard.py` or `start_dashboard.bat`

## Dashboard Pages

### 📊 Overview
**Purpose**: System health at a glance

**Key Metrics**:
- Overall Health Score (0-100%)
- Active Alerts (blocking sessions)
- CPU, Memory, I/O status
- Wait category distribution

**Use When**: Quick health check, identifying immediate issues

---

### ⚡ Performance
**Purpose**: Query and workload analysis

**Key Metrics**:
- Query duration (avg, p95, p99)
- Top slow queries
- Top CPU-intensive queries
- Top I/O-heavy queries
- Wait type breakdown

**Use When**: Performance troubleshooting, slow query identification

---

### 💾 Storage
**Purpose**: I/O and index health

**Key Metrics**:
- Read/write latency by file
- Database file sizes
- Index fragmentation
- Missing indexes

**Use When**: I/O bottleneck investigation, index optimization planning

---

### 🔒 Reliability
**Purpose**: System stability and backup monitoring

**Key Metrics**:
- SQL Server uptime
- Blocking sessions
- Deadlock count
- Backup age
- Active connections

**Use When**: Checking backup compliance, investigating blocking

---

## Health Thresholds

### CPU Usage
- 🟢 **Good**: < 70%
- 🟡 **Warning**: 70-85%
- 🔴 **Critical**: > 85%

### Memory (Page Life Expectancy)
- 🟢 **Good**: > 300 seconds
- 🟡 **Warning**: 150-300 seconds
- 🔴 **Critical**: < 150 seconds

### I/O Latency
- 🟢 **Good**: < 10 ms
- 🟡 **Warning**: 10-20 ms
- 🔴 **Critical**: > 20 ms

### Backup Age
- 🟢 **Good**: < 12 hours
- 🟡 **Warning**: 12-24 hours
- 🔴 **Critical**: > 24 hours

---

## Common Tasks

### Check Overall System Health
1. Go to **Overview** page
2. Check Overall Health Score (should be 80+)
3. Review any active alerts
4. Check CPU/Memory gauges

### Identify Slow Queries
1. Go to **Performance** page
2. Review "Top 10 Queries by Avg Duration"
3. Check query execution counts
4. Correlate with wait types

### Investigate I/O Issues
1. Go to **Storage** page
2. Check average read/write latency
3. Identify files with highest latency
4. Review I/O latency chart

### Check Backup Status
1. Go to **Reliability** page
2. Review "Hours Since Last Full Backup" chart
3. Look for red/yellow bars (overdue)
4. Check backup KPI card

### Find Blocking Issues
1. Go to **Reliability** page
2. Check "Blocking Sessions" KPI
3. Review blocking sessions table
4. Identify root blocker

---

## Refresh Settings

- **5 seconds**: Real-time monitoring (high load)
- **10 seconds**: Active troubleshooting
- **30 seconds**: Normal monitoring (recommended)
- **60 seconds**: Background monitoring
- **Manual**: On-demand refresh only

---

## Troubleshooting

### Dashboard won't Start
- Check SQL Server is running
- Verify config.json has correct credentials
- Ensure ODBC driver is installed
- Check firewall allows connection

### No Data Displayed
- Verify user has VIEW SERVER STATE permission
- Check database is accessible
- Ensure SQL Server version is 2012+
- Review terminal output for errors

### Slow Performance
- Increase refresh interval
- Check SQL Server resources
- Reduce number of open tabs
- Close other resource-intensive applications

### Missing Metrics
- Some features require Enterprise edition
- Backup data requires MSDB access
- Some DMVs not available in Express edition

---

## Color Coding

### KPI Cards
- **Blue (#4ECDC4)**: Informational
- **Green (#4CAF50)**: Healthy
- **Yellow (#FFA726)**: Warning
- **Red (#EF5350)**: Critical

### Wait Categories
- **Red**: CPU waits
- **Teal**: I/O waits
- **Blue**: Memory waits
- **Green**: Latch waits
- **Yellow**: Lock waits
- **Gray**: Other waits

---

## Best Practices

### Monitoring
- Set appropriate refresh interval for your use case
- Monitor all 4 pages regularly
- Pay attention to health score trends
- Investigate yellow/red indicators promptly

### Performance
- Address queries with high CPU/reads first
- Focus on frequently executed slow queries
- Monitor wait statistics for bottlenecks
- Review index recommendations

### Reliability
- Ensure backups are current (< 24 hours)
- Monitor blocking sessions during peak hours
- Track deadlock counts
- Verify uptime for stability

### Maintenance
- Review index fragmentation weekly
- Implement missing index recommendations carefully
- Consider removing unused indexes
- Monitor file growth trends

---

## Quick Reference SQL Permissions

```sql
-- Grant necessary permissions
USE master;
GO

GRANT VIEW SERVER STATE TO [your_monitoring_user];
GRANT VIEW DATABASE STATE TO [your_monitoring_user];
GO

USE msdb;
GO

GRANT SELECT ON dbo.backupset TO [your_monitoring_user];
GO
```

---

## Support

For issues or enhancements:
1. Check ENHANCEMENTS.md for detailed documentation
2. Review README.md for setup instructions
3. Check logs in terminal output
4. Verify SQL Server error logs

---

## Version Information

- **Version**: 2.0 (Enhanced Multi-Page Dashboard)
- **Python**: 3.7+
- **SQL Server**: 2012+
- **Key Libraries**: Dash, Plotly, Pandas, PyODBC
