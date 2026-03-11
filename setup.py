"""
Setup script for SQL Server Wait Statistics Dashboard
"""
import json
import os
import sys


def check_config():
    """Check if config.json exists"""
    if not os.path.exists('config.json'):
        print("❌ config.json not found!")
        print("📋 Please copy config.example.json to config.json and update with your credentials")
        return False
    
    print("✓ config.json found")
    return True


def validate_config():
    """Validate config.json structure"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        required_fields = ['server', 'database', 'username', 'password', 'driver']
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            print(f"❌ Missing required fields in config.json: {', '.join(missing)}")
            return False
        
        # Check for placeholder values
        if config['username'] == 'your_username' or config['server'] == 'your_server_instance':
            print("⚠️  Warning: config.json contains placeholder values")
            print("   Please update with your actual SQL Server credentials")
            return False
        
        print("✓ config.json is valid")
        return True
        
    except json.JSONDecodeError:
        print("❌ config.json is not valid JSON")
        return False
    except Exception as e:
        print(f"❌ Error reading config.json: {e}")
        return False


def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['pyodbc', 'pandas', 'plotly', 'dash']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is not installed")
    
    if missing_packages:
        print(f"\n📦 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True


def test_connection():
    """Test database connection"""
    try:
        import pyodbc
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        print("\n🔌 Testing database connection...")
        conn_str = (
            f"DRIVER={{{config['driver']}}};"
            f"SERVER={config['server']};"
            f"DATABASE={config['database']};"
            f"UID={config['username']};"
            f"PWD={config['password']}"
        )
        
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"✓ Successfully connected to SQL Server")
        print(f"  Version: {version.split('\\n')[0]}")
        conn.close()
        return True
        
    except pyodbc.Error as e:
        print(f"❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 60)
    print("SQL Server Wait Statistics Dashboard - Setup")
    print("=" * 60)
    print()
    
    # Check configuration
    if not check_config():
        sys.exit(1)
    
    if not validate_config():
        sys.exit(1)
    
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Please install missing dependencies before continuing")
        sys.exit(1)
    
    # Test connection
    if not test_connection():
        print("\n⚠️  Please verify your database connection settings")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("✓ Setup complete! You can now run the dashboard:")
    print("  python sql_wait_stats_dashboard.py")
    print()
    print("  Then open your browser to: http://127.0.0.1:8050")
    print("=" * 60)


if __name__ == '__main__':
    main()
