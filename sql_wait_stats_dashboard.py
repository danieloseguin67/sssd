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


class SQLServerWaitStats:
    """Class to handle SQL Server wait statistics queries"""
    
    def __init__(self, config_file='config.json'):
        """Initialize with database configuration"""
        with open(config_file, 'r') as f:
            self.config = json.load(f)
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
app = Dash(__name__)

# Define the layout with professional styling
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("SQL Server Wait Statistics", style={
            'textAlign': 'center',
            'color': '#ffffff',
            'margin': '0',
            'padding': '20px'
        }),
        html.Div([
            html.Label("Refresh Interval: ", style={'color': 'white', 'marginRight': '10px'}),
            dcc.Dropdown(
                id='refresh-interval',
                options=[
                    {'label': '5 sec', 'value': 5},
                    {'label': '10 sec', 'value': 10},
                    {'label': '30 sec', 'value': 30},
                    {'label': '60 sec', 'value': 60},
                    {'label': 'Manual', 'value': 0}
                ],
                value=10,
                style={'width': '120px', 'display': 'inline-block'}
            ),
            html.Div(id='status-message', style={
                'display': 'inline-block',
                'marginLeft': '20px',
                'color': '#4CAF50'
            })
        ], style={'textAlign': 'center', 'padding': '10px'})
    ], style={
        'backgroundColor': '#1a1a2e',
        'marginBottom': '20px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
    }),
    
    # Interval component for auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=10*1000,  # in milliseconds
        n_intervals=0
    ),
    
    # KPI Cards Row
    html.Div(id='kpi-cards', style={'padding': '0 20px'}),
    
    # Charts Section
    html.Div([
        # Row 1: Top Wait Types and Category Distribution
        html.Div([
            html.Div([
                html.H3("Top Wait Types by Total Wait Time", style={
                    'color': '#333',
                    'fontSize': '18px',
                    'marginBottom': '10px'
                }),
                dcc.Graph(id='top-waits-bar-chart', config={'displayModeBar': False})
            ], style={
                'width': '58%',
                'display': 'inline-block',
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginRight': '2%'
            }),
            
            html.Div([
                html.H3("Wait Category Distribution", style={
                    'color': '#333',
                    'fontSize': '18px',
                    'marginBottom': '10px'
                }),
                dcc.Graph(id='wait-category-donut', config={'displayModeBar': False})
            ], style={
                'width': '38%',
                'display': 'inline-block',
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'verticalAlign': 'top'
            })
        ], style={'marginBottom': '20px'}),
        
        # Row 2: Average Wait Time and Signal vs Resource
        html.Div([
            html.Div([
                html.H3("Average Wait Time per Task (ms)", style={
                    'color': '#333',
                    'fontSize': '18px',
                    'marginBottom': '10px'
                }),
                dcc.Graph(id='avg-wait-bar-chart', config={'displayModeBar': False})
            ], style={
                'width': '48%',
                'display': 'inline-block',
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'marginRight': '2%'
            }),
            
            html.Div([
                html.H3("Signal vs Resource Wait — Top 10", style={
                    'color': '#333',
                    'fontSize': '18px',
                    'marginBottom': '10px'
                }),
                dcc.Graph(id='signal-resource-chart', config={'displayModeBar': False})
            ], style={
                'width': '48%',
                'display': 'inline-block',
                'backgroundColor': 'white',
                'padding': '15px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'verticalAlign': 'top'
            })
        ], style={'marginBottom': '20px'}),
        
        # Top 10 Queries Table
        html.Div([
            html.H3("Top Queries by Total Wait Time", style={
                'color': '#333',
                'fontSize': '18px',
                'marginBottom': '10px'
            }),
            html.Div(id='queries-table')
        ], style={
            'backgroundColor': 'white',
            'padding': '15px',
            'borderRadius': '8px',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
            'marginBottom': '20px'
        })
    ], style={'padding': '0 20px'})
], style={
    'backgroundColor': '#f5f5f5',
    'minHeight': '100vh',
    'fontFamily': 'Arial, sans-serif'
})


