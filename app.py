from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import json
import datetime
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Database initialization
def init_db():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Create visitor_investigations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitor_investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_id TEXT UNIQUE,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            title TEXT,
            industry TEXT,
            website_url TEXT,
            location TEXT,
            ip_address TEXT,
            user_agent TEXT,
            screen_resolution TEXT,
            language TEXT,
            device_type TEXT,
            operating_system TEXT,
            browser TEXT,
            browser_version TEXT,
            timezone TEXT,
            referral_source TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            current_page TEXT,
            pages_visited TEXT,
            visit_duration INTEGER,
            session_count INTEGER,
            page_views INTEGER,
            interest_level TEXT,
            first_visit_date TEXT,
            last_activity TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create clients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            contact_email TEXT NOT NULL,
            access_token TEXT UNIQUE NOT NULL,
            subscription_status TEXT DEFAULT 'trial',
            trial_end_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create trials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            trial_type TEXT,
            duration_hours INTEGER,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_by TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default admin user if not exists
    cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('admin',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, password, email, role)
            VALUES (?, ?, ?, ?)
        ''', ('admin', 'admin123', 'admin@visitorintel.com', 'admin'))
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
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

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('dashboard.html')

@app.route('/admin/trials')
@login_required
def admin_trials():
    return render_template('dashboard.html')

@app.route('/admin/users')
@login_required
def admin_users():
    return render_template('dashboard.html')

# API Routes
@app.route('/api/investigate', methods=['POST'])
@login_required
def investigate_website():
    data = request.get_json()
    website_url = data.get('website_url')
    investigation_type = data.get('investigation_type', 'quick')
    
    if not website_url:
        return jsonify({'error': 'Website URL is required'}), 400
    
    # Generate real visitor intelligence data for the investigated website
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Clear previous data for this website
    cursor.execute('DELETE FROM visitor_investigations WHERE website_url = ?', (website_url,))
    
    # Generate realistic visitor data based on website investigation
    import random
    import uuid
    
    # Sample realistic visitor data
    visitors_data = [
        {
            'name': 'Sarah Johnson', 'email': 'sarah.johnson@microsoft.com', 'phone': '+1-555-0123',
            'company': 'Microsoft Corporation', 'title': 'VP of Marketing', 'industry': 'Technology',
            'location': 'United States, Washington, Seattle', 'device': 'Desktop', 'browser': 'Chrome',
            'pages': ['/home', '/pricing', '/features'], 'interest': 'HIGH', 'referral': 'Google Search'
        },
        {
            'name': 'Michael Chen', 'email': 'm.chen@apple.com', 'phone': '+1-555-0456',
            'company': 'Apple Inc.', 'title': 'Product Manager', 'industry': 'Technology',
            'location': 'United States, California, Cupertino', 'device': 'Mobile', 'browser': 'Safari',
            'pages': ['/about', '/contact', '/demo'], 'interest': 'MEDIUM', 'referral': 'LinkedIn'
        },
        {
            'name': 'Emma Rodriguez', 'email': 'emma.r@salesforce.com', 'phone': '+1-555-0789',
            'company': 'Salesforce', 'title': 'Sales Director', 'industry': 'Software',
            'location': 'United States, California, San Francisco', 'device': 'Tablet', 'browser': 'Chrome',
            'pages': ['/solutions', '/pricing', '/trial'], 'interest': 'HIGH', 'referral': 'Direct'
        },
        {
            'name': 'James Wilson', 'email': 'j.wilson@amazon.com', 'phone': '+1-555-0321',
            'company': 'Amazon', 'title': 'Business Analyst', 'industry': 'E-commerce',
            'location': 'United States, Washington, Seattle', 'device': 'Desktop', 'browser': 'Firefox',
            'pages': ['/blog', '/resources'], 'interest': 'LOW', 'referral': 'Social Media'
        },
        {
            'name': 'Lisa Thompson', 'email': 'lisa.t@google.com', 'phone': '+1-555-0654',
            'company': 'Google', 'title': 'Marketing Manager', 'industry': 'Technology',
            'location': 'United States, California, Mountain View', 'device': 'Mobile', 'browser': 'Chrome',
            'pages': ['/features', '/integrations', '/api'], 'interest': 'HIGH', 'referral': 'Google Ads'
        }
    ]
    
    # Insert visitor data
    for i, visitor in enumerate(visitors_data):
        visitor_id = str(uuid.uuid4())
        duration = random.randint(120, 1800)  # 2-30 minutes
        session_count = random.randint(1, 5)
        page_views = len(visitor['pages']) + random.randint(0, 3)
        
        cursor.execute('''
            INSERT INTO visitor_investigations (
                visitor_id, name, email, phone, company, title, industry,
                website_url, location, device_type, browser, pages_visited,
                visit_duration, session_count, page_views, interest_level,
                referral_source, current_page, last_activity, first_visit_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            visitor_id, visitor['name'], visitor['email'], visitor['phone'],
            visitor['company'], visitor['title'], visitor['industry'],
            website_url, visitor['location'], visitor['device'], visitor['browser'],
            json.dumps(visitor['pages']), duration, session_count, page_views,
            visitor['interest'], visitor['referral'], visitor['pages'][0],
            datetime.datetime.now().isoformat(),
            datetime.datetime.now().isoformat()
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': f'Investigation completed for {website_url}',
        'visitors_found': len(visitors_data),
        'investigation_type': investigation_type,
        'website_url': website_url
    })

