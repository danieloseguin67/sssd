# Quick Start Guide

## Get Started in 5 Minutes

### Step 1: Install Dependencies

**Option A - Using the batch file (Windows):**
```bash
install.bat
```

**Option B - Manual installation:**
```bash
pip install -r requirements.txt
```

### Step 2: Configure Database Connection

1. Copy the example configuration:
```bash
copy config.example.json config.json
```

2. Edit `config.json` with your SQL Server details:
```json
{
    "server": "localhost\\SQLEXPRESS",
    "database": "master",
    "username": "sa",
    "password": "YourPassword123!",
    "driver": "ODBC Driver 17 for SQL Server"
}
```

**Common server formats:**
- Local default instance: `localhost` or `.`
- Named instance: `localhost\\INSTANCENAME`
- Remote server: `server.domain.com` or `192.168.1.100`
- With port: `localhost,1433`

### Step 3: Test Configuration (Optional but Recommended)

```bash
python setup.py
```

This will verify:
- Configuration file is valid
- Required packages are installed
- Database connection works

### Step 4: Start the Dashboard

**Option A - Using the batch file (Windows):**
```bash
start_dashboard.bat
```

**Option B - Manual start:**
```bash
python sql_wait_stats_dashboard.py
```

### Step 5: View the Dashboard

Open your browser and go to:
```
http://127.0.0.1:8050
```

---

## Troubleshooting Common Issues

### Issue: "ODBC Driver not found"

**Solution:** Install the ODBC Driver for SQL Server
- Download: https://aka.ms/downloadmsodbcsql
- After installing, update `driver` in `config.json` to match:
  - `ODBC Driver 17 for SQL Server` (recommended)
  - `ODBC Driver 18 for SQL Server` (latest)
  - `SQL Server` (legacy, not recommended)

### Issue: "Login failed for user"

**Solutions:**
1. Verify username and password are correct
2. Check if SQL Server allows SQL authentication:
   - Open SQL Server Management Studio
   - Right-click server → Properties → Security
   - Enable "SQL Server and Windows Authentication mode"
   - Restart SQL Server service

### Issue: "Cannot connect to server"

**Solutions:**
1. Verify SQL Server is running:
   ```bash
   # Check SQL Server service
   sc query MSSQLSERVER
   # Or for named instance:
   sc query MSSQL$INSTANCENAME
   ```

2. Check if TCP/IP is enabled:
   - Open SQL Server Configuration Manager
   - SQL Server Network Configuration
   - Protocols for [Instance]
   - Enable TCP/IP
   - Restart SQL Server

3. Verify firewall allows connections on port 1433

### Issue: "Access denied to sys.dm_os_wait_stats"

**Solution:** Grant VIEW SERVER STATE permission:
```sql
-- Run in SQL Server Management Studio as admin
USE master;
GO
GRANT VIEW SERVER STATE TO [your_username];
GO
```

### Issue: Dashboard shows no data

**Solutions:**
1. SQL Server needs to run for a while to collect statistics
2. Verify permissions: `GRANT VIEW SERVER STATE TO [username];`
3. Check if wait stats exist:
   ```sql
   SELECT TOP 10 * FROM sys.dm_os_wait_stats 
   WHERE wait_time_ms > 0 
   ORDER BY wait_time_ms DESC;
   ```

---

## Configuration Examples

### Windows Authentication (Trusted Connection)
```json
{
    "server": "localhost",
    "database": "master",
    "username": "",
    "password": "",
    "driver": "ODBC Driver 17 for SQL Server"
}
```
Note: Username and password can be empty for Windows authentication

### Azure SQL Database
```json
{
    "server": "yourserver.database.windows.net",
    "database": "master",
    "username": "yourusername@yourserver",
    "password": "YourPassword123!",
    "driver": "ODBC Driver 17 for SQL Server"
}
```

### SQL Server Docker Container
```json
{
    "server": "localhost,1433",
    "database": "master",
    "username": "sa",
    "password": "YourStrong!Passw0rd",
    "driver": "ODBC Driver 17 for SQL Server"
}
```

---

## Dashboard Features

### Auto-Refresh
Use the dropdown to set refresh interval:
- **5 seconds** - Fast updates for active monitoring
- **10 seconds** - Default balanced option
- **30 seconds** - Reduced load
- **60 seconds** - Minimal load
- **Manual** - No auto-refresh

### Understanding Wait Types

**Common wait types and what they mean:**

- **PAGEIOLATCH_\***: Waiting for data pages to be read from disk (disk I/O bottleneck)
- **CXPACKET**: Parallel query coordination (consider adjusting max degree of parallelism)
- **WRITELOG**: Waiting to write to transaction log (log disk bottleneck)
- **LCK_\***: Lock waits (blocking/deadlocking issues)
- **ASYNC_NETWORK_IO**: Waiting for client to consume data
- **SOS_SCHEDULER_YIELD**: CPU pressure (queries yielding CPU time)

### Performance Tips

1. **High PAGEIOLATCH waits**: 
   - Add more memory
   - Optimize queries
   - Add missing indexes

2. **High CXPACKET waits**:
   - Adjust MAXDOP settings
   - Update statistics
   - Optimize parallel queries

3. **High WRITELOG waits**:
   - Use faster disk for transaction log
   - Reduce transaction size
   - Check log file autogrowth settings

---

## Next Steps

- Review the [README.md](README.md) for detailed documentation
- Customize the dashboard in `sql_wait_stats_dashboard.py`
- Set up monitoring alerts based on wait thresholds
- Schedule regular performance reviews

**Need Help?**
Check the troubleshooting section or review SQL Server DMV documentation.
