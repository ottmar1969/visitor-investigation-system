from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
import sqlite3
import json
import random
import string
import datetime
import os
import schedule
import time
import threading
from openpyxl import Workbook
import csv
import io
import requests
import hashlib

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'
CORS(app)

# Database initialization
def init_db():
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Enhanced visitor investigations table with comprehensive data
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
            pages_visited TEXT,  -- JSON array
            visit_duration INTEGER,  -- in seconds
            session_count INTEGER,
            total_page_views INTEGER,
            interest_level TEXT,
            first_visit TIMESTAMP,
            last_activity TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Clients table for multi-tenant system
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
    
    # Users table for access control
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            client_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            allowed_countries TEXT,  -- JSON array
            access_expires TIMESTAMP,
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
            converted_to_paid BOOLEAN DEFAULT 0,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

# Helper functions
def generate_access_token():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

def generate_visitor_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

def get_ip_info(ip_address):
    """Get geographic and ISP information from IP address"""
    try:
        # Using a free IP geolocation service
        response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=5)
        if response.status_code == 200:
            data = response.json()
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

def parse_user_agent(user_agent):
    """Extract device, OS, and browser info from user agent"""
    device_type = 'Desktop'
    operating_system = 'Unknown'
    browser = 'Unknown'
    
    if 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent:
        device_type = 'Mobile'
    elif 'Tablet' in user_agent or 'iPad' in user_agent:
        device_type = 'Tablet'
    
    if 'Windows' in user_agent:
        operating_system = 'Windows'
    elif 'Mac OS' in user_agent or 'macOS' in user_agent:
        operating_system = 'macOS'
    elif 'Linux' in user_agent:
        operating_system = 'Linux'
    elif 'Android' in user_agent:
        operating_system = 'Android'
    elif 'iOS' in user_agent or 'iPhone' in user_agent or 'iPad' in user_agent:
        operating_system = 'iOS'
    
    if 'Chrome' in user_agent:
        browser = 'Chrome'
    elif 'Firefox' in user_agent:
        browser = 'Firefox'
    elif 'Safari' in user_agent and 'Chrome' not in user_agent:
        browser = 'Safari'
    elif 'Edge' in user_agent:
        browser = 'Edge'
    
    return device_type, operating_system, browser

def calculate_interest_level(pages_visited, visit_duration, page_views):
    """Calculate visitor interest level based on engagement metrics"""
    score = 0
    
    # Points for pages visited
    if len(pages_visited) >= 5:
        score += 3
    elif len(pages_visited) >= 3:
        score += 2
    elif len(pages_visited) >= 2:
        score += 1
    
    # Points for time on site (in seconds)
    if visit_duration >= 300:  # 5+ minutes
        score += 3
    elif visit_duration >= 120:  # 2+ minutes
        score += 2
    elif visit_duration >= 60:  # 1+ minute
        score += 1
    
    # Points for page views
    if page_views >= 10:
        score += 2
    elif page_views >= 5:
        score += 1
    
    if score >= 6:
        return 'HIGH'
    elif score >= 3:
        return 'MEDIUM'
    else:
        return 'LOW'

# Routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/trials')
def admin_trials():
    return render_template('admin_trials.html')

@app.route('/admin/users')
def user_management():
    return render_template('user_management.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/client/<access_token>')
def client_dashboard(access_token):
    # Verify access token
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients WHERE access_token = ? AND is_active = 1', (access_token,))
    client = cursor.fetchone()
    conn.close()
    
    if not client:
        return render_template('access_denied.html')
    
    return render_template('client_dashboard.html', access_token=access_token)

@app.route('/access-denied')
def access_denied():
    return render_template('access_denied.html')

# API Routes

