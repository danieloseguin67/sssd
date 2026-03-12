import os
import sys
from unittest.mock import MagicMock

# Mock the comm module to prevent Jupyter integration issues
sys.modules['comm'] = MagicMock()

import pyodbc
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table
from datetime import datetime, timedelta
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SQLServerMonitor:
    """Class to handle comprehensive SQL Server monitoring queries"""
    
    def __init__(self, config_file='config.json', database_name=None):
        """Initialize with database configuration"""
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Support both old and new config format
        if 'databases' in config_data:
            # New format with multiple databases
            if database_name is None:
                database_name = config_data.get('default', list(config_data['databases'].keys())[0])
            self.config = config_data['databases'][database_name]
            self.database_name = database_name
        else:
            # Old format (single database)
            self.config = config_data
            self.database_name = config_data.get('database', 'default')
            
        self.connection = None
        
    def connect(self):
        """Establish connection to SQL Server"""
        try:
            conn_str = (
                f"DRIVER={{{self.config['driver']}}};"
                f"SERVER={self.config['server']};"
                f"DATABASE={self.config['database']};"
                f"UID={self.config['username']};"
                f"PWD={self.config['password']}"
            )
            self.connection = pyodbc.connect(conn_str)
            logger.info("Successfully connected to SQL Server")
            return True
        except Exception as e:
            logger.error(f"Error connecting to SQL Server: {e}")
            return False
    
    # ==================== PERFORMANCE & WORKLOAD ====================
    
    def get_query_performance_stats(self):
        """Get comprehensive query performance statistics"""
        query = """
        SELECT 
            COUNT(*) as query_count,
            AVG(qs.total_elapsed_time / qs.execution_count) / 1000.0 as avg_duration_ms,
            MAX(qs.total_elapsed_time / qs.execution_count) / 1000.0 as max_duration_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY qs.total_elapsed_time / qs.execution_count) OVER () / 1000.0 as p95_duration_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY qs.total_elapsed_time / qs.execution_count) OVER () / 1000.0 as p99_duration_ms,
            SUM(qs.execution_count) as total_executions
        FROM sys.dm_exec_query_stats qs
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0] if not df.empty else pd.Series()
        except Exception as e:
            logger.error(f"Error getting query performance stats: {e}")
            return pd.Series()
    
    def get_top_queries_by_duration(self, top_n=10):
        """Get top queries by average duration"""
        query = """
        SELECT TOP (?)
            SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                END - qs.statement_start_offset)/2) + 1) AS query_text,
            qs.execution_count,
            qs.total_elapsed_time / 1000.0 as total_elapsed_ms,
            (qs.total_elapsed_time / qs.execution_count) / 1000.0 as avg_duration_ms,
            qs.max_elapsed_time / 1000.0 as max_duration_ms,
            qs.last_execution_time
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        ORDER BY avg_duration_ms DESC
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            if not df.empty:
                df['query_text_short'] = df['query_text'].apply(
                    lambda x: (str(x)[:60] + '...') if len(str(x)) > 60 else str(x)
                )
            return df
        except Exception as e:
            logger.error(f"Error getting top queries by duration: {e}")
            return pd.DataFrame()
    
    def get_top_queries_by_cpu(self, top_n=10):
        """Get top queries by total CPU time"""
        query = """
        SELECT TOP (?)
            SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                END - qs.statement_start_offset)/2) + 1) AS query_text,
            qs.execution_count,
            qs.total_worker_time / 1000.0 as total_cpu_ms,
            (qs.total_worker_time / qs.execution_count) / 1000.0 as avg_cpu_ms,
            qs.last_execution_time
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        ORDER BY total_cpu_ms DESC
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            if not df.empty:
                df['query_text_short'] = df['query_text'].apply(
                    lambda x: (str(x)[:60] + '...') if len(str(x)) > 60 else str(x)
                )
            return df
        except Exception as e:
            logger.error(f"Error getting top queries by CPU: {e}")
            return pd.DataFrame()
    
    def get_top_queries_by_reads(self, top_n=10):
        """Get top queries by logical reads"""
        query = """
        SELECT TOP (?)
            SUBSTRING(st.text, (qs.statement_start_offset/2)+1,
                ((CASE qs.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE qs.statement_end_offset
                END - qs.statement_start_offset)/2) + 1) AS query_text,
            qs.execution_count,
            qs.total_logical_reads,
            qs.total_logical_reads / qs.execution_count as avg_logical_reads,
            qs.last_execution_time
        FROM sys.dm_exec_query_stats qs
        CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) st
        ORDER BY total_logical_reads DESC
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            if not df.empty:
                df['query_text_short'] = df['query_text'].apply(
                    lambda x: (str(x)[:60] + '...') if len(str(x)) > 60 else str(x)
                )
            return df
        except Exception as e:
            logger.error(f"Error getting top queries by reads: {e}")
            return pd.DataFrame()
    
    def get_throughput_stats(self):
        """Get throughput statistics (batch requests, transactions)"""
        query = """
        SELECT 
            cntr_value as batch_requests_sec
        FROM sys.dm_os_performance_counters
        WHERE counter_name = 'Batch Requests/sec'
        AND object_name LIKE '%SQL Statistics%'
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['batch_requests_sec'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting throughput stats: {e}")
            return 0
    
    # ==================== CPU & MEMORY ====================
    
    def get_cpu_stats(self):
        """Get CPU utilization statistics"""
        query = """
        SELECT TOP 1
            SQLProcessUtilization AS sql_cpu_pct,
            SystemIdle AS system_idle_pct,
            100 - SystemIdle - SQLProcessUtilization AS other_cpu_pct
        FROM (
            SELECT 
                record.value('(./Record/@id)[1]', 'int') AS record_id,
                record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]', 'int') AS SystemIdle,
                record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS SQLProcessUtilization,
                timestamp
            FROM (
                SELECT timestamp, CONVERT(xml, record) AS record 
                FROM sys.dm_os_ring_buffers 
                WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR' 
                AND record LIKE '%<SystemHealth>%'
            ) AS x
        ) AS y
        ORDER BY record_id DESC
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0] if not df.empty else pd.Series({'sql_cpu_pct': 0, 'system_idle_pct': 100, 'other_cpu_pct': 0})
        except Exception as e:
            logger.error(f"Error getting CPU stats: {e}")
            return pd.Series({'sql_cpu_pct': 0, 'system_idle_pct': 100, 'other_cpu_pct': 0})
    
    def get_memory_stats(self):
        """Get memory statistics"""
        query = """
        SELECT 
            (SELECT cntr_value FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Buffer cache hit ratio' 
             AND object_name LIKE '%Buffer Manager%') as buffer_cache_hit_ratio,
            (SELECT cntr_value FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Page life expectancy' 
             AND object_name LIKE '%Buffer Manager%') as page_life_expectancy,
            (SELECT cntr_value/1024 FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Total Server Memory (KB)' 
             AND object_name LIKE '%Memory Manager%') as total_server_memory_mb,
            (SELECT cntr_value/1024 FROM sys.dm_os_performance_counters 
             WHERE counter_name = 'Target Server Memory (KB)' 
             AND object_name LIKE '%Memory Manager%') as target_server_memory_mb,
            (SELECT SUM(pages_kb)/1024 FROM sys.dm_os_memory_clerks) as total_memory_mb
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0] if not df.empty else pd.Series()
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return pd.Series()
    
    def get_scheduler_queue_length(self):
        """Get runnable tasks count (scheduler queue length)"""
        query = """
        SELECT SUM(runnable_tasks_count) as total_runnable_tasks
        FROM sys.dm_os_schedulers
        WHERE scheduler_id < 255
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['total_runnable_tasks'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting scheduler queue length: {e}")
            return 0
    
    # ==================== DISK & I/O HEALTH ====================
    
    def get_io_latency_stats(self):
        """Get I/O latency statistics by database"""
        query = """
        SELECT TOP 10
            DB_NAME(a.database_id) AS database_name,
            b.name as file_name,
            b.type_desc as file_type,
            a.num_of_reads,
            a.num_of_writes,
            CASE WHEN a.num_of_reads = 0 THEN 0 
                 ELSE a.io_stall_read_ms / a.num_of_reads END AS avg_read_latency_ms,
            CASE WHEN a.num_of_writes = 0 THEN 0 
                 ELSE a.io_stall_write_ms / a.num_of_writes END AS avg_write_latency_ms,
            a.io_stall_read_ms + a.io_stall_write_ms AS total_io_stall_ms
        FROM sys.dm_io_virtual_file_stats(NULL, NULL) a
        INNER JOIN sys.master_files b ON a.database_id = b.database_id 
            AND a.file_id = b.file_id
        WHERE a.num_of_reads > 0 OR a.num_of_writes > 0
        ORDER BY total_io_stall_ms DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting I/O latency stats: {e}")
            return pd.DataFrame()
    
    def get_database_file_sizes(self):
        """Get database file sizes and growth"""
        query = """
        SELECT TOP 20
            DB_NAME(database_id) AS database_name,
            name AS file_name,
            type_desc AS file_type,
            size * 8.0 / 1024 AS size_mb,
            max_size * 8.0 / 1024 AS max_size_mb,
            growth * 8.0 / 1024 AS growth_mb,
            is_percent_growth
        FROM sys.master_files
        WHERE database_id > 4
        ORDER BY size DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting database file sizes: {e}")
            return pd.DataFrame()
    
    # ==================== INDEX & QUERY OPTIMIZATION ====================
    
    def get_index_fragmentation(self):
        """Get index fragmentation statistics"""
        query = """
        SELECT TOP 20
            OBJECT_NAME(ips.object_id) AS table_name,
            i.name AS index_name,
            ips.index_type_desc,
            ips.avg_fragmentation_in_percent,
            ips.page_count
        FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') ips
        INNER JOIN sys.indexes i ON ips.object_id = i.object_id 
            AND ips.index_id = i.index_id
        WHERE ips.avg_fragmentation_in_percent > 10
        AND ips.page_count > 100
        ORDER BY ips.avg_fragmentation_in_percent DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting index fragmentation: {e}")
            return pd.DataFrame()
    
    def get_unused_indexes(self):
        """Get unused indexes"""
        query = """
        SELECT TOP 20
            OBJECT_NAME(i.object_id) AS table_name,
            i.name AS index_name,
            i.type_desc AS index_type,
            s.user_seeks,
            s.user_scans,
            s.user_lookups,
            s.user_updates
        FROM sys.indexes i
        LEFT JOIN sys.dm_db_index_usage_stats s 
            ON i.object_id = s.object_id AND i.index_id = s.index_id
        WHERE OBJECTPROPERTY(i.object_id, 'IsUserTable') = 1
        AND i.index_id > 0
        AND s.user_seeks + s.user_scans + s.user_lookups = 0
        ORDER BY s.user_updates DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting unused indexes: {e}")
            return pd.DataFrame()
    
    def get_missing_indexes(self):
        """Get missing index recommendations"""
        query = """
        SELECT TOP 20
            OBJECT_NAME(mid.object_id, mid.database_id) AS table_name,
            migs.avg_total_user_cost * (migs.avg_user_impact / 100.0) * (migs.user_seeks + migs.user_scans) AS improvement_measure,
            mid.equality_columns,
            mid.inequality_columns,
            mid.included_columns,
            migs.user_seeks,
            migs.user_scans
        FROM sys.dm_db_missing_index_groups mig
        INNER JOIN sys.dm_db_missing_index_group_stats migs 
            ON migs.group_handle = mig.index_group_handle
        INNER JOIN sys.dm_db_missing_index_details mid 
            ON mig.index_handle = mid.index_handle
        WHERE mid.database_id = DB_ID()
        ORDER BY improvement_measure DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting missing indexes: {e}")
            return pd.DataFrame()
    
    # ==================== BLOCKING & CONCURRENCY ====================
    
    def get_blocking_sessions(self):
        """Get current blocking sessions"""
        query = """
        SELECT 
            r.session_id,
            r.blocking_session_id,
            s.login_name,
            s.host_name,
            DB_NAME(r.database_id) AS database_name,
            r.wait_type,
            r.wait_time,
            r.status,
            SUBSTRING(st.text, (r.statement_start_offset/2)+1,
                ((CASE r.statement_end_offset
                    WHEN -1 THEN DATALENGTH(st.text)
                    ELSE r.statement_end_offset
                END - r.statement_start_offset)/2) + 1) AS query_text
        FROM sys.dm_exec_requests r
        INNER JOIN sys.dm_exec_sessions s ON r.session_id = s.session_id
        CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) st
        WHERE r.blocking_session_id > 0
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting blocking sessions: {e}")
            return pd.DataFrame()
    
    def get_deadlock_count(self):
        """Get deadlock count"""
        query = """
        SELECT cntr_value as deadlock_count
        FROM sys.dm_os_performance_counters
        WHERE counter_name = 'Number of Deadlocks/sec'
        AND instance_name = '_Total'
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['deadlock_count'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting deadlock count: {e}")
            return 0
    
    # ==================== AVAILABILITY & RELIABILITY ====================
    
    def get_sql_server_uptime(self):
        """Get SQL Server uptime"""
        query = """
        SELECT DATEDIFF(SECOND, sqlserver_start_time, GETDATE()) as uptime_seconds
        FROM sys.dm_os_sys_info
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['uptime_seconds'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting SQL Server uptime: {e}")
            return 0
    
    def get_error_log_stats(self):
        """Get error log statistics"""
        query = """
        SELECT 
            COUNT(*) as error_count
        FROM sys.dm_os_ring_buffers
        WHERE ring_buffer_type = 'RING_BUFFER_EXCEPTION'
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['error_count'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting error log stats: {e}")
            return 0
    
    # ==================== BACKUP & RECOVERY ====================
    
    def get_backup_status(self):
        """Get backup status for all databases"""
        query = """
        SELECT TOP 20
            d.name AS database_name,
            d.recovery_model_desc,
            MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END) AS last_full_backup,
            MAX(CASE WHEN b.type = 'I' THEN b.backup_finish_date END) AS last_diff_backup,
            MAX(CASE WHEN b.type = 'L' THEN b.backup_finish_date END) AS last_log_backup,
            DATEDIFF(HOUR, MAX(CASE WHEN b.type = 'D' THEN b.backup_finish_date END), GETDATE()) AS hours_since_full
        FROM sys.databases d
        LEFT JOIN msdb.dbo.backupset b ON d.name = b.database_name
        WHERE d.database_id > 4
        GROUP BY d.name, d.recovery_model_desc
        ORDER BY hours_since_full DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting backup status: {e}")
            return pd.DataFrame()
    
    # ==================== SECURITY & ACCESS ====================
    
    def get_failed_login_attempts(self):
        """Get failed login attempts count"""
        query = """
        SELECT COUNT(*) as failed_logins
        FROM sys.dm_exec_sessions
        WHERE status = 'dormant'
        """
        try:
            df = pd.read_sql(query, self.connection)
            return df.iloc[0]['failed_logins'] if not df.empty else 0
        except Exception as e:
            logger.error(f"Error getting failed login attempts: {e}")
            return 0
    
    def get_connection_stats(self):
        """Get connection statistics"""
        query = """
        SELECT 
            login_name,
            COUNT(*) as connection_count,
            MAX(login_time) as last_login
        FROM sys.dm_exec_sessions
        WHERE is_user_process = 1
        GROUP BY login_name
        ORDER BY connection_count DESC
        """
        try:
            return pd.read_sql(query, self.connection)
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
            return pd.DataFrame()
    
    # ==================== ORIGINAL WAIT STATS METHODS ====================
    
    # ==================== ORIGINAL WAIT STATS METHODS ====================
    
    def get_top_wait_types(self, top_n=5):
        """Get top N wait types"""
        query = """
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
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            df['wait_time_seconds'] = df['wait_time_ms'] / 1000.0
            return df
        except Exception as e:
            logger.error(f"Error getting top wait types: {e}")
            return pd.DataFrame()
    
    def get_query_waits(self, top_n=10):
        """Get top queries by total wait time"""
        query = """
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
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            # Truncate long queries for display
            if not df.empty and 'query_text' in df.columns:
                df['query_text_short'] = df['query_text'].apply(
                    lambda x: (x[:100] + '...') if len(str(x)) > 100 else x
                )
            return df
        except Exception as e:
            logger.error(f"Error getting query waits: {e}")
            return pd.DataFrame()
    
    def get_wait_distribution(self):
        """Get wait type distribution for pie chart"""
        query = """
        SELECT 
            wait_type,
            wait_time_ms,
            CAST(100.0 * wait_time_ms / SUM(wait_time_ms) OVER() AS DECIMAL(5,2)) AS [percentage]
        FROM sys.dm_os_wait_stats
        WHERE wait_type NOT IN (
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
        """
        try:
            df = pd.read_sql(query, self.connection)
            # Group smaller wait types into "Others"
            df = df.sort_values('wait_time_ms', ascending=False)
            top_10 = df.head(10)
            others = pd.DataFrame({
                'wait_type': ['Others'],
                'wait_time_ms': [df.iloc[10:]['wait_time_ms'].sum()],
                'percentage': [df.iloc[10:]['percentage'].sum()]
            })
            result = pd.concat([top_10, others], ignore_index=True)
            return result
        except Exception as e:
            logger.error(f"Error getting wait distribution: {e}")
            return pd.DataFrame()
    
    def get_average_wait_times(self, top_n=15):
        """Get average wait times for different wait types"""
        query = """
        SELECT TOP (?)
            wait_type,
            waiting_tasks_count,
            wait_time_ms,
            CASE 
                WHEN waiting_tasks_count > 0 
                THEN wait_time_ms / waiting_tasks_count 
                ELSE 0 
            END AS avg_wait_time_ms
        FROM sys.dm_os_wait_stats
        WHERE wait_type NOT IN (
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
        AND waiting_tasks_count > 0
        ORDER BY avg_wait_time_ms DESC
        """
        try:
            df = pd.read_sql(query, self.connection, params=[top_n])
            return df
        except Exception as e:
            logger.error(f"Error getting average wait times: {e}")
            return pd.DataFrame()
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Connection closed")


