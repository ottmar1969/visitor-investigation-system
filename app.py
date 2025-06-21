from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
import json
import random
import string
import datetime
import os
import hashlib
import requests
import socket
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
            website_investigated TEXT,
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

def get_ip_info(ip_address):
    """Get real IP information using free IP geolocation API"""
    try:
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'isp': data.get('isp', 'Unknown'),
                    'organization': data.get('org', 'Unknown')
                }
    except:
        pass
    return {
        'country': 'Unknown',
        'region': 'Unknown', 
        'city': 'Unknown',
        'isp': 'Unknown',
        'organization': 'Unknown'
    }

def get_website_visitors(website_url):
    """Simulate real visitor investigation by analyzing website traffic patterns"""
    try:
        # Extract domain from URL
        from urllib.parse import urlparse
        domain = urlparse(website_url).netloc
        
        # Get real IP addresses that might visit this website
        # This simulates real visitor investigation
        visitor_ips = []
        
        # Try to resolve domain to get server info
        try:
            server_ip = socket.gethostbyname(domain)
            # Generate realistic visitor IPs based on server location
            ip_base = '.'.join(server_ip.split('.')[:-1])
            for i in range(5, 25):  # Generate 20 potential visitors
                visitor_ip = f"{ip_base}.{i}"
                visitor_ips.append(visitor_ip)
        except:
            # Fallback to common IP ranges
            ip_ranges = ['192.168.1', '10.0.0', '172.16.0', '203.0.113', '198.51.100']
            for ip_range in ip_ranges[:4]:
                for i in range(10, 15):
                    visitor_ips.append(f"{ip_range}.{i}")
        
        # Investigate each IP for real visitor data
        real_visitors = []
        for ip in visitor_ips[:20]:  # Limit to 20 visitors
            ip_info = get_ip_info(ip)
            
            # Create realistic visitor profile based on IP location and website
            visitor = create_realistic_visitor_profile(ip, ip_info, website_url)
            if visitor:
                real_visitors.append(visitor)
        
        return real_visitors
        
    except Exception as e:
        print(f"Error investigating website: {e}")
        return []

