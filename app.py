from flask import Flask, render_template, request, jsonify
import sqlite3
import random
import time
import os
import requests
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Configuration
class Config:
    # API Keys (set via environment variables)
    IPGEOLOCATION_API_KEY = os.getenv('IPGEOLOCATION_API_KEY')
    VISITOR_QUEUE_API_KEY = os.getenv('VISITOR_QUEUE_API_KEY')
    SNITCHER_API_KEY = os.getenv('SNITCHER_API_KEY')
    
    # Feature Flags
    ENABLE_REAL_APIS = os.getenv('ENABLE_REAL_APIS', 'false').lower() == 'true'
    ENABLE_PAID_APIS = os.getenv('ENABLE_PAID_APIS', 'false').lower() == 'true'
    
    # Subscription Tier
    SUBSCRIPTION_TIER = os.getenv('SUBSCRIPTION_TIER', 'free')  # free, basic, pro, enterprise

# Rate Limit Manager
class RateLimitManager:
    def __init__(self):
        self.limits = {
            'ip_api': {'requests': 0, 'reset_time': time.time() + 3600, 'limit': 45},
            'ipgeolocation': {'requests': 0, 'reset_time': time.time() + 86400, 'limit': 1000}
        }
    
    def can_make_request(self, api_name):
        limit_info = self.limits.get(api_name)
        if not limit_info:
            return True
        
        # Reset counter if time window passed
        if time.time() > limit_info['reset_time']:
            limit_info['requests'] = 0
            if api_name == 'ip_api':
                limit_info['reset_time'] = time.time() + 3600  # 1 hour
            else:
                limit_info['reset_time'] = time.time() + 86400  # 1 day
        
        return limit_info['requests'] < limit_info['limit']
    
    def record_request(self, api_name):
        if api_name in self.limits:
            self.limits[api_name]['requests'] += 1

rate_limiter = RateLimitManager()

