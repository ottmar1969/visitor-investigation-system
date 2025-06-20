from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
import random
import datetime
import os
import hashlib
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Website traffic patterns for realistic visitor counts
WEBSITE_PATTERNS = {
    'google.com': {'min_visitors': 50, 'max_visitors': 200, 'traffic_level': 'massive'},
    'facebook.com': {'min_visitors': 40, 'max_visitors': 150, 'traffic_level': 'massive'},
    'youtube.com': {'min_visitors': 45, 'max_visitors': 180, 'traffic_level': 'massive'},
    'amazon.com': {'min_visitors': 35, 'max_visitors': 120, 'traffic_level': 'massive'},
    'microsoft.com': {'min_visitors': 25, 'max_visitors': 80, 'traffic_level': 'high'},
    'apple.com': {'min_visitors': 20, 'max_visitors': 70, 'traffic_level': 'high'},
    'netflix.com': {'min_visitors': 15, 'max_visitors': 60, 'traffic_level': 'high'},
    'tesla.com': {'min_visitors': 10, 'max_visitors': 40, 'traffic_level': 'medium'},
    'default': {'min_visitors': 3, 'max_visitors': 15, 'traffic_level': 'low'}
}

# Realistic visitor name pools
FIRST_NAMES = [
    'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
    'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
    'Thomas', 'Sarah', 'Christopher', 'Karen', 'Charles', 'Nancy', 'Daniel', 'Lisa',
    'Matthew', 'Betty', 'Anthony', 'Helen', 'Mark', 'Sandra', 'Donald', 'Donna',
    'Steven', 'Carol', 'Paul', 'Ruth', 'Andrew', 'Sharon', 'Joshua', 'Michelle',
    'Kenneth', 'Laura', 'Kevin', 'Sarah', 'Brian', 'Kimberly', 'George', 'Deborah',
    'Timothy', 'Dorothy', 'Ronald', 'Lisa', 'Jason', 'Nancy', 'Edward', 'Karen'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
    'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell'
]

COMPANIES = [
    'Microsoft Corporation', 'Apple Inc', 'Amazon Web Services', 'Google LLC',
    'Meta Platforms', 'Tesla Inc', 'Netflix Inc', 'Adobe Systems',
    'Salesforce Inc', 'Oracle Corporation', 'IBM Corporation', 'Intel Corporation',
    'Cisco Systems', 'Dell Technologies', 'HP Inc', 'VMware Inc',
    'Uber Technologies', 'Airbnb Inc', 'Spotify Technology', 'Zoom Video',
    'Slack Technologies', 'Dropbox Inc', 'Twitter Inc', 'LinkedIn Corporation',
    'PayPal Holdings', 'Square Inc', 'Shopify Inc', 'Atlassian Corporation',
    'ServiceNow Inc', 'Workday Inc', 'Snowflake Inc', 'Palantir Technologies',
    'Austin Community Bank', 'Dallas Technology Solutions', 'Houston Energy Corporation',
    'San Antonio Insurance Group', 'Fort Worth Manufacturing', 'El Paso Logistics',
    'Arlington Software Solutions', 'Plano Financial Services', 'Irving Tech Consulting',
    'Garland Medical Systems', 'Lubbock Agricultural Corp', 'Amarillo Wind Energy'
]

JOB_TITLES = [
    'Software Engineer', 'Product Manager', 'Data Scientist', 'Marketing Manager',
    'Sales Director', 'Business Analyst', 'Project Manager', 'UX Designer',
    'DevOps Engineer', 'Financial Analyst', 'Operations Manager', 'HR Director',
    'Customer Success Manager', 'Technical Writer', 'Quality Assurance Engineer',
    'Account Executive', 'Research Scientist', 'Brand Manager', 'IT Administrator',
    'Content Manager', 'Digital Marketing Specialist', 'Business Development Manager',
    'Systems Administrator', 'Database Administrator', 'Network Engineer',
    'Security Analyst', 'Mobile Developer', 'Frontend Developer', 'Backend Developer',
    'Full Stack Developer', 'Machine Learning Engineer', 'Cloud Architect'
]

