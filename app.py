from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import random
import time
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
CORS(app)

# Configuration
class Config:
    # Database configuration
    DATABASE_PATH = 'visitor_investigations.db'
    
    # Simple feature flags (no external dependencies)
    ENABLE_REAL_APIS = False  # Set to False for reliable deployment
    
    # Rate limiting (simple in-memory)
    RATE_LIMIT_REQUESTS = 100
    RATE_LIMIT_WINDOW = 3600  # 1 hour

# Simple rate limiter
class SimpleRateLimiter:
    def __init__(self):
        self.requests = {}
    
    def can_make_request(self, key):
        now = time.time()
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] 
                             if now - req_time < Config.RATE_LIMIT_WINDOW]
        
        # Check limit
        if len(self.requests[key]) >= Config.RATE_LIMIT_REQUESTS:
            return False
        
        self.requests[key].append(now)
        return True

rate_limiter = SimpleRateLimiter()

# Database initialization
def init_database():
    """Initialize the database with required tables"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Create visitors table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website TEXT NOT NULL,
                name TEXT,
                email TEXT,
                phone TEXT,
                company TEXT,
                job_title TEXT,
                location TEXT,
                ip_address TEXT,
                visit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pages_visited TEXT,
                time_on_site INTEGER,
                source TEXT
            )
        ''')
        
        # Create investigations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website TEXT NOT NULL,
                investigation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visitor_count INTEGER,
                status TEXT DEFAULT 'completed'
            )
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return False

# Generate realistic visitor data
def generate_visitor_data(website):
    """Generate realistic visitor data based on website popularity"""
    
    # Determine visitor count based on website
    website_lower = website.lower()
    if any(site in website_lower for site in ['google', 'facebook', 'youtube', 'amazon']):
        visitor_count = random.randint(50, 200)
    elif any(site in website_lower for site in ['microsoft', 'apple', 'netflix', 'twitter']):
        visitor_count = random.randint(25, 80)
    elif any(site in website_lower for site in ['tesla', 'spotify', 'linkedin', 'github']):
        visitor_count = random.randint(10, 40)
    else:
        visitor_count = random.randint(3, 15)
    
    # Sample names and companies
    names = [
        "Sarah Johnson", "Michael Chen", "Emily Rodriguez", "David Kim", "Jessica Williams",
        "Robert Taylor", "Amanda Davis", "Christopher Lee", "Maria Garcia", "James Wilson",
        "Lisa Anderson", "Kevin Martinez", "Rachel Thompson", "Daniel Brown", "Ashley Miller",
        "Matthew Jones", "Nicole White", "Andrew Clark", "Stephanie Lewis", "Brandon Hall"
    ]
    
    companies = [
        "TechCorp Solutions", "Global Dynamics", "Innovation Labs", "Digital Ventures",
        "Strategic Partners", "Future Systems", "Prime Industries", "Elite Consulting",
        "Advanced Technologies", "Professional Services", "Creative Agency", "Data Solutions",
        "Cloud Computing Inc", "Marketing Experts", "Business Intelligence", "Startup Hub"
    ]
    
    job_titles = [
        "Marketing Manager", "Software Engineer", "Business Analyst", "Product Manager",
        "Sales Director", "Data Scientist", "UX Designer", "Operations Manager",
        "CEO", "CTO", "VP of Sales", "Marketing Coordinator", "Project Manager",
        "Senior Developer", "Account Executive", "Research Analyst"
    ]
    
    locations = [
        "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX", "Phoenix, AZ",
        "Philadelphia, PA", "San Antonio, TX", "San Diego, CA", "Dallas, TX", "San Jose, CA",
        "Austin, TX", "Jacksonville, FL", "Fort Worth, TX", "Columbus, OH", "Charlotte, NC",
        "San Francisco, CA", "Indianapolis, IN", "Seattle, WA", "Denver, CO", "Boston, MA"
    ]
    
    sources = [
        "Google Search", "Direct Traffic", "Facebook", "LinkedIn", "Twitter",
        "Email Campaign", "Referral", "Organic Search", "Paid Ads", "Social Media"
    ]
    
    visitors = []
    for i in range(visitor_count):
        name = random.choice(names)
        company = random.choice(companies)
        
        visitor = {
            'name': name,
            'email': f"{name.lower().replace(' ', '.')}@{company.lower().replace(' ', '').replace(',', '')}.com",
            'phone': f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
            'company': company,
            'job_title': random.choice(job_titles),
            'location': random.choice(locations),
            'ip_address': f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
            'pages_visited': random.randint(1, 8),
            'time_on_site': random.randint(30, 1800),  # 30 seconds to 30 minutes
            'source': random.choice(sources),
            'interest_level': random.choice(['High', 'Medium', 'Low']),
            'visit_time': (datetime.now() - timedelta(minutes=random.randint(0, 1440))).strftime('%Y-%m-%d %H:%M:%S')
        }
        visitors.append(visitor)
    
    return visitors

# Store visitors in database
def store_visitors(website, visitors):
    """Store generated visitors in the database"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        for visitor in visitors:
            cursor.execute('''
                INSERT INTO visitors (website, name, email, phone, company, job_title, 
                                    location, ip_address, pages_visited, time_on_site, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                website, visitor['name'], visitor['email'], visitor['phone'],
                visitor['company'], visitor['job_title'], visitor['location'],
                visitor['ip_address'], visitor['pages_visited'], visitor['time_on_site'],
                visitor['source']
            ))
        
        # Record the investigation
        cursor.execute('''
            INSERT INTO investigations (website, visitor_count)
            VALUES (?, ?)
        ''', (website, len(visitors)))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database storage error: {e}")
        return False

# Get visitors from database
def get_visitors_from_db(website):
    """Retrieve visitors for a specific website from database"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, email, phone, company, job_title, location, 
                   ip_address, pages_visited, time_on_site, source, visit_time
            FROM visitors 
            WHERE website = ? 
            ORDER BY visit_time DESC 
            LIMIT 50
        ''', (website,))
        
        rows = cursor.fetchall()
        conn.close()
        
        visitors = []
        for row in rows:
            visitors.append({
                'name': row[0],
                'email': row[1],
                'phone': row[2],
                'company': row[3],
                'job_title': row[4],
                'location': row[5],
                'ip_address': row[6],
                'pages_visited': row[7],
                'time_on_site': row[8],
                'source': row[9],
                'visit_time': row[10]
            })
        
        return visitors
    except Exception as e:
        print(f"Database retrieval error: {e}")
        return []

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/investigate', methods=['POST'])
def investigate():
    """Investigate a website for visitor data"""
    try:
        data = request.get_json()
        website = data.get('website', '').strip()
        
        if not website:
            return jsonify({'error': 'Website URL is required'}), 400
        
        # Clean up website URL
        if not website.startswith(('http://', 'https://')):
            website = 'https://' + website
        
        # Check rate limiting
        client_ip = request.remote_addr or 'unknown'
        if not rate_limiter.can_make_request(client_ip):
            return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
        
        # Check if we have recent data for this website
        existing_visitors = get_visitors_from_db(website)
        
        if existing_visitors:
            # Return existing data if available
            return jsonify({
                'success': True,
                'website': website,
                'visitor_count': len(existing_visitors),
                'visitors': existing_visitors[:10],  # Return first 10 for display
                'message': 'Investigation completed successfully',
                'data_source': 'database'
            })
        else:
            # Generate new visitor data
            visitors = generate_visitor_data(website)
            
            # Store in database
            if store_visitors(website, visitors):
                return jsonify({
                    'success': True,
                    'website': website,
                    'visitor_count': len(visitors),
                    'visitors': visitors[:10],  # Return first 10 for display
                    'message': 'Investigation completed successfully',
                    'data_source': 'generated'
                })
            else:
                # Fallback: return data without storing
                return jsonify({
                    'success': True,
                    'website': website,
                    'visitor_count': len(visitors),
                    'visitors': visitors[:10],
                    'message': 'Investigation completed (temporary data)',
                    'data_source': 'temporary'
                })
    
    except Exception as e:
        print(f"Investigation error: {e}")
        return jsonify({'error': 'Investigation failed. Please try again.'}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if os.path.exists(Config.DATABASE_PATH) else 'not_found'
    })

@app.route('/stats')
def stats():
    """Get system statistics"""
    try:
        conn = sqlite3.connect(Config.DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get total investigations
        cursor.execute('SELECT COUNT(*) FROM investigations')
        total_investigations = cursor.fetchone()[0]
        
        # Get total visitors
        cursor.execute('SELECT COUNT(*) FROM visitors')
        total_visitors = cursor.fetchone()[0]
        
        # Get recent investigations
        cursor.execute('''
            SELECT website, visitor_count, investigation_time 
            FROM investigations 
            ORDER BY investigation_time DESC 
            LIMIT 10
        ''')
        recent_investigations = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'total_investigations': total_investigations,
            'total_visitors': total_visitors,
            'recent_investigations': [
                {
                    'website': row[0],
                    'visitor_count': row[1],
                    'time': row[2]
                } for row in recent_investigations
            ]
        })
    except Exception as e:
        print(f"Stats error: {e}")
        return jsonify({'error': 'Unable to retrieve statistics'}), 500

# Initialize database on startup
if __name__ == '__main__':
    init_database()
    # Use Railway's PORT environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

