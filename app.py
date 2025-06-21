from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
import json
import random
import string
import datetime
import os
import hashlib
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-very-secure-secret-key-change-in-production'
CORS(app)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# Database initialization
def init_db():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Visitor investigations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitor_investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            job_title TEXT,
            industry TEXT,
            visitor_ip TEXT,
            location_country TEXT,
            location_region TEXT,
            location_city TEXT,
            isp TEXT,
            organization TEXT,
            device_type TEXT,
            operating_system TEXT,
            browser TEXT,
            screen_resolution TEXT,
            user_agent TEXT,
            referral_source TEXT,
            traffic_source TEXT,
            entry_page TEXT,
            current_page TEXT,
            pages_visited TEXT,
            visit_duration INTEGER,
            session_count INTEGER,
            total_page_views INTEGER,
            interest_level TEXT,
            first_visit TIMESTAMP,
            last_activity TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            access_token TEXT UNIQUE NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            subscription_status TEXT DEFAULT 'trial',
            trial_end_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            client_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    # Trials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            trial_type TEXT DEFAULT 'standard',
            duration_hours INTEGER,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            created_by TEXT DEFAULT 'system',
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
def generate_access_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_credentials(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# Routes
@app.route('/')
def index():
    # Check if logged in, if not redirect to login
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return render_template('dashboard.html', active_tab='investigation')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if verify_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    return render_template('dashboard.html', active_tab='admin')

@app.route('/admin/login')
def admin_login():
    return redirect(url_for('login'))

@app.route('/admin/trials')
@login_required
def admin_trials():
    return render_template('dashboard.html', active_tab='trials')

@app.route('/admin/users')
@login_required
def admin_users():
    return render_template('dashboard.html', active_tab='users')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# API Routes
@app.route('/api/clients', methods=['GET'])
@login_required
def get_clients():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients ORDER BY created_at DESC')
    clients = cursor.fetchall()
    conn.close()
    
    clients_data = []
    for client in clients:
        clients_data.append({
            'id': client[0],
            'client_name': client[1],
            'access_token': client[2],
            'is_active': client[3],
            'subscription_status': client[4],
            'trial_end_date': client[5],
            'created_at': client[6]
        })
    
    return jsonify(clients_data)

@app.route('/api/clients', methods=['POST'])
@login_required
def create_client():
    data = request.get_json()
    client_name = data.get('client_name')
    
    if not client_name:
        return jsonify({'error': 'Client name is required'}), 400
    
    access_token = generate_access_token()
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO clients (client_name, access_token)
        VALUES (?, ?)
    ''', (client_name, access_token))
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'client_name': client_name,
        'access_token': access_token,
        'dashboard_url': f'/client/{access_token}'
    })

@app.route('/api/trials', methods=['GET'])
@login_required
def get_trials():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, c.client_name 
        FROM trials t 
        LEFT JOIN clients c ON t.client_id = c.id 
        ORDER BY t.start_time DESC
    ''')
    trials = cursor.fetchall()
    conn.close()
    
    trials_data = []
    for trial in trials:
        trials_data.append({
            'id': trial[0],
            'client_id': trial[1],
            'client_name': trial[8] if len(trial) > 8 else 'Unknown',
            'trial_type': trial[2],
            'duration_hours': trial[3],
            'start_time': trial[4],
            'end_time': trial[5],
            'is_active': trial[6],
            'created_by': trial[7]
        })
    
    return jsonify(trials_data)

