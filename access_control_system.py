"""
Enhanced Visitor Investigation System with Advanced Access Control
Multi-tenant SaaS platform with granular user permissions and restrictions
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
import ipaddress

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, origins="*")

# Database initialization
def init_database():
    """Initialize the multi-tenant database with advanced access control"""
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
    
    # Client users table - stores users with access to client dashboards
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
            allowed_ips TEXT,
            permissions TEXT,
            session_limit INTEGER DEFAULT 1,
            current_sessions INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # User sessions table - tracks active user sessions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES client_users (user_id),
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Access logs table - audit trail
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            client_id TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            ip_address TEXT,
            user_agent TEXT,
            success BOOLEAN DEFAULT 1,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES client_users (user_id),
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Visitor investigations table - stores visitor data per client
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

def log_access(user_id, client_id, action, resource=None, ip_address=None, user_agent=None, success=True, details=None):
    """Log user access for audit trail"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO access_logs 
        (user_id, client_id, action, resource, ip_address, user_agent, success, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, client_id, action, resource, ip_address, user_agent, success, details))
    
    conn.commit()
    conn.close()

def check_ip_restriction(user_id, client_ip):
    """Check if user's IP is allowed"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT allowed_ips FROM client_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result or not result[0]:
        return True  # No IP restrictions
    
    allowed_ips = json.loads(result[0])
    if not allowed_ips:
        return True
    
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        for allowed_ip in allowed_ips:
            if '/' in allowed_ip:  # CIDR notation
                if client_ip_obj in ipaddress.ip_network(allowed_ip, strict=False):
                    return True
            else:  # Single IP
                if str(client_ip_obj) == allowed_ip:
                    return True
        return False
    except:
        return False

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
    """Verify user access token and return user/client info with restrictions"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT cu.user_id, cu.client_id, cu.name, cu.email, cu.role, cu.status,
               cu.access_expires_at, cu.allowed_ips, cu.permissions, cu.session_limit,
               c.business_name, c.website_url, c.subscription_status, c.plan_type
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
        'allowed_ips': json.loads(result[7]) if result[7] else [],
        'permissions': json.loads(result[8]) if result[8] else {},
        'session_limit': result[9],
        'business_name': result[10],
        'website_url': result[11],
        'subscription_status': result[12],
        'plan_type': result[13]
    }
    
    # Check if access has expired
    if user_data['access_expires_at']:
        expires_at = datetime.fromisoformat(user_data['access_expires_at'])
        if datetime.now() > expires_at:
            log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                      details='Access expired', ip_address=ip_address, success=False)
            return None
    
    # Check IP restrictions
    if ip_address and not check_ip_restriction(user_data['user_id'], ip_address):
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  details=f'IP not allowed: {ip_address}', ip_address=ip_address, success=False)
        return None
    
    # Check session limit
    if check_session_limit(user_data['user_id']):
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  details='Session limit exceeded', ip_address=ip_address, success=False)
        return None
    
    return user_data

def create_user_session(user_id, client_id, ip_address=None, user_agent=None):
    """Create a new user session"""
    session_id = generate_session_id()
    expires_at = datetime.now() + timedelta(hours=24)  # 24-hour sessions
    
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO user_sessions 
        (session_id, user_id, client_id, ip_address, user_agent, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session_id, user_id, client_id, ip_address, user_agent, expires_at.isoformat()))
    
    conn.commit()
    conn.close()
    
    return session_id

def cleanup_expired_sessions():
    """Clean up expired sessions"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE user_sessions 
        SET is_active = 0 
        WHERE expires_at <= datetime('now')
    ''')
    
    conn.commit()
    conn.close()

# Permission checking functions
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

def filter_visitor_data(visitor, user_data):
    """Filter visitor data based on user permissions"""
    if has_permission(user_data, 'view_contact_info'):
        return visitor  # Return full data
    
    # Remove sensitive contact information
    filtered_visitor = visitor.copy()
    if not has_permission(user_data, 'view_email'):
        filtered_visitor['email'] = 'Hidden'
    if not has_permission(user_data, 'view_phone'):
        filtered_visitor['phone'] = 'Hidden'
    if not has_permission(user_data, 'view_company'):
        filtered_visitor['company'] = 'Hidden'
        filtered_visitor['job_title'] = 'Hidden'
    
    return filtered_visitor

# Routes
@app.route('/')
def index():
    """Main visitor investigation interface"""
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for managing clients"""
    return render_template('admin_dashboard.html')