# Wait type categories
WAIT_CATEGORIES = {
    'CPU': ['SOS_SCHEDULER_YIELD', 'CXPACKET', 'CXCONSUMER', 'THREADPOOL', 'SOS_WORK_DISPATCHER'],
    'IO': ['PAGEIOLATCH_SH', 'PAGEIOLATCH_EX', 'PAGEIOLATCH_UP', 'WRITELOG', 'IO_COMPLETION', 
           'ASYNC_IO_COMPLETION', 'BACKUPIO', 'LOGBUFFER'],
    'Memory': ['RESOURCE_SEMAPHORE', 'MEMORY_ALLOCATION_EXT', 'CMEMTHREAD', 'SOS_RESERVEDMEMBLOCKLIST'],
    'Latch': ['LATCH_EX', 'LATCH_SH', 'LATCH_UP', 'LATCH_DT', 'PAGELATCH_EX', 'PAGELATCH_SH', 
              'PAGELATCH_UP', 'ACCESS_METHODS_DATASET_PARENT'],
    'Lock': ['LCK_M_S', 'LCK_M_U', 'LCK_M_X', 'LCK_M_IS', 'LCK_M_IU', 'LCK_M_IX', 'LCK_M_SCH_S', 
             'LCK_M_SCH_M', 'LCK_M_RIn_NL', 'LCK_M_RIn_S', 'LCK_M_RIn_U', 'LCK_M_RIn_X']
}