@app.route('/api/trials', methods=['POST'])
@login_required
def create_trial():
    data = request.get_json()
    client_id = data.get('client_id')
    duration_hours = data.get('duration_hours', 3)
    trial_type = data.get('trial_type', 'manual')
    
    if not client_id:
        return jsonify({'error': 'Client ID is required'}), 400
    
    # Admin can create any duration, website limited to 3 hours
    if trial_type == 'website' and duration_hours > 3:
        duration_hours = 3
    
    end_time = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trials (client_id, trial_type, duration_hours, end_time, created_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (client_id, trial_type, duration_hours, end_time, session.get('username', 'admin')))
    
    # Update client trial end date
    cursor.execute('''
        UPDATE clients SET trial_end_date = ?, subscription_status = 'trial' WHERE id = ?
    ''', (end_time, client_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': f'Trial created for {duration_hours} hours',
        'end_time': end_time.isoformat()
    })

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.*, c.client_name 
        FROM users u 
        LEFT JOIN clients c ON u.client_id = c.id 
        ORDER BY u.created_at DESC
    ''')
    users = cursor.fetchall()
    conn.close()
    
    users_data = []
    for user in users:
        users_data.append({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'role': user[4],
            'client_id': user[5],
            'client_name': user[8] if len(user) > 8 else 'No Client',
            'is_active': user[6],
            'created_at': user[7]
        })
    
    return jsonify(users_data)

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'viewer')
    client_id = data.get('client_id')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    password_hash = hash_password(password)
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, client_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, password_hash, role, client_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'User {username} created successfully'
        })
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Username or email already exists'}), 400

@app.route('/api/generate-demo-data')
@login_required
def generate_demo_data():
    # Generate demo visitor data
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute('DELETE FROM visitor_investigations')
    
    # Demo data with comprehensive information
    demo_visitors = [
        {
            'name': 'Sarah Johnson',
            'email': 'sarah.johnson@microsoft.com',
            'phone': '+1-555-0123',
            'company': 'Microsoft Corporation',
            'title': 'VP of Marketing',
            'industry': 'Technology',
            'location': 'United States, Washington, Seattle',
            'device': 'Desktop',
            'browser': 'Chrome',
            'duration': 1256,
            'pages': ['/blog', '/pricing', '/features'],
            'interest': 'HIGH',
            'referral': 'Google Search',
            'sessions': 3,
            'page_views': 8
        },
        {
            'name': 'Michael Chen',
            'email': 'm.chen@apple.com',
            'phone': '+1-555-0456',
            'company': 'Apple Inc.',
            'title': 'Product Manager',
            'industry': 'Technology',
            'location': 'United States, California, Cupertino',
            'device': 'Mobile',
            'browser': 'Safari',
            'duration': 847,
            'pages': ['/home', '/about', '/contact'],
            'interest': 'MEDIUM',
            'referral': 'LinkedIn',
            'sessions': 2,
            'page_views': 5
        },
        {
            'name': 'Emma Rodriguez',
            'email': 'emma.r@google.com',
            'phone': '+1-555-0789',
            'company': 'Google LLC',
            'title': 'Software Engineer',
            'industry': 'Technology',
            'location': 'United States, California, Mountain View',
            'device': 'Tablet',
            'browser': 'Chrome',
            'duration': 423,
            'pages': ['/api', '/docs'],
            'interest': 'LOW',
            'referral': 'Direct',
            'sessions': 1,
            'page_views': 2
        },
        {
            'name': 'David Wilson',
            'email': 'david.wilson@salesforce.com',
            'phone': '+1-555-0321',
            'company': 'Salesforce',
            'title': 'Sales Director',
            'industry': 'Software',
            'location': 'United States, California, San Francisco',
            'device': 'Desktop',
            'browser': 'Firefox',
            'duration': 1890,
            'pages': ['/pricing', '/demo', '/contact', '/features'],
            'interest': 'HIGH',
            'referral': 'Facebook Ads',
            'sessions': 4,
            'page_views': 12
        },
        {
            'name': 'Lisa Thompson',
            'email': 'lisa.t@amazon.com',
            'phone': '+1-555-0654',
            'company': 'Amazon',
            'title': 'Marketing Manager',
            'industry': 'E-commerce',
            'location': 'United States, Washington, Seattle',
            'device': 'Mobile',
            'browser': 'Chrome',
            'duration': 672,
            'pages': ['/home', '/pricing'],
            'interest': 'MEDIUM',
            'referral': 'Twitter',
            'sessions': 1,
            'page_views': 3
        }
    ]
    
    for visitor in demo_visitors:
        visitor_id = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        cursor.execute('''
            INSERT INTO visitor_investigations 
            (visitor_id, name, email, phone, company, job_title, industry, 
             location_country, device_type, browser, pages_visited, visit_duration, 
             interest_level, referral_source, session_count, total_page_views,
             first_visit, last_activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            visitor_id, visitor['name'], visitor['email'], visitor['phone'],
            visitor['company'], visitor['title'], visitor['industry'],
            visitor['location'], visitor['device'], visitor['browser'],
            json.dumps(visitor['pages']), visitor['duration'], visitor['interest'],
            visitor['referral'], visitor['sessions'], visitor['page_views']
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'status': 'success', 'message': 'Demo data generated with comprehensive visitor information'})

@app.route('/api/visitors')
@login_required
def get_visitors():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM visitor_investigations ORDER BY last_activity DESC')
    visitors = cursor.fetchall()
    conn.close()
    
    visitors_data = []
    for visitor in visitors:
        pages_visited = json.loads(visitor[23] or '[]')
        visitors_data.append({
            'id': visitor[0],
            'name': visitor[2] or 'Anonymous',
            'email': visitor[3] or '',
            'phone': visitor[4] or '',
            'company': visitor[5] or 'Unknown Company',
            'title': visitor[6] or 'Unknown Title',
            'industry': visitor[7] or 'Unknown Industry',
            'location': visitor[9] or 'Unknown',
            'device': visitor[14] or 'Unknown',
            'browser': visitor[16] or 'Unknown',
            'pages_visited': pages_visited,
            'duration': visitor[24] or 0,
            'interest_level': visitor[27] or 'LOW',
            'referral_source': visitor[19] or 'Direct',
            'session_count': visitor[25] or 1,
            'total_page_views': visitor[26] or len(pages_visited),
            'current_page': visitor[22] or (pages_visited[-1] if pages_visited else '/'),
            'last_activity': visitor[29]
        })
    
    return jsonify(visitors_data)

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT, debug=False)