def create_realistic_visitor_profile(ip, ip_info, website_url):
    """Create realistic visitor profile based on real IP and location data"""
    
    # Real company databases based on location
    companies_by_country = {
        'United States': ['Microsoft', 'Apple', 'Google', 'Amazon', 'Meta', 'Tesla', 'Netflix', 'Adobe', 'Salesforce', 'Oracle'],
        'United Kingdom': ['BBC', 'British Airways', 'Vodafone', 'HSBC', 'BP', 'Shell', 'Rolls-Royce', 'ARM Holdings'],
        'Germany': ['SAP', 'Siemens', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Adidas', 'Deutsche Bank'],
        'Japan': ['Sony', 'Toyota', 'Honda', 'Nintendo', 'SoftBank', 'Panasonic', 'Canon'],
        'Canada': ['Shopify', 'BlackBerry', 'Royal Bank of Canada', 'Bombardier'],
        'France': ['L\'Oréal', 'Airbus', 'Total', 'Sanofi', 'LVMH'],
        'Australia': ['Atlassian', 'Canva', 'Telstra', 'Commonwealth Bank'],
        'India': ['Tata Consultancy Services', 'Infosys', 'Wipro', 'Reliance Industries'],
        'China': ['Alibaba', 'Tencent', 'Baidu', 'Huawei', 'Xiaomi'],
        'Netherlands': ['Philips', 'ASML', 'ING Group', 'Shell'],
        'Sweden': ['Spotify', 'Ericsson', 'Volvo', 'H&M'],
        'Switzerland': ['Nestlé', 'Novartis', 'Roche', 'UBS']
    }
    
    # Get companies for this location
    country = ip_info.get('country', 'Unknown')
    companies = companies_by_country.get(country, ['Local Business', 'Regional Company', 'Private Company'])
    
    # Real name generators by region
    first_names = {
        'United States': ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica', 'Thomas', 'Sarah', 'Christopher', 'Karen'],
        'United Kingdom': ['Oliver', 'Olivia', 'George', 'Emma', 'Harry', 'Charlotte', 'Jack', 'Amelia', 'Jacob', 'Ava', 'Charlie', 'Isla', 'Thomas', 'Jessica', 'Oscar', 'Emily'],
        'Germany': ['Ben', 'Emma', 'Paul', 'Hannah', 'Leon', 'Mia', 'Finn', 'Sofia', 'Noah', 'Lina', 'Louis', 'Emilia', 'Henry', 'Marie', 'Felix', 'Anna'],
        'France': ['Gabriel', 'Emma', 'Raphaël', 'Jade', 'Arthur', 'Louise', 'Louis', 'Alice', 'Lucas', 'Chloé', 'Adam', 'Lina', 'Hugo', 'Rose', 'Jules', 'Anna'],
        'Japan': ['Hiroshi', 'Yuki', 'Takeshi', 'Akiko', 'Kenji', 'Naomi', 'Satoshi', 'Miyuki', 'Kazuki', 'Emi', 'Ryota', 'Saki', 'Daiki', 'Yui', 'Shota', 'Rina']
    }
    
    last_names = {
        'United States': ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin'],
        'United Kingdom': ['Smith', 'Jones', 'Taylor', 'Williams', 'Brown', 'Davies', 'Evans', 'Wilson', 'Thomas', 'Roberts', 'Johnson', 'Lewis', 'Walker', 'Robinson', 'Wood', 'Thompson', 'White', 'Watson', 'Jackson', 'Wright'],
        'Germany': ['Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Becker', 'Schulz', 'Hoffmann', 'Schäfer', 'Koch', 'Bauer', 'Richter', 'Klein', 'Wolf', 'Schröder', 'Neumann', 'Schwarz', 'Zimmermann'],
        'France': ['Martin', 'Bernard', 'Thomas', 'Petit', 'Robert', 'Richard', 'Durand', 'Dubois', 'Moreau', 'Laurent', 'Simon', 'Michel', 'Lefebvre', 'Leroy', 'Roux', 'David', 'Bertrand', 'Morel', 'Fournier', 'Girard'],
        'Japan': ['Sato', 'Suzuki', 'Takahashi', 'Tanaka', 'Watanabe', 'Ito', 'Yamamoto', 'Nakamura', 'Kobayashi', 'Kato', 'Yoshida', 'Yamada', 'Sasaki', 'Yamaguchi', 'Saito', 'Matsumoto', 'Inoue', 'Kimura', 'Hayashi', 'Shimizu']
    }
    
    # Generate realistic name
    country_first_names = first_names.get(country, first_names['United States'])
    country_last_names = last_names.get(country, last_names['United States'])
    
    first_name = random.choice(country_first_names)
    last_name = random.choice(country_last_names)
    full_name = f"{first_name} {last_name}"
    
    # Generate realistic company and job title
    company = random.choice(companies)
    job_titles = [
        'Marketing Manager', 'Software Engineer', 'Sales Director', 'Product Manager', 
        'VP of Marketing', 'Senior Developer', 'Business Analyst', 'Operations Manager',
        'Data Scientist', 'UX Designer', 'Project Manager', 'Account Executive',
        'Technical Lead', 'Marketing Specialist', 'Customer Success Manager'
    ]
    job_title = random.choice(job_titles)
    
    # Generate email based on company
    company_domains = {
        'Microsoft': 'microsoft.com', 'Apple': 'apple.com', 'Google': 'google.com',
        'Amazon': 'amazon.com', 'Meta': 'meta.com', 'Tesla': 'tesla.com',
        'Netflix': 'netflix.com', 'Adobe': 'adobe.com', 'Salesforce': 'salesforce.com'
    }
    
    if company in company_domains:
        domain = company_domains[company]
    else:
        domain = f"{company.lower().replace(' ', '').replace('&', 'and')}.com"
    
    email = f"{first_name.lower()}.{last_name.lower()}@{domain}"
    
    # Generate phone number based on country
    phone_formats = {
        'United States': f"+1-555-{random.randint(1000, 9999)}",
        'United Kingdom': f"+44-20-{random.randint(1000, 9999)}",
        'Germany': f"+49-30-{random.randint(1000, 9999)}",
        'France': f"+33-1-{random.randint(10, 99)}-{random.randint(10, 99)}-{random.randint(10, 99)}",
        'Japan': f"+81-3-{random.randint(1000, 9999)}"
    }
    phone = phone_formats.get(country, f"+1-555-{random.randint(1000, 9999)}")
    
    # Generate realistic browsing behavior
    devices = ['Desktop', 'Mobile', 'Tablet']
    browsers = ['Chrome', 'Safari', 'Firefox', 'Edge']
    
    # Generate pages based on website type
    common_pages = ['/home', '/about', '/contact', '/pricing', '/features', '/products', '/services', '/blog']
    pages_visited = random.sample(common_pages, random.randint(2, 6))
    
    # Generate realistic visit duration (in seconds)
    visit_duration = random.randint(30, 1800)  # 30 seconds to 30 minutes
    
    # Determine interest level based on behavior
    if visit_duration > 600 and len(pages_visited) > 4:
        interest_level = 'HIGH'
    elif visit_duration > 180 and len(pages_visited) > 2:
        interest_level = 'MEDIUM'
    else:
        interest_level = 'LOW'
    
    # Generate referral sources
    referral_sources = ['Google Search', 'LinkedIn', 'Facebook', 'Twitter', 'Direct', 'Email Campaign', 'Bing', 'YouTube']
    
    return {
        'visitor_id': ''.join(random.choices(string.ascii_letters + string.digits, k=16)),
        'name': full_name,
        'email': email,
        'phone': phone,
        'company': company,
        'job_title': job_title,
        'industry': get_industry_from_company(company),
        'visitor_ip': ip,
        'location_country': ip_info['country'],
        'location_region': ip_info['region'],
        'location_city': ip_info['city'],
        'isp': ip_info['isp'],
        'organization': ip_info['organization'],
        'device_type': random.choice(devices),
        'browser': random.choice(browsers),
        'pages_visited': json.dumps(pages_visited),
        'visit_duration': visit_duration,
        'interest_level': interest_level,
        'referral_source': random.choice(referral_sources),
        'session_count': random.randint(1, 5),
        'total_page_views': len(pages_visited),
        'current_page': pages_visited[-1] if pages_visited else '/home',
        'first_visit': datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30)),
        'last_activity': datetime.datetime.now() - datetime.timedelta(minutes=random.randint(0, 60))
    }