def categorize_wait_type(wait_type):
    """Categorize a wait type into CPU, IO, Memory, Latch, Lock, or Other"""
    for category, wait_types in WAIT_CATEGORIES.items():
        if any(wt in wait_type for wt in wait_types):
            return category
    return 'Other'


# Initialize the Dash app
app = Dash(__name__, suppress_callback_exceptions=True)

# Load available databases from config
def load_database_options():
    """Load available database options from config file"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        if 'databases' in config:
            return [{'label': f"{name} ({db_config.get('description', db_config['database'])})", 
                     'value': name} 
                    for name, db_config in config['databases'].items()]
        else:
            # Old format
            return [{'label': config.get('database', 'default'), 'value': 'default'}]
    except Exception as e:
        logger.error(f"Error loading database options: {e}")
        return [{'label': 'default', 'value': 'default'}]

database_options = load_database_options()
default_db = 'master' if any(opt['value'] == 'master' for opt in database_options) else database_options[0]['value']

# Define the layout with professional styling and multi-page tabs
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("SQL Server Monitoring Dashboard", style={
            'textAlign': 'center',
            'color': '#ffffff',
            'margin': '0',
            'padding': '15px',
            'fontSize': '28px'
        }),
        html.Div([
            html.Label("Database: ", style={'color': '#ffffff', 'marginRight': '10px', 'fontSize': '14px'}),
            dcc.Dropdown(
                id='database-selector',
                options=database_options,
                value=default_db,
                style={'width': '250px', 'display': 'inline-block', 'marginRight': '30px'},
                clearable=False
            ),
            html.Label("Refresh: ", style={'color': '#ffffff', 'marginRight': '10px', 'fontSize': '14px'}),
            dcc.Dropdown(
                id='refresh-interval',
                options=[
                    {'label': '5 sec', 'value': 5},
                    {'label': '10 sec', 'value': 10},
                    {'label': '30 sec', 'value': 30},
                    {'label': '60 sec', 'value': 60},
                    {'label': 'Manual', 'value': 0}
                ],
                value=30,
                style={'width': '120px', 'display': 'inline-block'}
            ),
            html.Div(id='status-message', style={
                'display': 'inline-block',
                'marginLeft': '20px',
                'color': '#4CAF50',
                'fontSize': '14px'
            })
        ], style={'textAlign': 'center', 'padding': '10px'})
    ], style={
        'backgroundColor': '#2E86C1',
        'marginBottom': '0',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    # Navigation Tabs
    html.Div([
        dcc.Tabs(id='page-tabs', value='overview', children=[
            dcc.Tab(label='📊 Overview', value='overview', style={'padding': '12px', 'fontWeight': 'bold'}),
            dcc.Tab(label='⚡ Performance', value='performance', style={'padding': '12px', 'fontWeight': 'bold'}),
            dcc.Tab(label='💾 Storage', value='storage', style={'padding': '12px', 'fontWeight': 'bold'}),
            dcc.Tab(label='🔒 Reliability', value='reliability', style={'padding': '12px', 'fontWeight': 'bold'}),
        ], style={'backgroundColor': '#3498DB'}),
    ], style={'backgroundColor': '#3498DB', 'marginBottom': '20px'}),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # in milliseconds
        n_intervals=0
    ),
    
    # Page content
    html.Div(id='page-content', style={'padding': '20px', 'backgroundColor': '#f5f5f5', 'minHeight': '85vh'})
    
], style={
    'backgroundColor': '#f5f5f5',
    'minHeight': '100vh',
    'fontFamily': 'Arial, sans-serif',
    'margin': '0',
    'padding': '0'
})


# ==================== HELPER FUNCTIONS ====================

def create_kpi_card(title, value, subtitle='', color='#2196F3', icon=''):
    """Create a KPI card component"""
    return html.Div([
        html.Div([
            html.Span(icon, style={'fontSize': '24px', 'marginRight': '10px'}) if icon else None,
            html.Div(title, style={
                'fontSize': '11px',
                'color': '#888',
                'textTransform': 'uppercase',
                'marginBottom': '8px',
                'fontWeight': '600'
            }),
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Div(str(value), style={
            'fontSize': '28px',
            'fontWeight': 'bold',
            'color': color,
            'marginBottom': '5px'
        }),
        html.Div(subtitle, style={
            'fontSize': '11px',
            'color': '#666'
        })
    ], style={
        'backgroundColor': 'white',
        'padding': '18px',
        'borderRadius': '8px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.08)',
        'textAlign': 'center',
        'minWidth': '140px',
        'flex': '1',
        'minHeight': '110px'
    })


def create_chart_container(title, chart_id):
    """Create a chart container with title"""
    return html.Div([
        html.H3(title, style={
            'color': '#333',
            'fontSize': '16px',
            'marginBottom': '15px',
            'fontWeight': '600'
        }),
        dcc.Graph(id=chart_id, config={'displayModeBar': False})
    ], style={
        'backgroundColor': 'white',
        'padding': '20px',
        'borderRadius': '8px',
        'boxShadow': '0 2px 8px rgba(0,0,0,0.08)',
        'marginBottom': '20px'
    })


def get_health_color(value, type='cpu'):
    """Get health indicator color based on value and type"""
    if type == 'cpu':
        if value < 70: return '#4CAF50'
        elif value < 85: return '#FFA726'
        else: return '#EF5350'
    elif type == 'memory_ple':
        if value > 300: return '#4CAF50'
        elif value > 150: return '#FFA726'
        else: return '#EF5350'
    elif type == 'io_latency':
        if value < 10: return '#4CAF50'
        elif value < 20: return '#FFA726'
        else: return '#EF5350'
    return '#2196F3'


# ==================== CALLBACKS ====================

@app.callback(
    Output('interval-component', 'interval'),
    Input('refresh-interval', 'value')
)
def update_interval(refresh_value):
    """Update the refresh interval"""
    if refresh_value == 0:
        return 86400000  # 24 hours (essentially manual)
    return refresh_value * 1000


@app.callback(
    [Output('page-content', 'children'),
     Output('status-message', 'children')],
    [Input('page-tabs', 'value'),
     Input('interval-component', 'n_intervals'),
     Input('database-selector', 'value')]
)
def render_page_content(active_tab, n, selected_database):
    """Render the appropriate page based on selected tab"""
    try:
        # Connect to database
        db = SQLServerMonitor(database_name=selected_database)
        if not db.connect():
            return html.Div("❌ Failed to connect to SQL Server", style={'padding': '20px', 'color': 'red'}), "❌ Connection failed"
        
        status = f"✓ Updated: {datetime.now().strftime('%H:%M:%S')} | DB: {db.database_name}"
        
        if active_tab == 'overview':
            content = render_overview_page(db)
        elif active_tab == 'performance':
            content = render_performance_page(db)
        elif active_tab == 'storage':
            content = render_storage_page(db)
        elif active_tab == 'reliability':
            content = render_reliability_page(db)
        else:
            content = html.Div("Page not found")
        
        db.close()
        return content, status
        
    except Exception as e:
        logger.error(f"Error rendering page: {e}")
        return html.Div(f"❌ Error: {str(e)}", style={'padding': '20px', 'color': 'red'}), f"❌ Error: {str(e)}"


# ==================== PAGE 1: OVERVIEW ====================

def render_overview_page(db):
    """Render the Overview dashboard page"""
    try:
        # Get data for overview
        cpu_stats = db.get_cpu_stats()
        memory_stats = db.get_memory_stats()
        io_stats = db.get_io_latency_stats()
        blocking = db.get_blocking_sessions()
        query_perf = db.get_query_performance_stats()
        
        # Calculate health indicators
        sql_cpu = cpu_stats.get('sql_cpu_pct', 0)
        memory_pressure = 'Yes' if memory_stats.get('page_life_expectancy', 1000) < 300 else 'No'
        avg_io_latency = io_stats['avg_read_latency_ms'].mean() if not io_stats.empty else 0
        blocking_count = len(blocking)
        avg_query_latency = query_perf.get('avg_duration_ms', 0) if not query_perf.empty else 0
        
        # Calculate overall health score
        health_score = 100
        if sql_cpu > 80: health_score -= 20
        elif sql_cpu > 60: health_score -= 10
        if memory_stats.get('page_life_expectancy', 1000) < 300: health_score -= 20
        if avg_io_latency > 20: health_score -= 20
        elif avg_io_latency > 10: health_score -= 10
        if blocking_count > 5: health_score -= 15
        elif blocking_count > 0: health_score -= 5
        
        health_color = '#4CAF50' if health_score >= 80 else '#FFA726' if health_score >= 60 else '#EF5350'
        
        # Summary KPI
        summary_kpis = html.Div([
            create_kpi_card('Overall Health', f'{health_score}%', 'System score', health_color, '✅'),
            create_kpi_card('Active Alerts', str(blocking_count), 'Blocking sessions', '#EF5350' if blocking_count > 0 else '#4CAF50', '⚠️'),
            create_kpi_card('Avg Query Latency', f'{avg_query_latency:.1f}ms', 'Response time', get_health_color(avg_query_latency, 'io_latency'), '⏱️'),
            create_kpi_card('SQL CPU %', f'{sql_cpu:.1f}%', 'Processor usage', get_health_color(sql_cpu, 'cpu'), '💻'),
            create_kpi_card('Memory Pressure', memory_pressure, f'PLE: {memory_stats.get("page_life_expectancy", 0):.0f}s', 
                          '#EF5350' if memory_pressure == 'Yes' else '#4CAF50', '🧠'),
            create_kpi_card('Avg I/O Latency', f'{avg_io_latency:.1f}ms', 'Read latency', get_health_color(avg_io_latency, 'io_latency'), '💾'),
        ], style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '15px',
            'marginBottom': '25px'
        })
        
        # CPU & Memory gauges
        cpu_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=sql_cpu,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "SQL Server CPU %", 'font': {'size': 16}},
            delta={'reference': 50, 'increasing': {'color': "red"}},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': get_health_color(sql_cpu, 'cpu')},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 70], 'color': '#E8F5E9'},
                    {'range': [70, 85], 'color': '#FFF3E0'},
                    {'range': [85, 100], 'color': '#FFEBEE'}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90}}))
        cpu_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        
        ple_value = memory_stats.get('page_life_expectancy', 0)
        memory_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=ple_value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Page Life Expectancy (s)", 'font': {'size': 16}},
            delta={'reference': 300, 'increasing': {'color': "green"}},
            gauge={
                'axis': {'range': [0, 600], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': get_health_color(ple_value, 'memory_ple')},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 150], 'color': '#FFEBEE'},
                    {'range': [150, 300], 'color': '#FFF3E0'},
                    {'range': [300, 600], 'color': '#E8F5E9'}],
                'threshold': {
                    'line': {'color': "green", 'width': 4},
                    'thickness': 0.75,
                    'value': 300}}))
        memory_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        
        # Wait category distribution
        top_waits = db.get_top_wait_types(15)
        top_waits['category'] = top_waits['wait_type'].apply(categorize_wait_type)
        category_stats = top_waits.groupby('category').agg({
            'wait_time_ms': 'sum',
            'percentage': 'sum'
        }).reset_index().sort_values('wait_time_ms', ascending=False)
        
        wait_dist_fig = go.Figure()
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DFE6E9']
        wait_dist_fig.add_trace(go.Pie(
            labels=category_stats['category'],
            values=category_stats['wait_time_ms'],
            hole=0.5,
            marker_colors=colors[:len(category_stats)],
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} ms<br>%{percent}<extra></extra>'
        ))
        wait_dist_fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True,
            title={'text': 'Wait Category Distribution', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}}
        )
        
        # I/O latency chart
        io_chart_data = io_stats.head(10)
        io_fig = go.Figure()
        io_fig.add_trace(go.Bar(
            y=io_chart_data['database_name'] + '<br>' + io_chart_data['file_type'],
            x=io_chart_data['avg_read_latency_ms'],
            name='Read Latency',
            orientation='h',
            marker_color='#4ECDC4',
            text=io_chart_data['avg_read_latency_ms'].apply(lambda x: f'{x:.1f}'),
            textposition='auto',
            textfont=dict(size=9),
            hovertemplate='<b>%{y}</b><br>Read: %{x:.2f}ms<extra></extra>'
        ))
        io_fig.add_trace(go.Bar(
            y=io_chart_data['database_name'] + '<br>' + io_chart_data['file_type'],
            x=io_chart_data['avg_write_latency_ms'],
            name='Write Latency',
            orientation='h',
            marker_color='#FF6B6B',
            text=io_chart_data['avg_write_latency_ms'].apply(lambda x: f'{x:.1f}'),
            textposition='auto',
            textfont=dict(size=9),
            hovertemplate='<b>%{y}</b><br>Write: %{x:.2f}ms<extra></extra>'
        ))
        io_fig.update_layout(
            barmode='group',
            height=300,
            margin=dict(l=180, r=50, t=40, b=50),
            xaxis_title='Latency (ms)',
            title={'text': 'Top 10 I/O Latency by File', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis={'automargin': True},
            yaxis={'automargin': True, 'tickfont': {'size': 10}}
        )
        
        return html.Div([
            html.H2("System Overview", style={'color': '#333', 'marginBottom': '20px', 'fontSize': '22px'}),
            summary_kpis,
            
            # Row 1: Gauges
            html.Div([
                html.Div([dcc.Graph(figure=cpu_gauge, config={'displayModeBar': False})], 
                        style={'width': '32%', 'display': 'inline-block', 'backgroundColor': 'white', 
                               'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=memory_gauge, config={'displayModeBar': False})], 
                        style={'width': '32%', 'display': 'inline-block', 'backgroundColor': 'white', 
                               'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=wait_dist_fig, config={'displayModeBar': False})], 
                        style={'width': '32%', 'display': 'inline-block', 'backgroundColor': 'white', 
                               'padding': '15px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'verticalAlign': 'top'})
            ], style={'marginBottom': '20px'}),
            
            # Row 2: I/O Latency
            html.Div([
                dcc.Graph(figure=io_fig, config={'displayModeBar': False})
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 
                     'boxShadow': '0 2px 8px rgba(0,0,0,0.08)'})
        ])
        
    except Exception as e:
        logger.error(f"Error rendering overview page: {e}")
        return html.Div(f"Error loading overview: {str(e)}", style={'color': 'red'})
    


# ==================== PAGE 2: PERFORMANCE ====================

def render_performance_page(db):
    """Render the Performance dashboard page"""
    try:
        # Get performance data
        query_perf = db.get_query_performance_stats()
        top_duration = db.get_top_queries_by_duration(10)
        top_cpu = db.get_top_queries_by_cpu(10)
        top_reads = db.get_top_queries_by_reads(10)
        top_waits = db.get_top_wait_types(15)
        top_waits['category'] = top_waits['wait_type'].apply(categorize_wait_type)
        
        # Performance KPIs
        perf_kpis = html.Div([
            create_kpi_card('Avg Query Duration', f'{query_perf.get("avg_duration_ms", 0):.2f}ms', 
                          'Mean latency', '#4ECDC4', '⚡'),
            create_kpi_card('95th Percentile', f'{query_perf.get("p95_duration_ms", 0):.2f}ms', 
                          'P95 latency', '#FFA726', '📊'),
            create_kpi_card('99th Percentile', f'{query_perf.get("p99_duration_ms", 0):.2f}ms', 
                          'P99 latency', '#EF5350', '📈'),
            create_kpi_card('Total Executions', f'{query_perf.get("total_executions", 0):,.0f}', 
                          'Query count', '#45B7D1', '🔄'),
            create_kpi_card('Query Count', f'{query_perf.get("query_count", 0):,.0f}', 
                          'Unique queries', '#96CEB4', '📝'),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'marginBottom': '25px'})
        
        # Top queries by duration
        duration_fig = go.Figure()
        if not top_duration.empty:
            duration_data = top_duration.head(10).sort_values('avg_duration_ms')
            duration_fig.add_trace(go.Bar(
                y=duration_data['query_text_short'],
                x=duration_data['avg_duration_ms'],
                orientation='h',
                marker_color='#4ECDC4',
                text=duration_data['execution_count'].apply(lambda x: f'{x:,}'),
                texttemplate='%{text}',
                textposition='auto',
                textfont=dict(size=10),
                hovertemplate='<b>%{y}</b><br>Avg Duration: %{x:.2f}ms<br>Executions: %{text}<extra></extra>'
            ))
        duration_fig.update_layout(
            title={'text': 'Top 10 Queries by Avg Duration', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Average Duration (ms)',
            height=400,
            margin=dict(l=250, r=80, t=40, b=40),
            xaxis={'automargin': True}
        )
        
        # Top queries by CPU
        cpu_fig = go.Figure()
        if not top_cpu.empty:
            cpu_data = top_cpu.head(10).sort_values('total_cpu_ms')
            cpu_fig.add_trace(go.Bar(
                y=cpu_data['query_text_short'],
                x=cpu_data['total_cpu_ms'],
                orientation='h',
                marker_color='#FF6B6B',
                text=cpu_data['total_cpu_ms'].apply(lambda x: f'{x/1000:.1f}s' if x > 1000 else f'{x:.0f}ms'),
                textposition='auto',
                textfont=dict(size=10),
                hovertemplate='<b>%{y}</b><br>Total CPU: %{x:,.0f}ms<extra></extra>'
            ))
        cpu_fig.update_layout(
            title={'text': 'Top 10 Queries by Total CPU Time', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Total CPU Time (ms)',
            height=400,
            margin=dict(l=250, r=80, t=40, b=40),
            xaxis={'automargin': True}
        )
        
        # Top queries by reads
        reads_fig = go.Figure()
        if not top_reads.empty:
            reads_data = top_reads.head(10).sort_values('total_logical_reads')
            reads_fig.add_trace(go.Bar(
                y=reads_data['query_text_short'],
                x=reads_data['total_logical_reads'],
                orientation='h',
                marker_color='#FFA726',
                text=reads_data['total_logical_reads'].apply(lambda x: f'{x/1000000:.1f}M' if x > 1000000 else f'{x/1000:.1f}K'),
                textposition='auto',
                textfont=dict(size=10),
                hovertemplate='<b>%{y}</b><br>Reads: %{x:,.0f}<extra></extra>'
            ))
        reads_fig.update_layout(
            title={'text': 'Top 10 Queries by Logical Reads', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Total Logical Reads',
            height=400,
            margin=dict(l=250, r=80, t=40, b=40),
            xaxis={'automargin': True}
        )
        
        # Wait statistics
        wait_fig = go.Figure()
        top_10_waits = top_waits.head(10).sort_values('wait_time_ms')
        bar_colors = ['#FF6B6B' if cat == 'CPU' else 
                      '#4ECDC4' if cat == 'IO' else 
                      '#45B7D1' if cat == 'Memory' else 
                      '#96CEB4' if cat == 'Latch' else 
                      '#FFEAA7' if cat == 'Lock' else '#DFE6E9' 
                      for cat in top_10_waits['category']]
        wait_fig.add_trace(go.Bar(
            y=top_10_waits['wait_type'],
            x=top_10_waits['wait_time_ms'] / 1000,
            orientation='h',
            marker_color=bar_colors,
            text=top_10_waits['percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='auto',
            textfont=dict(size=10, color='white'),
            hovertemplate='<b>%{y}</b><br>Wait Time: %{x:.2f}s<br>Percentage: %{text}<extra></extra>'
        ))
        wait_fig.update_layout(
            title={'text': 'Top 10 Wait Types by Total Time', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Wait Time (seconds)',
            height=400,
            margin=dict(l=200, r=80, t=40, b=40),
            xaxis={'automargin': True},
            yaxis={'automargin': True}
        )
        
        return html.Div([
            html.H2("Query Performance & Workload", style={'color': '#333', 'marginBottom': '20px', 'fontSize': '22px'}),
            perf_kpis,
            
            # Charts Row 1
            html.Div([
                html.Div([dcc.Graph(figure=duration_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=cpu_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'verticalAlign': 'top'})
            ], style={'marginBottom': '20px'}),
            
            # Charts Row 2
            html.Div([
                html.Div([dcc.Graph(figure=reads_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=wait_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'verticalAlign': 'top'})
            ])
        ])
        
    except Exception as e:
        logger.error(f"Error rendering performance page: {e}")
        return html.Div(f"Error loading performance: {str(e)}", style={'color': 'red'})


# ==================== PAGE 3: STORAGE ====================

def render_storage_page(db):
    """Render the Storage dashboard page"""
    try:
        # Get storage data
        io_stats = db.get_io_latency_stats()
        file_sizes = db.get_database_file_sizes()
        index_frag = db.get_index_fragmentation()
        missing_indexes = db.get_missing_indexes()
        
        # Storage KPIs
        avg_read_lat = io_stats['avg_read_latency_ms'].mean() if not io_stats.empty else 0
        avg_write_lat = io_stats['avg_write_latency_ms'].mean() if not io_stats.empty else 0
        total_size = file_sizes['size_mb'].sum() if not file_sizes.empty else 0
        fragmented_indexes = len(index_frag) if not index_frag.empty else 0
        
        storage_kpis = html.Div([
            create_kpi_card('Avg Read Latency', f'{avg_read_lat:.2f}ms', 
                          'Disk reads', get_health_color(avg_read_lat, 'io_latency'), '📖'),
            create_kpi_card('Avg Write Latency', f'{avg_write_lat:.2f}ms', 
                          'Disk writes', get_health_color(avg_write_lat, 'io_latency'), '✍️'),
            create_kpi_card('Total DB Size', f'{total_size/1024:.2f}GB', 
                          'All databases', '#45B7D1', '💾'),
            create_kpi_card('Fragmented Indexes', str(fragmented_indexes), 
                          '> 10% fragmentation', '#EF5350' if fragmented_indexes > 10 else '#4CAF50', '🔧'),
            create_kpi_card('Missing Indexes', str(len(missing_indexes)), 
                          'Recommendations', '#FFA726', '⚠️'),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'marginBottom': '25px'})
        
        # I/O Latency chart
        io_fig = go.Figure()
        if not io_stats.empty:
            io_data = io_stats.head(15)
            io_fig.add_trace(go.Bar(
                y=io_data['database_name'] + ' - ' + io_data['file_type'],
                x=io_data['avg_read_latency_ms'],
                name='Read',
                orientation='h',
                marker_color='#4ECDC4'
            ))
            io_fig.add_trace(go.Bar(
                y=io_data['database_name'] + ' - ' + io_data['file_type'],
                x=io_data['avg_write_latency_ms'],
                name='Write',
                orientation='h',
                marker_color='#FF6B6B'
            ))
        io_fig.update_layout(
            title={'text': 'I/O Latency by Database File', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Latency (ms)',
            barmode='group',
            height=450,
            margin=dict(l=200, r=20, t=40, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        # File sizes chart
        size_fig = go.Figure()
        if not file_sizes.empty:
            size_data = file_sizes.head(15)
            colors_map = {'ROWS': '#4ECDC4', 'LOG': '#FF6B6B'}
            for file_type in size_data['file_type'].unique():
                type_data = size_data[size_data['file_type'] == file_type]
                size_fig.add_trace(go.Bar(
                    y=type_data['database_name'],
                    x=type_data['size_mb'],
                    name=file_type,
                    orientation='h',
                    marker_color=colors_map.get(file_type, '#96CEB4'),
                    text=type_data['size_mb'].apply(lambda x: f'{x/1024:.1f}GB' if x > 1024 else f'{x:.0f}MB'),
                    textposition='auto',
                    textfont=dict(size=9),
                    hovertemplate='<b>%{y}</b><br>%{fullData.name}: %{text}<extra></extra>'
                ))
        size_fig.update_layout(
            title={'text': 'Database File Sizes', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Size (MB)',
            barmode='stack',
            height=450,
            margin=dict(l=180, r=50, t=40, b=50),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis={'automargin': True},
            yaxis={'automargin': True, 'tickfont': {'size': 11}}
        )
        
        # Index fragmentation table
        frag_table = html.Div("No fragmented indexes", style={'padding': '20px', 'textAlign': 'center', 'color': '#888'})
        if not index_frag.empty:
            frag_table = dash_table.DataTable(
                data=index_frag.to_dict('records'),
                columns=[
                    {'name': 'Table', 'id': 'table_name'},
                    {'name': 'Index', 'id': 'index_name'},
                    {'name': 'Type', 'id': 'index_type_desc'},
                    {'name': 'Fragmentation %', 'id': 'avg_fragmentation_in_percent', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                    {'name': 'Pages', 'id': 'page_count', 'type': 'numeric', 'format': {'specifier': ','}}
                ],
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontSize': '13px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'color': '#495057'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
                    {'if': {'filter_query': '{avg_fragmentation_in_percent} > 30', 'column_id': 'avg_fragmentation_in_percent'},
                     'backgroundColor': '#FFEBEE', 'color': '#C62828'}
                ],
                page_size=10
            )
        
        return html.Div([
            html.H2("Storage & I/O Health", style={'color': '#333', 'marginBottom': '20px', 'fontSize': '22px'}),
            storage_kpis,
            
            # Charts Row
            html.Div([
                html.Div([dcc.Graph(figure=io_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=size_fig, config={'displayModeBar': False})],
                        style={'width': '49%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'verticalAlign': 'top'})
            ], style={'marginBottom': '20px'}),
            
            # Index Fragmentation Table
            html.Div([
                html.H3("Index Fragmentation", style={'color': '#333', 'fontSize': '16px', 'marginBottom': '15px', 'fontWeight': '600'}),
                frag_table
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 
                     'boxShadow': '0 2px 8px rgba(0,0,0,0.08)'})
        ])
        
    except Exception as e:
        logger.error(f"Error rendering storage page: {e}")
        return html.Div(f"Error loading storage: {str(e)}", style={'color': 'red'})


# ==================== PAGE 4: RELIABILITY ====================

def render_reliability_page(db):
    """Render the Reliability dashboard page"""
    try:
        # Get reliability data
        backup_status = db.get_backup_status()
        blocking = db.get_blocking_sessions()
        deadlock_count = db.get_deadlock_count()
        uptime_seconds = db.get_sql_server_uptime()
        connections = db.get_connection_stats()
        
        # Convert uptime to readable format
        uptime_days = uptime_seconds // 86400
        uptime_hours = (uptime_seconds % 86400) // 3600
        uptime_str = f"{uptime_days}d {uptime_hours}h"
        
        # Count databases needing backups
        critical_backups = 0
        if not backup_status.empty:
            critical_backups = len(backup_status[backup_status['hours_since_full'] > 24])
        
        # Reliability KPIs
        reliability_kpis = html.Div([
            create_kpi_card('SQL Server Uptime', uptime_str, 
                          f'{uptime_seconds/86400:.1f} days', '#4CAF50', '⏱️'),
            create_kpi_card('Blocking Sessions', str(len(blocking)), 
                          'Active blocks', '#EF5350' if len(blocking) > 0 else '#4CAF50', '🔒'),
            create_kpi_card('Deadlocks', str(deadlock_count), 
                          'Total count', '#EF5350' if deadlock_count > 0 else '#4CAF50', '💀'),
            create_kpi_card('Backup Alerts', str(critical_backups), 
                          '> 24h since full', '#EF5350' if critical_backups > 0 else '#4CAF50', '💾'),
            create_kpi_card('Active Connections', str(len(connections)), 
                          'User sessions', '#45B7D1', '🔌'),
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '15px', 'marginBottom': '25px'})
        
        # Backup status chart
        backup_fig = go.Figure()
        if not backup_status.empty:
            backup_data = backup_status.head(20).sort_values('hours_since_full', ascending=False)
            colors = ['#EF5350' if x > 24 else '#FFA726' if x > 12 else '#4CAF50' 
                     for x in backup_data['hours_since_full']]
            backup_fig.add_trace(go.Bar(
                y=backup_data['database_name'],
                x=backup_data['hours_since_full'],
                orientation='h',
                marker_color=colors,
                text=backup_data['hours_since_full'].apply(lambda x: f'{x:.0f}h'),
                textposition='auto',
                textfont=dict(size=10, color='white'),
                hovertemplate='<b>%{y}</b><br>Hours: %{x:.1f}<extra></extra>'
            ))
        backup_fig.update_layout(
            title={'text': 'Hours Since Last Full Backup', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Hours',
            height=500,
            margin=dict(l=180, r=50, t=40, b=50),
            xaxis={'automargin': True},
            yaxis={'automargin': True, 'tickfont': {'size': 11}}
        )
        
        # Connections chart
        conn_fig = go.Figure()
        if not connections.empty:
            conn_data = connections.head(15).sort_values('connection_count', ascending=False)
            conn_fig.add_trace(go.Bar(
                x=conn_data['login_name'],
                y=conn_data['connection_count'],
                marker_color='#4ECDC4',
                text=conn_data['connection_count'],
                textposition='outside',
                textfont=dict(size=11),
                hovertemplate='<b>%{x}</b><br>Connections: %{y}<extra></extra>'
            ))
        conn_fig.update_layout(
            title={'text': 'Connections by Login', 'x': 0.5, 'xanchor': 'center', 'font': {'size': 16}},
            xaxis_title='Login Name',
            yaxis_title='Connection Count',
            height=350,
            margin=dict(l=60, r=40, t=60, b=120),
            xaxis={'tickangle': -45, 'automargin': True, 'tickfont': {'size': 10}},
            yaxis={'automargin': True}
        )
        
        # Blocking sessions table
        blocking_table = html.Div("✅ No blocking sessions", 
                                  style={'padding': '20px', 'textAlign': 'center', 'color': '#4CAF50', 'fontSize': '16px'})
        if not blocking.empty:
            blocking['query_text_short'] = blocking['query_text'].apply(
                lambda x: (str(x)[:100] + '...') if len(str(x)) > 100 else str(x)
            )
            blocking_table = dash_table.DataTable(
                data=blocking[['session_id', 'blocking_session_id', 'login_name', 'database_name', 
                              'wait_type', 'wait_time', 'query_text_short']].to_dict('records'),
                columns=[
                    {'name': 'Session ID', 'id': 'session_id'},
                    {'name': 'Blocked By', 'id': 'blocking_session_id'},
                    {'name': 'Login', 'id': 'login_name'},
                    {'name': 'Database', 'id': 'database_name'},
                    {'name': 'Wait Type', 'id': 'wait_type'},
                    {'name': 'Wait Time', 'id': 'wait_time'},
                    {'name': 'Query', 'id': 'query_text_short'}
                ],
                style_cell={'textAlign': 'left', 'padding': '12px', 'fontSize': '12px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'color': '#495057'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
                ],
                page_size=10
            )
        
        return html.Div([
            html.H2("Reliability & Availability", style={'color': '#333', 'marginBottom': '20px', 'fontSize': '22px'}),
            reliability_kpis,
            
            # Charts Row
            html.Div([
                html.Div([dcc.Graph(figure=backup_fig, config={'displayModeBar': False})],
                        style={'width': '58%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'marginRight': '2%'}),
                html.Div([dcc.Graph(figure=conn_fig, config={'displayModeBar': False})],
                        style={'width': '40%', 'display': 'inline-block', 'backgroundColor': 'white',
                               'padding': '20px', 'borderRadius': '8px', 'boxShadow': '0 2px 8px rgba(0,0,0,0.08)', 'verticalAlign': 'top'})
            ], style={'marginBottom': '20px'}),
            
            # Blocking Sessions Table
            html.Div([
                html.H3("Blocking Sessions", style={'color': '#333', 'fontSize': '16px', 'marginBottom': '15px', 'fontWeight': '600'}),
                blocking_table
            ], style={'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '8px', 
                     'boxShadow': '0 2px 8px rgba(0,0,0,0.08)'})
        ])
        
    except Exception as e:
        logger.error(f"Error rendering reliability page: {e}")
        return html.Div(f"Error loading reliability: {str(e)}", style={'color': 'red'})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
