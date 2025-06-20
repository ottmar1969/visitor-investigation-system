"""
Enhanced Visitor Investigation System with Country-Based Access Control
Multi-tenant SaaS platform with geographic restrictions and IP geolocation
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
import json
import random
import string
import hashlib
import time
import uuid
from datetime import datetime, timedelta
import secrets
import os
import csv
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import requests

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, origins="*")

# Country data for restrictions
COUNTRIES = {
    'US': 'United States', 'CA': 'Canada', 'GB': 'United Kingdom', 'AU': 'Australia',
    'DE': 'Germany', 'FR': 'France', 'IT': 'Italy', 'ES': 'Spain', 'NL': 'Netherlands',
    'SE': 'Sweden', 'NO': 'Norway', 'DK': 'Denmark', 'FI': 'Finland', 'CH': 'Switzerland',
    'AT': 'Austria', 'BE': 'Belgium', 'IE': 'Ireland', 'PT': 'Portugal', 'LU': 'Luxembourg',
    'JP': 'Japan', 'KR': 'South Korea', 'SG': 'Singapore', 'HK': 'Hong Kong', 'TW': 'Taiwan',
    'IN': 'India', 'CN': 'China', 'RU': 'Russia', 'BR': 'Brazil', 'MX': 'Mexico',
    'AR': 'Argentina', 'CL': 'Chile', 'CO': 'Colombia', 'PE': 'Peru', 'VE': 'Venezuela',
    'ZA': 'South Africa', 'EG': 'Egypt', 'NG': 'Nigeria', 'KE': 'Kenya', 'MA': 'Morocco',
    'IL': 'Israel', 'AE': 'United Arab Emirates', 'SA': 'Saudi Arabia', 'TR': 'Turkey',
    'PL': 'Poland', 'CZ': 'Czech Republic', 'HU': 'Hungary', 'RO': 'Romania', 'BG': 'Bulgaria',
    'HR': 'Croatia', 'SI': 'Slovenia', 'SK': 'Slovakia', 'LT': 'Lithuania', 'LV': 'Latvia',
    'EE': 'Estonia', 'GR': 'Greece', 'CY': 'Cyprus', 'MT': 'Malta', 'IS': 'Iceland',
    'NZ': 'New Zealand', 'TH': 'Thailand', 'MY': 'Malaysia', 'ID': 'Indonesia', 'PH': 'Philippines',
    'VN': 'Vietnam', 'BD': 'Bangladesh', 'PK': 'Pakistan', 'LK': 'Sri Lanka', 'MM': 'Myanmar'
}

CONTINENTS = {
    'NA': ['US', 'CA', 'MX', 'GT', 'BZ', 'SV', 'HN', 'NI', 'CR', 'PA'],
    'EU': ['GB', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE', 'NO', 'DK', 'FI', 'CH', 'AT', 'BE', 'IE', 'PT', 'LU', 'PL', 'CZ', 'HU', 'RO', 'BG', 'HR', 'SI', 'SK', 'LT', 'LV', 'EE', 'GR', 'CY', 'MT', 'IS'],
    'AS': ['JP', 'KR', 'SG', 'HK', 'TW', 'IN', 'CN', 'TH', 'MY', 'ID', 'PH', 'VN', 'BD', 'PK', 'LK', 'MM'],
    'SA': ['BR', 'AR', 'CL', 'CO', 'PE', 'VE', 'UY', 'PY', 'BO', 'EC', 'GY', 'SR', 'GF'],
    'AF': ['ZA', 'EG', 'NG', 'KE', 'MA', 'GH', 'TZ', 'UG', 'MZ', 'MG', 'CM', 'CI', 'NE', 'BF', 'ML', 'MW', 'ZM', 'SN', 'SO', 'TD', 'GN', 'RW', 'BJ', 'TN', 'BI', 'ER', 'SL', 'TG', 'CF', 'LR', 'MR', 'GM'],
    'OC': ['AU', 'NZ', 'FJ', 'PG', 'NC', 'SB', 'VU', 'WS', 'KI', 'TO', 'FM', 'PW', 'MH', 'TV', 'NR']
}

def get_country_from_ip(ip_address):
    """Get country code from IP address using free geolocation service"""
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return 'US'  # Default for localhost
    
    try:
        # Using ip-api.com (free, no API key required)
        response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=countryCode', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('countryCode', 'Unknown')
    except:
        pass
    
    # Fallback: try ipinfo.io
    try:
        response = requests.get(f'https://ipinfo.io/{ip_address}/country', timeout=5)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    
    return 'Unknown'

def is_vpn_or_proxy(ip_address):
    """Detect if IP is from VPN or proxy (basic detection)"""
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return False
    
    try:
        # Using ip-api.com to check for proxy/VPN
        response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=proxy', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('proxy', False)
    except:
        pass
    
    return False

# Database initialization
def init_database():
    """Initialize the multi-tenant database with country-based access control"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    # Clients table - stores business client information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            business_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            website_url TEXT NOT NULL,
            access_token TEXT UNIQUE NOT NULL,
            subscription_status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_access TIMESTAMP,
            billing_cycle TEXT DEFAULT 'monthly',
            plan_type TEXT DEFAULT 'basic',
            max_users INTEGER DEFAULT 5,
            owner_user_id TEXT
        )
    ''')
    
    # Client users table - stores users with country-based access control
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS client_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            access_token TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            last_access TIMESTAMP,
            access_expires_at TIMESTAMP,
            country_restrictions TEXT,
            block_vpn BOOLEAN DEFAULT 0,
            permissions TEXT,
            session_limit INTEGER DEFAULT 1,
            current_sessions INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # User sessions table - tracks active user sessions with country info
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            ip_address TEXT,
            country_code TEXT,
            is_vpn BOOLEAN DEFAULT 0,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES client_users (user_id),
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Access logs table - audit trail with country information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            client_id TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            ip_address TEXT,
            country_code TEXT,
            is_vpn BOOLEAN DEFAULT 0,
            user_agent TEXT,
            success BOOLEAN DEFAULT 1,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES client_users (user_id),
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Visitor investigations table (unchanged)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitor_investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT NOT NULL,
            visitor_id TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            job_title TEXT,
            location TEXT,
            ip_address TEXT,
            user_agent TEXT,
            current_page TEXT,
            pages_visited TEXT,
            time_on_site_seconds INTEGER DEFAULT 0,
            visit_start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            interest_level TEXT,
            traffic_source TEXT,
            device_type TEXT,
            browser TEXT,
            first_visit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_count INTEGER DEFAULT 1,
            total_page_views INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Admin users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

# Utility functions
def generate_client_id():
    """Generate unique client identifier"""
    return f"client_{uuid.uuid4().hex[:12]}"

def generate_user_id():
    """Generate unique user identifier"""
    return f"user_{uuid.uuid4().hex[:12]}"

def generate_access_token():
    """Generate secure access token"""
    return secrets.token_urlsafe(32)

def generate_session_id():
    """Generate unique session identifier"""
    return f"session_{uuid.uuid4().hex[:16]}"

def log_access(user_id, client_id, action, resource=None, ip_address=None, country_code=None, 
               is_vpn=False, user_agent=None, success=True, details=None):
    """Log user access for audit trail with country information"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO access_logs 
        (user_id, client_id, action, resource, ip_address, country_code, is_vpn, 
         user_agent, success, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, client_id, action, resource, ip_address, country_code, is_vpn, 
          user_agent, success, details))
    
    conn.commit()
    conn.close()

def check_country_restriction(user_id, country_code):
    """Check if user's country is allowed"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT country_restrictions FROM client_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        return True  # No country restrictions
    
    restrictions = json.loads(result[0])
    
    # Check restriction type
    restriction_type = restrictions.get('type', 'allow')  # 'allow' or 'block'
    countries = restrictions.get('countries', [])
    continents = restrictions.get('continents', [])
    
    # Check if country is in the list
    country_in_list = country_code in countries
    
    # Check if country is in allowed/blocked continents
    continent_match = False
    for continent, continent_countries in CONTINENTS.items():
        if continent in continents and country_code in continent_countries:
            continent_match = True
            break
    
    is_allowed = country_in_list or continent_match
    
    if restriction_type == 'allow':
        return is_allowed  # Must be in allowed list
    else:  # block
        return not is_allowed  # Must NOT be in blocked list

def check_session_limit(user_id):
    """Check if user has exceeded session limit"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    # Get user's session limit
    cursor.execute('SELECT session_limit FROM client_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if not result:
        return False
    
    session_limit = result[0]
    
    # Count active sessions
    cursor.execute('''
        SELECT COUNT(*) FROM user_sessions 
        WHERE user_id = ? AND is_active = 1 AND expires_at > datetime('now')
    ''', (user_id,))
    
    active_sessions = cursor.fetchone()[0]
    conn.close()
    
    return active_sessions >= session_limit

def verify_user_access(access_token, ip_address=None, user_agent=None):
    """Verify user access token with country-based restrictions"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cu.user_id, cu.client_id, cu.name, cu.email, cu.role, cu.status,
               cu.access_expires_at, cu.country_restrictions, cu.block_vpn, cu.permissions, 
               cu.session_limit, c.business_name, c.website_url, c.subscription_status, c.plan_type
        FROM client_users cu
        JOIN clients c ON cu.client_id = c.client_id
        WHERE cu.access_token = ? AND cu.status = 'active' AND c.subscription_status = 'active'
    ''', (access_token,))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return None
    
    user_data = {
        'user_id': result[0],
        'client_id': result[1],
        'name': result[2],
        'email': result[3],
        'role': result[4],
        'status': result[5],
        'access_expires_at': result[6],
        'country_restrictions': json.loads(result[7]) if result[7] else {},
        'block_vpn': bool(result[8]),
        'permissions': json.loads(result[9]) if result[9] else {},
        'session_limit': result[10],
        'business_name': result[11],
        'website_url': result[12],
        'subscription_status': result[13],
        'plan_type': result[14]
    }
    
    # Check if access has expired
    if user_data['access_expires_at']:
        expires_at = datetime.fromisoformat(user_data['access_expires_at'])
        if datetime.now() > expires_at:
            log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                      details='Access expired', ip_address=ip_address, success=False)
            return None
    
    # Get country from IP
    country_code = 'Unknown'
    is_vpn = False
    if ip_address:
        country_code = get_country_from_ip(ip_address)
        is_vpn = is_vpn_or_proxy(ip_address)
    
    # Check VPN restriction
    if user_data['block_vpn'] and is_vpn:
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  details='VPN/Proxy blocked', ip_address=ip_address, 
                  country_code=country_code, is_vpn=is_vpn, success=False)
        return None
    
    # Check country restrictions
    if not check_country_restriction(user_data['user_id'], country_code):
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  details=f'Country not allowed: {country_code}', ip_address=ip_address, 
                  country_code=country_code, is_vpn=is_vpn, success=False)
        return None
    
    # Check session limit
    if check_session_limit(user_data['user_id']):
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  details='Session limit exceeded', ip_address=ip_address, 
                  country_code=country_code, is_vpn=is_vpn, success=False)
        return None
    
    # Add country info to user data
    user_data['current_country'] = country_code
    user_data['current_country_name'] = COUNTRIES.get(country_code, country_code)
    user_data['is_vpn'] = is_vpn
    
    return user_data