@app.route('/admin/clients', methods=['GET'])
def get_clients():
    """Get all clients for admin dashboard"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT client_id, business_name, contact_email, website_url, 
               subscription_status, created_at, last_access, plan_type, max_users
        FROM clients 
        ORDER BY created_at DESC
    ''')
    
    clients = []
    for row in cursor.fetchall():
        # Get user count for each client
        cursor.execute('SELECT COUNT(*) FROM client_users WHERE client_id = ? AND status = "active"', (row[0],))
        user_count = cursor.fetchone()[0]
        
        clients.append({
            'client_id': row[0],
            'business_name': row[1],
            'contact_email': row[2],
            'website_url': row[3],
            'subscription_status': row[4],
            'created_at': row[5],
            'last_access': row[6],
            'plan_type': row[7],
            'max_users': row[8],
            'current_users': user_count
        })
    
    conn.close()
    return jsonify({'clients': clients})

@app.route('/admin/create-client', methods=['POST'])
def create_client():
    """Create new client with owner user"""
    try:
        data = request.get_json()
        business_name = data.get('business_name', '').strip()
        contact_email = data.get('contact_email', '').strip()
        website_url = data.get('website_url', '').strip()
        plan_type = data.get('plan_type', 'basic')
        
        if not all([business_name, contact_email, website_url]):
            return jsonify({'error': 'All fields are required'}), 400
        
        # Generate unique identifiers
        client_id = generate_client_id()
        owner_user_id = generate_user_id()
        client_access_token = generate_access_token()
        owner_access_token = generate_access_token()
        
        # Determine max users based on plan
        max_users = {'basic': 5, 'professional': 15, 'enterprise': 50}.get(plan_type, 5)
        
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        # Create client
        cursor.execute('''
            INSERT INTO clients 
            (client_id, business_name, contact_email, website_url, access_token, 
             plan_type, max_users, owner_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (client_id, business_name, contact_email, website_url, client_access_token, 
              plan_type, max_users, owner_user_id))
        
        # Create owner user
        cursor.execute('''
            INSERT INTO client_users 
            (user_id, client_id, name, email, role, access_token, created_by, permissions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (owner_user_id, client_id, business_name + ' Owner', contact_email, 'owner', 
              owner_access_token, 'system', json.dumps({
                  'view_visitors': True,
                  'view_contact_info': True,
                  'view_email': True,
                  'view_phone': True,
                  'view_company': True,
                  'export_data': True,
                  'manage_users': True
              })))
        
        conn.commit()
        conn.close()
        
        # Generate secure dashboard URL
        dashboard_url = f"{request.host_url}dashboard/{owner_access_token}"
        
        return jsonify({
            'success': True,
            'client_id': client_id,
            'dashboard_url': dashboard_url,
            'access_token': owner_access_token,
            'message': f'Client created successfully for {business_name}'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create client: {str(e)}'}), 500

@app.route('/dashboard/<access_token>')
def client_dashboard(access_token):
    """Secure client dashboard accessible via unique URL"""
    ip_address = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    
    user_data = verify_user_access(access_token, ip_address, user_agent)
    
    if not user_data:
        return render_template('access_denied.html'), 403
    
    # Create session
    session_id = create_user_session(user_data['user_id'], user_data['client_id'], ip_address, user_agent)
    
    # Log access
    log_access(user_data['user_id'], user_data['client_id'], 'dashboard_access', 
              ip_address=ip_address, user_agent=user_agent)
    
    return render_template('client_dashboard.html', 
                         user=user_data, 
                         access_token=access_token)

@app.route('/api/client-visitors/<access_token>')
def get_client_visitors(access_token):
    """Get visitor data for specific client with pagination and user restrictions"""
    ip_address = request.remote_addr
    user_data = verify_user_access(access_token, ip_address)
    
    if not user_data:
        return jsonify({'error': 'Access denied'}), 403
    
    if not has_permission(user_data, 'view_visitors'):
        log_access(user_data['user_id'], user_data['client_id'], 'access_denied', 
                  'view_visitors', ip_address, success=False)
        return jsonify({'error': 'Permission denied'}), 403
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    per_page = 50
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    # Apply data filtering based on user permissions
    where_clause = "WHERE client_id = ?"
    params = [user_data['client_id']]
    
    # Filter by interest level if user has restricted access
    if not has_permission(user_data, 'view_all_interest_levels'):
        allowed_levels = user_data['permissions'].get('allowed_interest_levels', ['High', 'Medium', 'Low'])
        placeholders = ','.join(['?' for _ in allowed_levels])
        where_clause += f" AND interest_level IN ({placeholders})"
        params.extend(allowed_levels)
    
    # Get total count
    cursor.execute(f'''
        SELECT COUNT(*) FROM visitor_investigations {where_clause}
    ''', params)
    total_visitors = cursor.fetchone()[0]
    
    # Calculate pagination info
    total_pages = (total_visitors + per_page - 1) // per_page
    
    # Get visitors with priority sorting
    cursor.execute(f'''
        SELECT visitor_id, name, email, phone, company, job_title, location,
               current_page, pages_visited, time_on_site_seconds, visit_start_time,
               interest_level, traffic_source, device_type, browser,
               first_visit, last_activity, session_count, total_page_views, is_active
        FROM visitor_investigations 
        {where_clause}
        ORDER BY 
            CASE interest_level 
                WHEN 'High' THEN 1 
                WHEN 'Medium' THEN 2 
                WHEN 'Low' THEN 3 
                ELSE 4 
            END,
            time_on_site_seconds DESC
        LIMIT ? OFFSET ?
    ''', params + [per_page, offset])
    
    visitors = []
    for row in cursor.fetchall():
        visitor = {
            'visitor_id': row[0],
            'name': row[1],
            'email': row[2],
            'phone': row[3],
            'company': row[4],
            'job_title': row[5],
            'location': row[6],
            'current_page': row[7],
            'pages_visited': json.loads(row[8]) if row[8] else [],
            'time_on_site_seconds': row[9],
            'visit_start_time': row[10],
            'interest_level': row[11],
            'traffic_source': row[12],
            'device_type': row[13],
            'browser': row[14],
            'first_visit': row[15],
            'last_activity': row[16],
            'session_count': row[17],
            'total_page_views': row[18],
            'is_active': bool(row[19])
        }
        
        # Apply data filtering based on permissions
        filtered_visitor = filter_visitor_data(visitor, user_data)
        visitors.append(filtered_visitor)
    
    conn.close()
    
    # Log access
    log_access(user_data['user_id'], user_data['client_id'], 'view_visitors', 
              f'page_{page}', request.remote_addr)
    
    return jsonify({
        'visitors': visitors, 
        'user': user_data,
        'pagination': {
            'current_page': page,
            'total_pages': total_pages,
            'total_visitors': total_visitors,
            'per_page': per_page,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    })

@app.route('/api/user-management/<access_token>')
def user_management(access_token):
    """Get user management interface for client"""
    ip_address = request.remote_addr
    user_data = verify_user_access(access_token, ip_address)
    
    if not user_data:
        return jsonify({'error': 'Access denied'}), 403
    
    if not has_permission(user_data, 'manage_users'):
        return jsonify({'error': 'Permission denied - cannot manage users'}), 403
    
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    # Get all users for this client
    cursor.execute('''
        SELECT user_id, name, email, role, status, created_at, last_access,
               access_expires_at, allowed_ips, permissions, session_limit, notes
        FROM client_users 
        WHERE client_id = ?
        ORDER BY created_at DESC
    ''', (user_data['client_id'],))
    
    users = []
    for row in cursor.fetchall():
        users.append({
            'user_id': row[0],
            'name': row[1],
            'email': row[2],
            'role': row[3],
            'status': row[4],
            'created_at': row[5],
            'last_access': row[6],
            'access_expires_at': row[7],
            'allowed_ips': json.loads(row[8]) if row[8] else [],
            'permissions': json.loads(row[9]) if row[9] else {},
            'session_limit': row[10],
            'notes': row[11]
        })
    
    conn.close()
    return jsonify({'users': users, 'user': user_data})

@app.route('/api/create-user/<access_token>', methods=['POST'])
def create_user(access_token):
    """Create new user with restrictions"""
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
        allowed_ips = data.get('allowed_ips', [])
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
        
        # Create user
        cursor.execute('''
            INSERT INTO client_users 
            (user_id, client_id, name, email, role, access_token, created_by,
             access_expires_at, allowed_ips, permissions, session_limit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_user_id, user_data['client_id'], name, email, role, new_access_token,
              user_data['user_id'], access_expires_at, json.dumps(allowed_ips),
              json.dumps(permissions), session_limit, notes))
        
        conn.commit()
        conn.close()
        
        # Generate dashboard URL
        dashboard_url = f"{request.host_url}dashboard/{new_access_token}"
        
        # Log action
        log_access(user_data['user_id'], user_data['client_id'], 'create_user', 
                  new_user_id, ip_address)
        
        return jsonify({
            'success': True,
            'user_id': new_user_id,
            'dashboard_url': dashboard_url,
            'access_token': new_access_token,
            'message': f'User {name} created successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500

@app.route('/api/restrict-user/<access_token>/<target_user_id>', methods=['POST'])
def restrict_user(access_token, target_user_id):
    """Apply restrictions to a user"""
    ip_address = request.remote_addr
    user_data = verify_user_access(access_token, ip_address)
    
    if not user_data:
        return jsonify({'error': 'Access denied'}), 403
    
    if not has_permission(user_data, 'manage_users'):
        return jsonify({'error': 'Permission denied - cannot manage users'}), 403
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'deactivate', 'restrict_ip', 'limit_time', 'change_permissions'
        
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        if action == 'deactivate':
            cursor.execute('''
                UPDATE client_users 
                SET status = 'inactive' 
                WHERE user_id = ? AND client_id = ?
            ''', (target_user_id, user_data['client_id']))
            
            # Deactivate all sessions
            cursor.execute('''
                UPDATE user_sessions 
                SET is_active = 0 
                WHERE user_id = ?
            ''', (target_user_id,))
            
            message = 'User deactivated successfully'
            
        elif action == 'restrict_ip':
            allowed_ips = data.get('allowed_ips', [])
            cursor.execute('''
                UPDATE client_users 
                SET allowed_ips = ? 
                WHERE user_id = ? AND client_id = ?
            ''', (json.dumps(allowed_ips), target_user_id, user_data['client_id']))
            
            message = 'IP restrictions updated'
            
        elif action == 'limit_time':
            hours = data.get('hours', 24)
            expires_at = (datetime.now() + timedelta(hours=hours)).isoformat()
            cursor.execute('''
                UPDATE client_users 
                SET access_expires_at = ? 
                WHERE user_id = ? AND client_id = ?
            ''', (expires_at, target_user_id, user_data['client_id']))
            
            message = f'Access limited to {hours} hours'
            
        elif action == 'change_permissions':
            permissions = data.get('permissions', {})
            cursor.execute('''
                UPDATE client_users 
                SET permissions = ? 
                WHERE user_id = ? AND client_id = ?
            ''', (json.dumps(permissions), target_user_id, user_data['client_id']))
            
            message = 'Permissions updated'
            
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        conn.commit()
        conn.close()
        
        # Log action
        log_access(user_data['user_id'], user_data['client_id'], f'restrict_user_{action}', 
                  target_user_id, ip_address)
        
        return jsonify({'success': True, 'message': message})
        
    except Exception as e:
        return jsonify({'error': f'Failed to restrict user: {str(e)}'}), 500

@app.route('/api/access-logs/<access_token>')
def get_access_logs(access_token):
    """Get access logs for audit trail"""
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
               al.ip_address, al.success, al.details
        FROM access_logs al
        LEFT JOIN client_users cu ON al.user_id = cu.user_id
        WHERE al.client_id = ?
        ORDER BY al.timestamp DESC
        LIMIT 100
    ''', (user_data['client_id'],))
    
    logs = []
    for row in cursor.fetchall():
        logs.append({
            'timestamp': row[0],
            'user_name': row[1] or 'Unknown',
            'user_email': row[2] or 'Unknown',
            'action': row[3],
            'resource': row[4],
            'ip_address': row[5],
            'success': bool(row[6]),
            'details': row[7]
        })
    
    conn.close()
    return jsonify({'logs': logs})

# Include all the previous routes for visitor data, export, etc.
# (The generate_realistic_visitor_data, export functions, etc. remain the same)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    cleanup_expired_sessions()  # Clean up on health check
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚀 Starting Enhanced Visitor Investigation System with Advanced Access Control")
    print("📊 Admin Dashboard: http://localhost:5000/admin")
    print("🔍 Main Investigation: http://localhost:5000/")
    print("🔐 Features: Role-based access, IP restrictions, time limits, audit logs")
    app.run(host='0.0.0.0', port=5000, debug=True)