TRAFFIC_SOURCES = [
    'Google Search', 'Direct Visit', 'Facebook', 'LinkedIn', 'Twitter',
    'YouTube', 'Instagram', 'Google Ads', 'Facebook Ads', 'LinkedIn Ads',
    'Email Campaign', 'Referral Link', 'Bing Search', 'Yahoo Search',
    'Reddit', 'Pinterest', 'TikTok', 'Snapchat', 'WhatsApp', 'Telegram'
]

PAGES = [
    '/', '/about', '/contact', '/services', '/products', '/pricing', '/features',
    '/blog', '/news', '/careers', '/support', '/help', '/faq', '/terms',
    '/privacy', '/login', '/signup', '/dashboard', '/profile', '/settings',
    '/search', '/categories', '/reviews', '/testimonials', '/case-studies',
    '/downloads', '/documentation', '/api', '/developers', '/partners'
]

CITIES = [
    'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX', 'Phoenix, AZ',
    'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA', 'Dallas, TX', 'San Jose, CA',
    'Austin, TX', 'Jacksonville, FL', 'Fort Worth, TX', 'Columbus, OH', 'Charlotte, NC',
    'San Francisco, CA', 'Indianapolis, IN', 'Seattle, WA', 'Denver, CO', 'Washington, DC',
    'Boston, MA', 'El Paso, TX', 'Nashville, TN', 'Detroit, MI', 'Oklahoma City, OK',
    'Portland, OR', 'Las Vegas, NV', 'Memphis, TN', 'Louisville, KY', 'Baltimore, MD',
    'Milwaukee, WI', 'Albuquerque, NM', 'Tucson, AZ', 'Fresno, CA', 'Sacramento, CA',
    'Mesa, AZ', 'Kansas City, MO', 'Atlanta, GA', 'Long Beach, CA', 'Colorado Springs, CO',
    'Raleigh, NC', 'Miami, FL', 'Virginia Beach, VA', 'Omaha, NE', 'Oakland, CA',
    'Minneapolis, MN', 'Tulsa, OK', 'Arlington, TX', 'Tampa, FL', 'New Orleans, LA'
]