def create_user_session(user_id, client_id, ip_address=None, user_agent=None):
    """Create a new user session with country tracking"""
    session_id = generate_session_id()
    expires_at = datetime.now() + timedelta(hours=24)  # 24-hour sessions
    
    country_code = 'Unknown'
    is_vpn = False
    if ip_address:
        country_code = get_country_from_ip(ip_address)
        is_vpn = is_vpn_or_proxy(ip_address)
    
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_sessions 
        (session_id, user_id, client_id, ip_address, country_code, is_vpn, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, user_id, client_id, ip_address, country_code, is_vpn, user_agent, expires_at.isoformat()))
    
    conn.commit()
    conn.close()
    
    return session_id

# Permission checking functions (same as before)
def has_permission(user_data, permission):
    """Check if user has specific permission"""
    permissions = user_data.get('permissions', {})
    
    # Admin role has all permissions
    if user_data['role'] == 'admin':
        return True
    
    # Owner role has all permissions except user management (unless explicitly granted)
    if user_data['role'] == 'owner':
        if permission == 'manage_users':
            return permissions.get('manage_users', True)
        return True
    
    # Manager role has most permissions
    if user_data['role'] == 'manager':
        restricted_permissions = ['manage_users', 'delete_data']
        if permission in restricted_permissions:
            return permissions.get(permission, False)
        return True
    
    # Viewer role has limited permissions
    if user_data['role'] == 'viewer':
        allowed_permissions = ['view_visitors', 'view_basic_info']
        if permission in allowed_permissions:
            return permissions.get(permission, True)
        return permissions.get(permission, False)
    
    # Read-only role has very limited permissions
    if user_data['role'] == 'readonly':
        allowed_permissions = ['view_visitors']
        return permission in allowed_permissions and permissions.get(permission, True)
    
    return False