@app.route('/api/investigate', methods=['POST'])
def investigate():
    """Main visitor tracking endpoint"""
    try:
        data = request.get_json() or {}
        visitor_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Get IP information
        ip_info = get_ip_info(visitor_ip)
        
        # Parse user agent
        device_type, operating_system, browser = parse_user_agent(user_agent)
        
        # Generate or get visitor ID
        visitor_id = data.get('visitor_id') or generate_visitor_id()
        
        # Extract data from request
        current_page = data.get('current_page', '/')
        referral_source = data.get('referral_source', request.headers.get('Referer', 'Direct'))
        
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        
        # Check if visitor exists
        cursor.execute('SELECT * FROM visitor_investigations WHERE visitor_id = ?', (visitor_id,))
        existing_visitor = cursor.fetchone()
        
        if existing_visitor:
            # Update existing visitor
            pages_visited = json.loads(existing_visitor[19] or '[]')
            if current_page not in pages_visited:
                pages_visited.append(current_page)
            
            visit_duration = existing_visitor[20] + 30  # Add 30 seconds
            session_count = existing_visitor[21]
            total_page_views = existing_visitor[22] + 1
            
            interest_level = calculate_interest_level(pages_visited, visit_duration, total_page_views)
            
            cursor.execute('''
                UPDATE visitor_investigations 
                SET current_page = ?, pages_visited = ?, visit_duration = ?, 
                    total_page_views = ?, interest_level = ?, last_activity = CURRENT_TIMESTAMP
                WHERE visitor_id = ?
            ''', (current_page, json.dumps(pages_visited), visit_duration, 
                  total_page_views, interest_level, visitor_id))
        else:
            # Create new visitor
            pages_visited = [current_page]
            visit_duration = 30  # Initial 30 seconds
            session_count = 1
            total_page_views = 1
            interest_level = 'LOW'
            
            cursor.execute('''
                INSERT INTO visitor_investigations 
                (visitor_id, visitor_ip, location_country, location_region, location_city,
                 isp, organization, device_type, operating_system, browser, user_agent,
                 referral_source, traffic_source, entry_page, current_page, pages_visited,
                 visit_duration, session_count, total_page_views, interest_level,
                 first_visit, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (visitor_id, visitor_ip, ip_info['country'], ip_info['region'], ip_info['city'],
                  ip_info['isp'], ip_info['organization'], device_type, operating_system, browser,
                  user_agent, referral_source, 'Organic', current_page, current_page,
                  json.dumps(pages_visited), visit_duration, session_count, total_page_views, interest_level))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'visitor_id': visitor_id,
            'message': 'Visitor tracked successfully'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/client-visitors/<access_token>')
def get_client_visitors(access_token):
    """Get all visitors for a client dashboard"""
    try:
        # Verify access token
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE access_token = ? AND is_active = 1', (access_token,))
        client = cursor.fetchone()
        
        if not client:
            return jsonify({'error': 'Invalid access token'}), 403
        
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        per_page = 50
        offset = (page - 1) * per_page
        
        # Get visitors sorted by interest level and visit duration
        cursor.execute('''
            SELECT * FROM visitor_investigations 
            ORDER BY 
                CASE interest_level 
                    WHEN 'HIGH' THEN 1 
                    WHEN 'MEDIUM' THEN 2 
                    WHEN 'LOW' THEN 3 
                END,
                visit_duration DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        visitors = cursor.fetchall()
        
        # Get total count
        cursor.execute('SELECT COUNT(*) FROM visitor_investigations')
        total_visitors = cursor.fetchone()[0]
        
        conn.close()
        
        # Format visitors data
        visitors_data = []
        for visitor in visitors:
            pages_visited = json.loads(visitor[19] or '[]')
            visitors_data.append({
                'id': visitor[0],
                'visitor_id': visitor[1],
                'name': visitor[2] or 'Anonymous',
                'email': visitor[3] or '',
                'phone': visitor[4] or '',
                'company': visitor[5] or 'Unknown Company',
                'job_title': visitor[6] or 'Unknown Title',
                'industry': visitor[7] or 'Unknown Industry',
                'visitor_ip': visitor[8],
                'location': f"{visitor[9]}, {visitor[10]}, {visitor[11]}",
                'isp': visitor[12],
                'organization': visitor[13],
                'device_type': visitor[14],
                'operating_system': visitor[15],
                'browser': visitor[16],
                'screen_resolution': visitor[17] or 'Unknown',
                'user_agent': visitor[18],
                'referral_source': visitor[19],
                'traffic_source': visitor[20],
                'entry_page': visitor[21],
                'current_page': visitor[22],
                'pages_visited': pages_visited,
                'visit_duration': visitor[24],
                'session_count': visitor[25],
                'total_page_views': visitor[26],
                'interest_level': visitor[27],
                'first_visit': visitor[28],
                'last_activity': visitor[29]
            })
        
        return jsonify({
            'visitors': visitors_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_visitors': total_visitors,
                'total_pages': (total_visitors + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-demo-data/<access_token>')
def generate_demo_data(access_token):
    """Generate comprehensive demo visitor data"""
    try:
        # Verify access token
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE access_token = ? AND is_active = 1', (access_token,))
        client = cursor.fetchone()
        
        if not client:
            return jsonify({'error': 'Invalid access token'}), 403
        
        # Clear existing demo data
        cursor.execute('DELETE FROM visitor_investigations')
        
        # Demo data templates
        companies = [
            'Microsoft Corporation', 'Apple Inc.', 'Google LLC', 'Amazon.com Inc.', 'Meta Platforms',
            'Tesla Inc.', 'Netflix Inc.', 'Adobe Inc.', 'Salesforce Inc.', 'Oracle Corporation',
            'IBM Corporation', 'Intel Corporation', 'Cisco Systems', 'PayPal Holdings', 'Zoom Video',
            'Shopify Inc.', 'Square Inc.', 'Dropbox Inc.', 'Slack Technologies', 'Atlassian Corporation'
        ]
        
        names = [
            'John Smith', 'Sarah Johnson', 'Michael Brown', 'Emily Davis', 'David Wilson',
            'Jessica Miller', 'Christopher Moore', 'Ashley Taylor', 'Matthew Anderson', 'Amanda Thomas',
            'Daniel Jackson', 'Jennifer White', 'James Harris', 'Lisa Martin', 'Robert Thompson',
            'Michelle Garcia', 'William Martinez', 'Elizabeth Robinson', 'Joseph Clark', 'Mary Rodriguez'
        ]
        
        job_titles = [
            'CEO', 'CTO', 'VP of Marketing', 'Director of Sales', 'Product Manager',
            'Software Engineer', 'Marketing Manager', 'Sales Representative', 'Business Analyst', 'UX Designer',
            'Data Scientist', 'Operations Manager', 'HR Director', 'Financial Analyst', 'Project Manager',
            'Customer Success Manager', 'DevOps Engineer', 'Content Manager', 'Brand Manager', 'Account Executive'
        ]
        
        industries = [
            'Technology', 'Healthcare', 'Finance', 'E-commerce', 'Manufacturing',
            'Education', 'Real Estate', 'Consulting', 'Media', 'Automotive',
            'Telecommunications', 'Energy', 'Retail', 'Insurance', 'Logistics'
        ]
        
        countries = ['United States', 'Canada', 'United Kingdom', 'Germany', 'France', 'Australia', 'Japan', 'Singapore']
        devices = ['Desktop', 'Mobile', 'Tablet']
        browsers = ['Chrome', 'Firefox', 'Safari', 'Edge']
        operating_systems = ['Windows', 'macOS', 'iOS', 'Android', 'Linux']
        
        pages = [
            '/', '/about', '/services', '/products', '/pricing', '/contact', '/blog',
            '/features', '/testimonials', '/case-studies', '/resources', '/support',
            '/careers', '/news', '/partners', '/solutions', '/demo', '/trial'
        ]
        
        # Generate 75 demo visitors
        for i in range(75):
            visitor_id = generate_visitor_id()
            name = random.choice(names)
            company = random.choice(companies)
            job_title = random.choice(job_titles)
            industry = random.choice(industries)
            
            # Generate email based on name and company
            email_name = name.lower().replace(' ', '.')
            company_domain = company.lower().replace(' ', '').replace('.', '').replace(',', '') + '.com'
            email = f"{email_name}@{company_domain}"
            
            # Generate phone number
            phone = f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            
            # Random location and technical details
            country = random.choice(countries)
            device_type = random.choice(devices)
            browser = random.choice(browsers)
            os = random.choice(operating_systems)
            
            # Generate realistic browsing behavior
            num_pages = random.randint(1, 15)
            pages_visited = random.sample(pages, min(num_pages, len(pages)))
            current_page = random.choice(pages_visited)
            entry_page = pages_visited[0]
            
            visit_duration = random.randint(30, 1800)  # 30 seconds to 30 minutes
            session_count = random.randint(1, 10)
            total_page_views = len(pages_visited) + random.randint(0, 5)
            
            interest_level = calculate_interest_level(pages_visited, visit_duration, total_page_views)
            
            # Random IP address
            visitor_ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            
            cursor.execute('''
                INSERT INTO visitor_investigations 
                (visitor_id, name, email, phone, company, job_title, industry, visitor_ip,
                 location_country, location_region, location_city, isp, organization,
                 device_type, operating_system, browser, screen_resolution, user_agent,
                 referral_source, traffic_source, entry_page, current_page, pages_visited,
                 visit_duration, session_count, total_page_views, interest_level,
                 first_visit, last_activity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                visitor_id, name, email, phone, company, job_title, industry, visitor_ip,
                country, 'Unknown Region', 'Unknown City', 'Unknown ISP', company,
                device_type, os, browser, '1920x1080', f'{browser} User Agent',
                'Google Search', 'Organic', entry_page, current_page, json.dumps(pages_visited),
                visit_duration, session_count, total_page_views, interest_level
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'status': 'success', 'message': '75 demo visitors generated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-visitors/<access_token>')
def export_visitors(access_token):
    """Export visitor data as Excel or CSV"""
    try:
        # Verify access token
        conn = sqlite3.connect('visitor_investigations.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE access_token = ? AND is_active = 1', (access_token,))
        client = cursor.fetchone()
        
        if not client:
            return jsonify({'error': 'Invalid access token'}), 403
        
        export_format = request.args.get('format', 'excel')
        
        # Get all visitors
        cursor.execute('SELECT * FROM visitor_investigations ORDER BY last_activity DESC')
        visitors = cursor.fetchall()
        conn.close()
        
        if export_format == 'excel':
            # Create Excel file
            wb = Workbook()
            ws = wb.active
            ws.title = "Visitor Data"
            
            # Headers
            headers = [
                'Visitor ID', 'Name', 'Email', 'Phone', 'Company', 'Job Title', 'Industry',
                'IP Address', 'Country', 'Region', 'City', 'ISP', 'Organization',
                'Device Type', 'Operating System', 'Browser', 'Screen Resolution',
                'Referral Source', 'Traffic Source', 'Entry Page', 'Current Page',
                'Pages Visited', 'Visit Duration (seconds)', 'Session Count', 'Total Page Views',
                'Interest Level', 'First Visit', 'Last Activity'
            ]
            ws.append(headers)
            
            # Data rows
            for visitor in visitors:
                pages_visited = json.loads(visitor[19] or '[]')
                row = [
                    visitor[1], visitor[2] or 'Anonymous', visitor[3] or '', visitor[4] or '',
                    visitor[5] or 'Unknown Company', visitor[6] or 'Unknown Title', visitor[7] or 'Unknown Industry',
                    visitor[8], visitor[9], visitor[10], visitor[11], visitor[12], visitor[13],
                    visitor[14], visitor[15], visitor[16], visitor[17] or 'Unknown',
                    visitor[19], visitor[20], visitor[21], visitor[22],
                    ', '.join(pages_visited), visitor[24], visitor[25], visitor[26],
                    visitor[27], visitor[28], visitor[29]
                ]
                ws.append(row)
            
            # Save to memory
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name='visitor_data.xlsx'
            )
        
        else:  # CSV format
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Headers
            headers = [
                'Visitor ID', 'Name', 'Email', 'Phone', 'Company', 'Job Title', 'Industry',
                'IP Address', 'Country', 'Region', 'City', 'ISP', 'Organization',
                'Device Type', 'Operating System', 'Browser', 'Screen Resolution',
                'Referral Source', 'Traffic Source', 'Entry Page', 'Current Page',
                'Pages Visited', 'Visit Duration (seconds)', 'Session Count', 'Total Page Views',
                'Interest Level', 'First Visit', 'Last Activity'
            ]
            writer.writerow(headers)
            
            # Data rows
            for visitor in visitors:
                pages_visited = json.loads(visitor[19] or '[]')
                row = [
                    visitor[1], visitor[2] or 'Anonymous', visitor[3] or '', visitor[4] or '',
                    visitor[5] or 'Unknown Company', visitor[6] or 'Unknown Title', visitor[7] or 'Unknown Industry',
                    visitor[8], visitor[9], visitor[10], visitor[11], visitor[12], visitor[13],
                    visitor[14], visitor[15], visitor[16], visitor[17] or 'Unknown',
                    visitor[19], visitor[20], visitor[21], visitor[22],
                    ', '.join(pages_visited), visitor[24], visitor[25], visitor[26],
                    visitor[27], visitor[28], visitor[29]
                ]
                writer.writerow(row)
            
            # Convert to bytes
            output.seek(0)
            csv_data = output.getvalue().encode('utf-8')
            output_bytes = io.BytesIO(csv_data)
            
            return send_file(
                output_bytes,
                mimetype='text/csv',
                as_attachment=True,
                download_name='visitor_data.csv'
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Client Management APIs

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients"""
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
def create_client():
    """Create new client"""
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

@app.route('/api/trials', methods=['POST'])
def create_trial():
    """Create trial for client"""
    data = request.get_json()
    client_id = data.get('client_id')
    duration_hours = data.get('duration_hours', 24)
    
    if not client_id:
        return jsonify({'error': 'Client ID is required'}), 400
    
    end_time = datetime.datetime.now() + datetime.timedelta(hours=duration_hours)
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO trials (client_id, duration_hours, end_time)
        VALUES (?, ?, ?)
    ''', (client_id, duration_hours, end_time))
    
    # Update client trial end date
    cursor.execute('''
        UPDATE clients SET trial_end_date = ? WHERE id = ?
    ''', (end_time, client_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'status': 'success',
        'message': f'Trial created for {duration_hours} hours',
        'end_time': end_time.isoformat()
    })

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

# Background task to check expired trials
def check_expired_trials():
    """Background task to deactivate expired trials"""
    while True:
        try:
            conn = sqlite3.connect('visitor_investigations.db')
            cursor = conn.cursor()
            
            # Deactivate expired trials
            cursor.execute('''
                UPDATE clients 
                SET is_active = 0, subscription_status = 'expired'
                WHERE trial_end_date < CURRENT_TIMESTAMP AND subscription_status = 'trial'
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error checking expired trials: {e}")
        
        time.sleep(3600)  # Check every hour

# Start background task
trial_checker_thread = threading.Thread(target=check_expired_trials, daemon=True)
trial_checker_thread.start()

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT, debug=False)

