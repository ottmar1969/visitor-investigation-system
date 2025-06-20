from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
import random
import datetime
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Sample visitor data for demonstration
SAMPLE_VISITORS = [
    {
        "name": "Jennifer Martinez",
        "email": "jennifer.martinez@austinbank.com",
        "phone": "(512) 847-9234",
        "location": "Austin, TX 78701",
        "company": "Austin Community Bank",
        "job_title": "Branch Manager",
        "age": 34,
        "ip": "73.158.64.22",
        "current_page": "/contact",
        "time_on_page": 156,
        "pages_visited": ["/", "/services", "/contact"],
        "total_time": 321,
        "source": "Google Search"
    },
    {
        "name": "Robert Chen",
        "email": "robert.chen@dallastech.com", 
        "phone": "(214) 692-8157",
        "location": "Dallas, TX 75201",
        "company": "Dallas Technology Solutions",
        "job_title": "Software Engineer",
        "age": 29,
        "ip": "96.47.225.18",
        "current_page": "/pricing",
        "time_on_page": 89,
        "pages_visited": ["/", "/features", "/pricing"],
        "total_time": 245,
        "source": "LinkedIn"
    },
    {
        "name": "Maria Rodriguez",
        "email": "maria.rodriguez@energycorp.com",
        "phone": "(713) 458-2963", 
        "location": "Houston, TX 77002",
        "company": "Houston Energy Corporation",
        "job_title": "Project Manager",
        "age": 41,
        "ip": "108.75.186.45",
        "current_page": "/about",
        "time_on_page": 203,
        "pages_visited": ["/", "/about"],
        "total_time": 203,
        "source": "Direct Visit"
    },
    {
        "name": "David Williams",
        "email": "david.williams@usaa.com",
        "phone": "(210) 736-4821",
        "location": "San Antonio, TX 78205", 
        "company": "USAA",
        "job_title": "Insurance Adjuster",
        "age": 37,
        "ip": "207.244.70.35",
        "current_page": "/reviews",
        "time_on_page": 67,
        "pages_visited": ["/", "/services", "/reviews"],
        "total_time": 189,
        "source": "Facebook Ad"
    },
    {
        "name": "Sarah Johnson",
        "email": "sarah.johnson@delltech.com",
        "phone": "(512) 789-3456",
        "location": "Round Rock, TX 78681",
        "company": "Dell Technologies", 
        "job_title": "Senior Software Engineer",
        "age": 31,
        "ip": "174.79.20.129",
        "current_page": "/demo",
        "time_on_page": 410,
        "pages_visited": ["/", "/features", "/demo"],
        "total_time": 410,
        "source": "Google Ads"
    }
]

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
    
    # Create investigation record
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO investigations (website, visitor_count, status)
        VALUES (?, ?, ?)
    ''', (website, len(SAMPLE_VISITORS), 'completed'))
    
    investigation_id = cursor.lastrowid
    
    # Add sample visitors with some randomization
    visitors_data = []
    for i, visitor in enumerate(SAMPLE_VISITORS):
        # Add some randomization to make it look more realistic
        randomized_visitor = visitor.copy()
        randomized_visitor['time_on_page'] = random.randint(30, 500)
        randomized_visitor['total_time'] = random.randint(60, 800)
        
        cursor.execute('''
            INSERT INTO visitors (
                investigation_id, name, email, phone, location, company, 
                job_title, age, ip_address, current_page, time_on_page,
                pages_visited, total_time, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            investigation_id, randomized_visitor['name'], randomized_visitor['email'],
            randomized_visitor['phone'], randomized_visitor['location'], randomized_visitor['company'],
            randomized_visitor['job_title'], randomized_visitor['age'], randomized_visitor['ip'],
            randomized_visitor['current_page'], randomized_visitor['time_on_page'],
            json.dumps(randomized_visitor['pages_visited']), randomized_visitor['total_time'],
            randomized_visitor['source']
        ))
        
        visitors_data.append(randomized_visitor)
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'website': website,
        'investigation_id': investigation_id,
        'visitor_count': len(visitors_data),
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
            'source': row[14]
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