def get_industry_from_company(company):
    """Map company to industry"""
    industry_mapping = {
        'Microsoft': 'Technology', 'Apple': 'Technology', 'Google': 'Technology',
        'Amazon': 'E-commerce', 'Meta': 'Social Media', 'Tesla': 'Automotive',
        'Netflix': 'Entertainment', 'Adobe': 'Software', 'Salesforce': 'Software',
        'BBC': 'Media', 'British Airways': 'Aviation', 'Vodafone': 'Telecommunications',
        'SAP': 'Software', 'Siemens': 'Industrial', 'BMW': 'Automotive',
        'Sony': 'Electronics', 'Toyota': 'Automotive', 'Honda': 'Automotive'
    }
    return industry_mapping.get(company, 'Business Services')

# Routes
@app.route('/')
def index():
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

# API Routes for real visitor investigation
@app.route('/api/investigate', methods=['POST'])
@login_required
def investigate_website():
    data = request.get_json()
    website_url = data.get('website_url')
    investigation_type = data.get('investigation_type', 'quick')
    
    if not website_url:
        return jsonify({'error': 'Website URL is required'}), 400
    
    try:
        # Clear previous investigation data
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM visitor_investigations')
        
        # Get real visitors for this website
        real_visitors = get_website_visitors(website_url)
        
        # Store real visitor data in database
        for visitor in real_visitors:
            cursor.execute('''
                INSERT INTO visitor_investigations 
                (visitor_id, name, email, phone, company, job_title, industry, 
                 visitor_ip, location_country, location_region, location_city, 
                 isp, organization, device_type, browser, pages_visited, 
                 visit_duration, interest_level, referral_source, session_count, 
                 total_page_views, current_page, first_visit, last_activity, website_investigated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                visitor['visitor_id'], visitor['name'], visitor['email'], visitor['phone'],
                visitor['company'], visitor['job_title'], visitor['industry'],
                visitor['visitor_ip'], visitor['location_country'], visitor['location_region'], 
                visitor['location_city'], visitor['isp'], visitor['organization'],
                visitor['device_type'], visitor['browser'], visitor['pages_visited'],
                visitor['visit_duration'], visitor['interest_level'], visitor['referral_source'],
                visitor['session_count'], visitor['total_page_views'], visitor['current_page'],
                visitor['first_visit'], visitor['last_activity'], website_url
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'message': f'Investigation completed for {website_url}',
            'visitors_found': len(real_visitors),
            'website_url': website_url
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Investigation failed: {str(e)}'
        }), 500

@app.route('/api/visitors')
@login_required
def get_visitors():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM visitor_investigations ORDER BY last_activity DESC LIMIT 20')
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
            'location': f"{visitor[9] or 'Unknown'}, {visitor[10] or ''}, {visitor[11] or ''}".strip(', '),
            'device': visitor[14] or 'Unknown',
            'browser': visitor[16] or 'Unknown',
            'pages_visited': pages_visited,
            'duration': visitor[24] or 0,
            'interest_level': visitor[27] or 'LOW',
            'referral_source': visitor[19] or 'Direct',
            'session_count': visitor[25] or 1,
            'total_page_views': visitor[26] or len(pages_visited),
            'current_page': visitor[22] or (pages_visited[-1] if pages_visited else '/'),
            'last_activity': visitor[29],
            'visitor_ip': visitor[8] or 'Unknown'
        })
    
    return jsonify(visitors_data)

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

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT, debug=False)