# Callbacks
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
    [Output('kpi-cards', 'children'),
     Output('top-waits-bar-chart', 'figure'),
     Output('wait-category-donut', 'figure'),
     Output('avg-wait-bar-chart', 'figure'),
     Output('signal-resource-chart', 'figure'),
     Output('queries-table', 'children'),
     Output('status-message', 'children')],
    Input('interval-component', 'n_intervals')
)
def update_dashboard(n):
    """Update all dashboard components"""
    try:
        # Connect to database
        db = SQLServerWaitStats()
        if not db.connect():
            empty_fig = go.Figure()
            return html.Div("Connection failed"), empty_fig, empty_fig, empty_fig, empty_fig, html.Div("Connection failed"), "❌ Failed to connect"
        
        # Get data
        top_waits = db.get_top_wait_types(15)
        query_waits = db.get_query_waits(10)
        avg_waits = db.get_average_wait_times(15)
        
        if top_waits.empty:
            db.close()
            empty_fig = go.Figure()
            return html.Div("No data"), empty_fig, empty_fig, empty_fig, empty_fig, html.Div("No data"), "⚠️ No data available"
        
        # Add categories to wait types
        top_waits['category'] = top_waits['wait_type'].apply(categorize_wait_type)
        
        # Calculate KPIs
        total_wait_time = top_waits['wait_time_ms'].sum()
        total_tasks = top_waits['waiting_tasks_count'].sum()
        unique_wait_types = len(top_waits)
        top_wait_type = top_waits.iloc[0]['wait_type'] if not top_waits.empty else 'N/A'
        
        # Category aggregation
        category_stats = top_waits.groupby('category').agg({
            'wait_time_ms': 'sum',
            'percentage': 'sum'
        }).reset_index()
        
        # KPI Cards
        def create_kpi_card(title, value, subtitle='', color='#2196F3'):
            return html.Div([
                html.Div(title, style={
                    'fontSize': '12px',
                    'color': '#888',
                    'textTransform': 'uppercase',
                    'marginBottom': '5px'
                }),
                html.Div(value, style={
                    'fontSize': '32px',
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
                'padding': '20px',
                'borderRadius': '8px',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                'textAlign': 'center',
                'minWidth': '150px'
            })
        
        cpu_pct = category_stats[category_stats['category'] == 'CPU']['percentage'].sum() if 'CPU' in category_stats['category'].values else 0
        io_pct = category_stats[category_stats['category'] == 'IO']['percentage'].sum() if 'IO' in category_stats['category'].values else 0
        mem_pct = category_stats[category_stats['category'] == 'Memory']['percentage'].sum() if 'Memory' in category_stats['category'].values else 0
        latch_pct = category_stats[category_stats['category'] == 'Latch']['percentage'].sum() if 'Latch' in category_stats['category'].values else 0
        lock_pct = category_stats[category_stats['category'] == 'Lock']['percentage'].sum() if 'Lock' in category_stats['category'].values else 0
        other_pct = category_stats[category_stats['category'] == 'Other']['percentage'].sum() if 'Other' in category_stats['category'].values else 0
        
        kpi_cards = html.Div([
            create_kpi_card('CPU WAITS', f'{cpu_pct:.1f}%', 'Signal wait percentage', '#FF6B6B'),
            create_kpi_card('IO WAITS', f'{io_pct:.1f}%', 'Page & log I/O', '#4ECDC4'),
            create_kpi_card('MEMORY WAITS', f'{mem_pct:.1f}%', 'Resource allocation', '#45B7D1'),
            create_kpi_card('LATCH WAITS', f'{latch_pct:.1f}%', 'Internal latches', '#96CEB4'),
            create_kpi_card('LOCK WAITS', f'{lock_pct:.1f}%', 'Blocking/deadlocks', '#FFEAA7'),
            create_kpi_card('OTHER WAITS', f'{other_pct:.1f}%', 'Misc waits', '#DFE6E9'),
            create_kpi_card('TOTAL WAIT TIME', f'{total_wait_time/1000/60:.1f}M', 'Minutes', '#A29BFE'),
            create_kpi_card('TOP WAIT TYPE', top_wait_type[:20], f'{top_waits.iloc[0]["percentage"]:.1f}%', '#FD79A8'),
            create_kpi_card('UNIQUE WAIT TYPES', str(unique_wait_types), 'Distinct types', '#74B9FF'),
            create_kpi_card('WAITING TASKS', f'{total_tasks/1000000:.1f}M', 'Total count', '#55EFC4'),
        ], style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '15px',
            'marginBottom': '20px',
            'justifyContent': 'space-between'
        })
        
        # 1. Top Wait Types Horizontal Bar Chart
        top_10_waits = top_waits.head(10).sort_values('wait_time_ms')
        bar_colors = ['#FF6B6B' if cat == 'CPU' else 
                      '#4ECDC4' if cat == 'IO' else 
                      '#45B7D1' if cat == 'Memory' else 
                      '#96CEB4' if cat == 'Latch' else 
                      '#FFEAA7' if cat == 'Lock' else '#DFE6E9' 
                      for cat in top_10_waits['category']]
        
        top_waits_fig = go.Figure()
        top_waits_fig.add_trace(go.Bar(
            y=top_10_waits['wait_type'],
            x=top_10_waits['wait_time_ms'] / 1000,
            orientation='h',
            marker_color=bar_colors,
            text=top_10_waits['percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Wait Time: %{x:.2f}s<extra></extra>'
        ))
        top_waits_fig.update_layout(
            xaxis_title="Wait Time (seconds)",
            yaxis_title="",
            height=400,
            margin=dict(l=180, r=50, t=20, b=40),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # 2. Category Donut Chart
        donut_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DFE6E9']
        category_donut_fig = go.Figure()
        category_donut_fig.add_trace(go.Pie(
            labels=category_stats['category'],
            values=category_stats['wait_time_ms'],
            hole=0.6,
            marker_colors=donut_colors[:len(category_stats)],
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} ms<br>%{percent}<extra></extra>'
        ))
        category_donut_fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # 3. Average Wait Time Bar Chart
        avg_wait_fig = go.Figure()
        if not avg_waits.empty:
            avg_top_10 = avg_waits.head(10).sort_values('avg_wait_time_ms')
            avg_wait_fig.add_trace(go.Bar(
                y=avg_top_10['wait_type'],
                x=avg_top_10['avg_wait_time_ms'],
                orientation='h',
                marker_color='#4ECDC4',
                hovertemplate='<b>%{y}</b><br>Avg Wait: %{x:.2f} ms<extra></extra>'
            ))
        avg_wait_fig.update_layout(
            xaxis_title="Average Wait Time (ms)",
            yaxis_title="",
            height=400,
            margin=dict(l=180, r=50, t=20, b=40),
            showlegend=False,
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # 4. Signal vs Resource Wait Chart
        signal_resource_fig = go.Figure()
        top_10_signal = top_waits.head(10)
        
        signal_resource_fig.add_trace(go.Bar(
            y=top_10_signal['wait_type'],
            x=top_10_signal['resource_wait_time_ms'] / 1000,
            name='Resource Wait',
            orientation='h',
            marker_color='#FF6B6B',
            hovertemplate='<b>%{y}</b><br>Resource: %{x:.2f}s<extra></extra>'
        ))
        signal_resource_fig.add_trace(go.Bar(
            y=top_10_signal['wait_type'],
            x=top_10_signal['signal_wait_time_ms'] / 1000,
            name='Signal Wait',
            orientation='h',
            marker_color='#4ECDC4',
            hovertemplate='<b>%{y}</b><br>Signal: %{x:.2f}s<extra></extra>'
        ))
        
        signal_resource_fig.update_layout(
            xaxis_title="Wait Time (seconds)",
            yaxis_title="",
            barmode='stack',
            height=400,
            margin=dict(l=180, r=50, t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        
        # 5. Top Queries Table
        if not query_waits.empty:
            table = dash_table.DataTable(
                data=query_waits[['query_text_short', 'execution_count', 
                                  'total_wait_time_ms', 'total_cpu_time_ms', 
                                  'total_elapsed_time_ms']].to_dict('records'),
                columns=[
                    {'name': 'Query', 'id': 'query_text_short'},
                    {'name': 'Executions', 'id': 'execution_count', 'type': 'numeric', 'format': {'specifier': ','}},
                    {'name': 'Total Wait (ms)', 'id': 'total_wait_time_ms', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
                    {'name': 'Total CPU (ms)', 'id': 'total_cpu_time_ms', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
                    {'name': 'Total Elapsed (ms)', 'id': 'total_elapsed_time_ms', 'type': 'numeric', 'format': {'specifier': ',.0f'}}
                ],
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    'maxWidth': 0,
                    'fontSize': '13px',
                    'fontFamily': 'Arial, sans-serif'
                },
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'borderBottom': '2px solid #dee2e6',
                    'color': '#495057'
                },
                style_data={
                    'borderBottom': '1px solid #dee2e6'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa'
                    },
                    {
                        'if': {'column_id': 'query_text_short'},
                        'fontFamily': 'Courier New, monospace',
                        'fontSize': '12px'
                    }
                ],
                tooltip_data=[
                    {
                        'query_text_short': {'value': str(row['query_text'])[:500], 'type': 'text'}
                    } for i, row in query_waits.iterrows()
                ] if 'query_text' in query_waits.columns else None,
                tooltip_duration=None,
                page_size=10
            )
        else:
            table = html.Div("No query data available", style={'padding': '20px', 'textAlign': 'center', 'color': '#888'})
        
        db.close()
        
        status = f"✓ Updated: {datetime.now().strftime('%H:%M:%S')}"
        
        return kpi_cards, top_waits_fig, category_donut_fig, avg_wait_fig, signal_resource_fig, table, status
        
    except Exception as e:
        logger.error(f"Error updating dashboard: {e}")
        error_msg = f"❌ Error: {str(e)}"
        empty_fig = go.Figure()
        return html.Div("Error"), empty_fig, empty_fig, empty_fig, empty_fig, html.Div("Error loading data"), error_msg


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8050)