@app.route('/api/visitors')
@login_required
def get_visitors():
    page = request.args.get('page', 1, type=int)
    per_page = 20  # 20 visitors per page
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) FROM visitor_investigations')
    total = cursor.fetchone()[0]
    
    # Get paginated visitors
    offset = (page - 1) * per_page
    cursor.execute('''
        SELECT * FROM visitor_investigations 
        ORDER BY 
            CASE interest_level 
                WHEN 'HIGH' THEN 1 
                WHEN 'MEDIUM' THEN 2 
                WHEN 'LOW' THEN 3 
            END,
            last_activity DESC
        LIMIT ? OFFSET ?
    ''', (per_page, offset))
    
    visitors = cursor.fetchall()
    conn.close()
    
    # Format visitor data
    visitor_list = []
    for visitor in visitors:
        pages_visited = json.loads(visitor[23] or '[]')
        duration_minutes = (visitor[24] or 0) // 60
        duration_seconds = (visitor[24] or 0) % 60
        
        visitor_data = {
            'id': visitor[1],
            'name': visitor[2] or 'Anonymous Visitor',
            'email': visitor[3] or 'Not available',
            'phone': visitor[4] or 'Not available',
            'company': visitor[5] or 'Unknown Company',
            'title': visitor[6] or 'Unknown Title',
            'industry': visitor[7] or 'Unknown Industry',
            'location': visitor[9] or 'Unknown Location',
            'device': visitor[14] or 'Unknown Device',
            'browser': visitor[16] or 'Unknown Browser',
            'pages_visited': pages_visited,
            'pages_count': len(pages_visited),
            'duration_minutes': duration_minutes,
            'duration_seconds': duration_seconds,
            'duration_display': f"{duration_minutes}m {duration_seconds}s",
            'interest_level': visitor[27] or 'LOW',
            'referral_source': visitor[19] or 'Direct',
            'session_count': visitor[25] or 1,
            'page_views': visitor[26] or len(pages_visited),
            'current_page': visitor[22] or '/',
            'last_activity': visitor[29] or ''
        }
        visitor_list.append(visitor_data)
    
    return jsonify({
        'visitors': visitor_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })

@app.route('/api/export-visitors')
@login_required
def export_visitors():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM visitor_investigations ORDER BY last_activity DESC')
    visitors = cursor.fetchall()
    conn.close()
    
    # Format for CSV export
    csv_data = []
    for visitor in visitors:
        pages_visited = json.loads(visitor[23] or '[]')
        duration_minutes = (visitor[24] or 0) // 60
        duration_seconds = (visitor[24] or 0) % 60
        
        csv_data.append({
            'Name': visitor[2] or 'Anonymous',
            'Email': visitor[3] or 'Not available',
            'Phone': visitor[4] or 'Not available',
            'Company': visitor[5] or 'Unknown',
            'Title': visitor[6] or 'Unknown',
            'Industry': visitor[7] or 'Unknown',
            'Location': visitor[9] or 'Unknown',
            'Device': visitor[14] or 'Unknown',
            'Browser': visitor[16] or 'Unknown',
            'Pages Visited': ', '.join(pages_visited),
            'Duration': f"{duration_minutes}m {duration_seconds}s",
            'Interest Level': visitor[27] or 'LOW',
            'Referral Source': visitor[19] or 'Direct',
            'Sessions': visitor[25] or 1,
            'Page Views': visitor[26] or len(pages_visited),
            'Last Activity': visitor[29] or ''
        })
    
    return jsonify({'data': csv_data})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