def generate_realistic_visitor():
    """Generate a realistic visitor profile"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    company = random.choice(COMPANIES)
    job_title = random.choice(JOB_TITLES)
    location = random.choice(CITIES)
    
    # Generate realistic email
    email_domain = company.lower().replace(' ', '').replace('inc', '').replace('corporation', '').replace('llc', '').replace('technologies', 'tech')[:15] + '.com'
    email = f"{first_name.lower()}.{last_name.lower()}@{email_domain}"
    
    # Generate phone number
    area_codes = ['212', '213', '312', '713', '602', '215', '210', '619', '214', '408', '512', '904', '817', '614', '704', '415', '317', '206', '303', '202']
    phone = f"({random.choice(area_codes)}) {random.randint(100,999)}-{random.randint(1000,9999)}"
    
    # Generate IP address
    ip = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    
    # Generate browsing behavior
    pages_visited = random.sample(PAGES, random.randint(1, 5))
    current_page = random.choice(pages_visited)
    time_on_page = random.randint(15, 600)
    total_time = sum([random.randint(30, 300) for _ in pages_visited])
    
    # Generate interest level based on time spent
    if total_time > 400:
        interest_level = "High Interest"
    elif total_time > 150:
        interest_level = "Medium Interest"
    else:
        interest_level = "Low Interest"
    
    return {
        'name': f"{first_name} {last_name}",
        'email': email,
        'phone': phone,
        'location': location,
        'company': company,
        'job_title': job_title,
        'age': random.randint(22, 65),
        'ip': ip,
        'current_page': current_page,
        'time_on_page': time_on_page,
        'pages_visited': pages_visited,
        'total_time': total_time,
        'source': random.choice(TRAFFIC_SOURCES),
        'interest_level': interest_level
    }

def get_website_pattern(website):
    """Get traffic pattern for a website"""
    domain = website.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0].lower()
    
    for pattern_domain, pattern in WEBSITE_PATTERNS.items():
        if pattern_domain in domain or domain in pattern_domain:
            return pattern
    
    return WEBSITE_PATTERNS['default']

def init_db():
    """Initialize the database"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            visitor_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investigation_id INTEGER,
            name TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            company TEXT,
            job_title TEXT,
            age INTEGER,
            ip_address TEXT,
            current_page TEXT,
            time_on_page INTEGER,
            pages_visited TEXT,
            total_time INTEGER,
            source TEXT,
            interest_level TEXT,
            FOREIGN KEY (investigation_id) REFERENCES investigations (id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/investigate', methods=['POST'])
def investigate_website():
    """Investigate a website for visitor data"""
    data = request.get_json()
    website = data.get('website', '').strip()
    
    if not website:
        return jsonify({'error': 'Website URL is required'}), 400
    
    # Clean up website URL
    if not website.startswith(('http://', 'https://')):
        website = 'https://' + website
    
    # Initialize database
    init_db()
    
    # Get website traffic pattern
    pattern = get_website_pattern(website)
    visitor_count = random.randint(pattern['min_visitors'], pattern['max_visitors'])
    
    # Generate realistic visitors
    visitors_data = []
    for _ in range(visitor_count):
        visitor = generate_realistic_visitor()
        visitors_data.append(visitor)
    
    # Create investigation record
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO investigations (website, visitor_count, status)
        VALUES (?, ?, ?)
    ''', (website, visitor_count, 'completed'))
    
    investigation_id = cursor.lastrowid
    
    # Store visitors in database
    for visitor in visitors_data:
        cursor.execute('''
            INSERT INTO visitors (
                investigation_id, name, email, phone, location, company, 
                job_title, age, ip_address, current_page, time_on_page,
                pages_visited, total_time, source, interest_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            investigation_id, visitor['name'], visitor['email'],
            visitor['phone'], visitor['location'], visitor['company'],
            visitor['job_title'], visitor['age'], visitor['ip'],
            visitor['current_page'], visitor['time_on_page'],
            json.dumps(visitor['pages_visited']), visitor['total_time'],
            visitor['source'], visitor['interest_level']
        ))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'website': website,
        'investigation_id': investigation_id,
        'visitor_count': visitor_count,
        'traffic_level': pattern['traffic_level'],
        'visitors': visitors_data
    })

@app.route('/history')
def get_history():
    """Get investigation history"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, website, timestamp, visitor_count, status
        FROM investigations
        ORDER BY timestamp DESC
        LIMIT 20
    ''')
    
    investigations = []
    for row in cursor.fetchall():
        investigations.append({
            'id': row[0],
            'website': row[1],
            'timestamp': row[2],
            'visitor_count': row[3],
            'status': row[4]
        })
    
    conn.close()
    return jsonify(investigations)

@app.route('/investigation/<int:investigation_id>')
def get_investigation_details(investigation_id):
    """Get detailed investigation results"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Get investigation info
    cursor.execute('SELECT * FROM investigations WHERE id = ?', (investigation_id,))
    investigation = cursor.fetchone()
    
    if not investigation:
        return jsonify({'error': 'Investigation not found'}), 404
    
    # Get visitors
    cursor.execute('SELECT * FROM visitors WHERE investigation_id = ?', (investigation_id,))
    visitors = []
    for row in cursor.fetchall():
        visitors.append({
            'id': row[0],
            'name': row[2],
            'email': row[3],
            'phone': row[4],
            'location': row[5],
            'company': row[6],
            'job_title': row[7],
            'age': row[8],
            'ip_address': row[9],
            'current_page': row[10],
            'time_on_page': row[11],
            'pages_visited': json.loads(row[12]) if row[12] else [],
            'total_time': row[13],
            'source': row[14],
            'interest_level': row[15] if len(row) > 15 else 'Medium Interest'
        })
    
    conn.close()
    
    return jsonify({
        'investigation': {
            'id': investigation[0],
            'website': investigation[1],
            'timestamp': investigation[2],
            'visitor_count': investigation[3],
            'status': investigation[4]
        },
        'visitors': visitors
    })

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)