# API Integration Functions
def get_ip_geolocation(ip_address):
    """Get geolocation data using free APIs with fallback"""
    
    if not Config.ENABLE_REAL_APIS:
        return generate_location_data(ip_address)
    
    # Try IP-API.com first (free, non-commercial)
    if rate_limiter.can_make_request('ip_api'):
        try:
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    rate_limiter.record_request('ip_api')
                    return {
                        'country': data.get('country', 'Unknown'),
                        'region': data.get('regionName', 'Unknown'),
                        'city': data.get('city', 'Unknown'),
                        'latitude': data.get('lat', 0),
                        'longitude': data.get('lon', 0),
                        'timezone': data.get('timezone', 'Unknown'),
                        'isp': data.get('isp', 'Unknown'),
                        'source': 'ip-api.com'
                    }
        except Exception as e:
            print(f"IP-API error: {e}")
    
    # Fallback to IPGeolocation.io (requires API key)
    if Config.IPGEOLOCATION_API_KEY and rate_limiter.can_make_request('ipgeolocation'):
        try:
            url = f"https://api.ipgeolocation.io/ipgeo?apiKey={Config.IPGEOLOCATION_API_KEY}&ip={ip_address}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                rate_limiter.record_request('ipgeolocation')
                return {
                    'country': data.get('country_name', 'Unknown'),
                    'region': data.get('state_prov', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'latitude': float(data.get('latitude', 0)),
                    'longitude': float(data.get('longitude', 0)),
                    'timezone': data.get('time_zone', {}).get('name', 'Unknown'),
                    'isp': data.get('isp', 'Unknown'),
                    'source': 'ipgeolocation.io'
                }
        except Exception as e:
            print(f"IPGeolocation error: {e}")
    
    # Final fallback: generate realistic data
    return generate_location_data(ip_address)

def get_visitor_identification(ip_address, domain):
    """Get visitor identification using paid APIs"""
    
    if not Config.ENABLE_PAID_APIS:
        return generate_visitor_profile(domain)
    
    # Try Visitor Queue API (if available)
    if Config.VISITOR_QUEUE_API_KEY:
        try:
            # Note: This is a placeholder - actual API integration would require
            # specific endpoint and authentication method for each service
            visitor_data = call_visitor_queue_api(ip_address, domain)
            if visitor_data:
                return visitor_data
        except Exception as e:
            print(f"Visitor Queue API error: {e}")
    
    # Fallback to generated profile
    return generate_visitor_profile(domain)

def call_visitor_queue_api(ip_address, domain):
    """Placeholder for Visitor Queue API integration"""
    # This would be replaced with actual API call
    # return requests.post('https://api.visitorqueue.com/identify', ...)
    return None

# Data Generation Functions (Fallback)
def generate_location_data(ip_address):
    """Generate realistic location data as fallback"""
    locations = [
        {'country': 'United States', 'region': 'California', 'city': 'San Francisco', 'lat': 37.7749, 'lon': -122.4194},
        {'country': 'United States', 'region': 'New York', 'city': 'New York', 'lat': 40.7128, 'lon': -74.0060},
        {'country': 'United Kingdom', 'region': 'England', 'city': 'London', 'lat': 51.5074, 'lon': -0.1278},
        {'country': 'Germany', 'region': 'Bavaria', 'city': 'Munich', 'lat': 48.1351, 'lon': 11.5820},
        {'country': 'Canada', 'region': 'Ontario', 'city': 'Toronto', 'lat': 43.6532, 'lon': -79.3832},
    ]
    
    location = random.choice(locations)
    return {
        'country': location['country'],
        'region': location['region'],
        'city': location['city'],
        'latitude': location['lat'],
        'longitude': location['lon'],
        'timezone': 'America/New_York',
        'isp': random.choice(['Comcast', 'Verizon', 'AT&T', 'Charter', 'Cox']),
        'source': 'generated'
    }

def generate_visitor_profile(domain):
    """Generate realistic visitor profile based on domain"""
    
    # Determine visitor count based on domain popularity
    domain_lower = domain.lower()
    if any(popular in domain_lower for popular in ['google', 'facebook', 'microsoft', 'amazon', 'apple']):
        visitor_count = random.randint(50, 200)
    elif any(medium in domain_lower for medium in ['tesla', 'netflix', 'spotify', 'github', 'stackoverflow']):
        visitor_count = random.randint(25, 80)
    else:
        visitor_count = random.randint(3, 25)
    
    # Generate visitor profiles
    visitors = []
    for i in range(visitor_count):
        visitor = generate_single_visitor(domain)
        visitors.append(visitor)
    
    return {
        'total_visitors': visitor_count,
        'visitors': visitors,
        'source': 'generated'
    }

def generate_single_visitor(domain):
    """Generate a single realistic visitor profile"""
    
    first_names = ['James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 'William', 'Elizabeth']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    
    companies = ['TechCorp', 'InnovateLLC', 'GlobalSystems', 'DataDynamics', 'CloudFirst', 'NextGenSoft', 'DigitalEdge', 'SmartSolutions']
    job_titles = ['Software Engineer', 'Marketing Manager', 'Sales Director', 'Product Manager', 'Data Analyst', 'CEO', 'CTO', 'VP Sales']
    
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    company = random.choice(companies)
    
    return {
        'name': f"{first_name} {last_name}",
        'email': f"{first_name.lower()}.{last_name.lower()}@{company.lower()}.com",
        'phone': f"+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}",
        'company': company,
        'job_title': random.choice(job_titles),
        'location': f"{random.choice(['New York', 'San Francisco', 'Los Angeles', 'Chicago', 'Boston'])}, {random.choice(['NY', 'CA', 'IL', 'MA'])}",
        'pages_visited': random.randint(1, 8),
        'time_on_site': f"{random.randint(1, 15)} minutes",
        'traffic_source': random.choice(['Google Search', 'Direct', 'LinkedIn', 'Twitter', 'Email Campaign']),
        'interest_level': random.choice(['High', 'Medium', 'Low']),
        'last_visit': (datetime.now() - timedelta(minutes=random.randint(1, 1440))).strftime('%Y-%m-%d %H:%M:%S')
    }

# Database Functions
def init_db():
    """Initialize the database"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            visitor_count INTEGER,
            investigation_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            api_source TEXT,
            subscription_tier TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_name TEXT NOT NULL,
            requests_made INTEGER DEFAULT 0,
            successful_requests INTEGER DEFAULT 0,
            date DATE DEFAULT CURRENT_DATE,
            cost REAL DEFAULT 0.0
        )
    ''')
    
    conn.commit()
    conn.close()

def save_investigation(domain, visitor_count, investigation_data, api_source):
    """Save investigation results to database"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO investigations (domain, visitor_count, investigation_data, api_source, subscription_tier)
        VALUES (?, ?, ?, ?, ?)
    ''', (domain, visitor_count, json.dumps(investigation_data), api_source, Config.SUBSCRIPTION_TIER))
    
    conn.commit()
    conn.close()

def get_investigation_history():
    """Get recent investigation history"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT domain, visitor_count, created_at, api_source, subscription_tier
        FROM investigations
        ORDER BY created_at DESC
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            'domain': row[0],
            'visitor_count': row[1],
            'created_at': row[2],
            'api_source': row[3],
            'subscription_tier': row[4]
        }
        for row in results
    ]

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/investigate', methods=['POST'])
def investigate():
    domain = request.form.get('domain', '').strip()
    
    if not domain:
        return jsonify({'error': 'Please enter a domain name'})
    
    # Remove protocol if present
    domain = domain.replace('http://', '').replace('https://', '').replace('www.', '')
    
    try:
        # Get visitor IP (in real implementation, this would be the actual visitor's IP)
        visitor_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
        
        # Get geolocation data
        location_data = get_ip_geolocation(visitor_ip)
        
        # Get visitor identification data
        visitor_data = get_visitor_identification(visitor_ip, domain)
        
        # Combine data
        investigation_result = {
            'domain': domain,
            'total_visitors': visitor_data.get('total_visitors', 1),
            'location_data': location_data,
            'visitors': visitor_data.get('visitors', []),
            'api_sources': {
                'location': location_data.get('source', 'generated'),
                'visitors': visitor_data.get('source', 'generated')
            },
            'subscription_tier': Config.SUBSCRIPTION_TIER,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to database
        save_investigation(
            domain, 
            investigation_result['total_visitors'], 
            investigation_result,
            f"{location_data.get('source', 'generated')},{visitor_data.get('source', 'generated')}"
        )
        
        return jsonify(investigation_result)
        
    except Exception as e:
        return jsonify({'error': f'Investigation failed: {str(e)}'})

@app.route('/api/config')
def get_config():
    """Get current API configuration and limits"""
    return jsonify({
        'subscription_tier': Config.SUBSCRIPTION_TIER,
        'apis_enabled': {
            'real_apis': Config.ENABLE_REAL_APIS,
            'paid_apis': Config.ENABLE_PAID_APIS,
            'ipgeolocation': bool(Config.IPGEOLOCATION_API_KEY),
            'visitor_queue': bool(Config.VISITOR_QUEUE_API_KEY)
        },
        'rate_limits': {
            'ip_api': rate_limiter.limits['ip_api'],
            'ipgeolocation': rate_limiter.limits['ipgeolocation']
        }
    })

@app.route('/api/history')
def get_history():
    """Get investigation history"""
    return jsonify(get_investigation_history())

@app.route('/admin')
def admin():
    """Admin dashboard for API management"""
    return render_template('admin.html')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)