# Routes
@app.route('/dashboard/<access_token>')
def client_dashboard(access_token):
    """Secure client dashboard with country-based access control"""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    user_data = verify_user_access(access_token, ip_address, user_agent)
    
    if not user_data:
        return render_template('access_denied.html'), 403
    
    # Create session
    session_id = create_user_session(user_data['user_id'], user_data['client_id'], ip_address, user_agent)
    
    # Log access
    log_access(user_data['user_id'], user_data['client_id'], 'dashboard_access', 
              ip_address=ip_address, country_code=user_data['current_country'], 
              is_vpn=user_data['is_vpn'], user_agent=user_agent)
    
    return render_template('client_dashboard.html', 
                         user=user_data, 
                         access_token=access_token)

@app.route('/api/countries')
def get_countries():
    """Get list of countries for restriction setup"""
    return jsonify({
        'countries': [{'code': code, 'name': name} for code, name in COUNTRIES.items()],
        'continents': {
            'NA': 'North America',
            'EU': 'Europe', 
            'AS': 'Asia',
            'SA': 'South America',
            'AF': 'Africa',
            'OC': 'Oceania'
        }
    })

@app.route('/api/create-user/<access_token>', methods=['POST'])
def create_user(access_token):
    """Create new user with country-based restrictions"""
    ip_address = request.remote_addr
    user_data = verify_user_access(access_token, ip_address)
    
    if not user_data:
        return jsonify({'error': 'Access denied'}), 403
    
    if not has_permission(user_data, 'manage_users'):
        return jsonify({'error': 'Permission denied - cannot manage users'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        role = data.get('role', 'viewer')
        access_duration = data.get('access_duration')  # hours, or None for permanent
        
        # Country restrictions
        restriction_type = data.get('restriction_type', 'allow')  # 'allow' or 'block'
        allowed_countries = data.get('allowed_countries', [])
        allowed_continents = data.get('allowed_continents', [])
        block_vpn = data.get('block_vpn', False)
        
        permissions = data.get('permissions', {})
        session_limit = data.get('session_limit', 1)
        notes = data.get('notes', '')
        
        if not all([name, email]):
            return jsonify({'error': 'Name and email are required'}), 400
        
        # Check if client has reached user limit
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT max_users FROM clients WHERE client_id = ?', (user_data['client_id'],))
        max_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM client_users WHERE client_id = ? AND status = "active"', 
                      (user_data['client_id'],))
        current_users = cursor.fetchone()[0]
        
        if current_users >= max_users:
            conn.close()
            return jsonify({'error': f'User limit reached ({max_users} users max)'}), 400
        
        # Generate user credentials
        new_user_id = generate_user_id()
        new_access_token = generate_access_token()
        
        # Calculate expiration
        access_expires_at = None
        if access_duration:
            access_expires_at = (datetime.now() + timedelta(hours=int(access_duration))).isoformat()
        
        # Prepare country restrictions
        country_restrictions = {
            'type': restriction_type,
            'countries': allowed_countries,
            'continents': allowed_continents
        }
        
        # Create user
        cursor.execute('''
            INSERT INTO client_users 
            (user_id, client_id, name, email, role, access_token, created_by,
             access_expires_at, country_restrictions, block_vpn, permissions, session_limit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_user_id, user_data['client_id'], name, email, role, new_access_token,
              user_data['user_id'], access_expires_at, json.dumps(country_restrictions),
              block_vpn, json.dumps(permissions), session_limit, notes))
        
        conn.commit()
        conn.close()
        
        # Generate dashboard URL
        dashboard_url = f"{request.host_url}dashboard/{new_access_token}"
        
        # Log action
        log_access(user_data['user_id'], user_data['client_id'], 'create_user', 
                  new_user_id, ip_address, user_data['current_country'], user_data['is_vpn'])
        
        return jsonify({
            'success': True,
            'user_id': new_user_id,
            'dashboard_url': dashboard_url,
            'access_token': new_access_token,
            'message': f'User {name} created successfully with country restrictions'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500

@app.route('/api/access-logs/<access_token>')
def get_access_logs(access_token):
    """Get access logs with country information"""
    ip_address = request.remote_addr
    user_data = verify_user_access(access_token, ip_address)
    
    if not user_data:
        return jsonify({'error': 'Access denied'}), 403
    
    if not has_permission(user_data, 'view_audit_logs'):
        return jsonify({'error': 'Permission denied - cannot view audit logs'}), 403
    
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT al.timestamp, cu.name, cu.email, al.action, al.resource,
               al.ip_address, al.country_code, al.is_vpn, al.success, al.details
        FROM access_logs al
        LEFT JOIN client_users cu ON al.user_id = cu.user_id
        WHERE al.client_id = ?
        ORDER BY al.timestamp DESC
        LIMIT 100
    ''', (user_data['client_id'],))
    
    logs = []
    for row in cursor.fetchall():
        country_name = COUNTRIES.get(row[6], row[6]) if row[6] else 'Unknown'
        logs.append({
            'timestamp': row[0],
            'user_name': row[1] or 'Unknown',
            'user_email': row[2] or 'Unknown',
            'action': row[3],
            'resource': row[4],
            'ip_address': row[5],
            'country_code': row[6],
            'country_name': country_name,
            'is_vpn': bool(row[7]),
            'success': bool(row[8]),
            'details': row[9]
        })
    
    conn.close()
    return jsonify({'logs': logs})

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Starting Enhanced Visitor Investigation System with Country-Based Access Control")
    print("📊 Admin Dashboard: http://localhost:5000/admin")
    print("🔍 Main Investigation: http://localhost:5000/")
    print("🌍 Features: Country restrictions, VPN blocking, geolocation tracking")
    app.run(host='0.0.0.0', port=5000, debug=True)

