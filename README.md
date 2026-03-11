# SQL Server Wait Statistics Dashboard

A real-time Python dashboard for monitoring SQL Server wait statistics and query performance.

## Features

1. **Top 5 Wait Types Line Chart** - Monitor the most significant wait types over time
2. **Top 10 Queries Table** - View queries with the highest total wait time
3. **Wait Type Distribution Pie Chart** - Visualize the distribution of different wait types
4. **Average Wait Times Bar Chart** - Compare average wait times across different wait types
5. **Auto-refresh** - Configurable refresh intervals (5s, 10s, 30s, 60s, or manual)

## Prerequisites

- Python 3.7 or higher
- SQL Server instance with appropriate permissions
- ODBC Driver for SQL Server

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
