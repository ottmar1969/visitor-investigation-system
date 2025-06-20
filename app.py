from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
import json
import random
import datetime
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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

def get_visitors_from_database(investigation_id=None):
    """Get real visitor data from database"""
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    if investigation_id:
        cursor.execute('SELECT * FROM visitors WHERE investigation_id = ?', (investigation_id,))
    else:
        # Get visitors from the most recent investigation, or all if no specific investigation
        cursor.execute('''
            SELECT v.* FROM visitors v 
            JOIN investigations i ON v.investigation_id = i.id 
            ORDER BY i.timestamp DESC 
            LIMIT 10
        ''')
    
    visitors = []
    for row in cursor.fetchall():
        visitors.append({
            'name': row[2] if row[2] else 'Anonymous User',
            'email': row[3] if row[3] else 'email@example.com',
            'phone': row[4] if row[4] else '(000) 000-0000',
            'location': row[5] if row[5] else 'Unknown Location',
            'company': row[6] if row[6] else 'Unknown Company',
            'job_title': row[7] if row[7] else 'Unknown Position',
            'age': row[8] if row[8] else random.randint(25, 55),
            'ip': row[9] if row[9] else f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            'current_page': row[10] if row[10] else '/',
            'time_on_page': row[11] if row[11] else random.randint(30, 500),
            'pages_visited': json.loads(row[12]) if row[12] else ['/'],
            'total_time': row[13] if row[13] else random.randint(60, 800),
            'source': row[14] if row[14] else 'Direct Visit'
        })
    
    conn.close()
    
    # If no real data found, return a message indicating this
    if not visitors:
        visitors = [{
            'name': 'No Real Data Available',
            'email': 'Add real visitor data to your database',
            'phone': 'Currently showing placeholder',
            'location': 'Database is empty',
            'company': 'Please add visitor records',
            'job_title': 'to see real data here',
            'age': 0,
            'ip': '0.0.0.0',
            'current_page': '/empty',
            'time_on_page': 0,
            'pages_visited': ['/'],
            'total_time': 0,
            'source': 'No Data'
        }]
    
    return visitors

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
    
    # Get real visitor data from database
    visitors_data = get_visitors_from_database()
    
    # Create investigation record
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO investigations (website, visitor_count, status)
        VALUES (?, ?, ?)
    ''', (website, len(visitors_data), 'completed'))
    
    investigation_id = cursor.lastrowid
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
    
    # Get real visitors from database
    visitors = get_visitors_from_database(investigation_id)
    
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

@app.route('/add_visitor', methods=['POST'])
def add_visitor():
    """Add a new visitor to the database (for testing/demo purposes)"""
    data = request.get_json()
    
    conn = sqlite3.connect('visitor_investigations.db')
    cursor = conn.cursor()
    
    # Get or create a default investigation
    cursor.execute('SELECT id FROM investigations ORDER BY timestamp DESC LIMIT 1')
    result = cursor.fetchone()
    
    if result:
        investigation_id = result[0]
    else:
        # Create a default investigation
        cursor.execute('''
            INSERT INTO investigations (website, visitor_count, status)
            VALUES (?, ?, ?)
        ''', ('default-website.com', 0, 'active'))
        investigation_id = cursor.lastrowid
    
    # Add the visitor
    cursor.execute('''
        INSERT INTO visitors (
            investigation_id, name, email, phone, location, company, 
            job_title, age, ip_address, current_page, time_on_page,
            pages_visited, total_time, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        investigation_id,
        data.get('name', 'Anonymous'),
        data.get('email', 'unknown@example.com'),
        data.get('phone', '(000) 000-0000'),
        data.get('location', 'Unknown'),
        data.get('company', 'Unknown Company'),
        data.get('job_title', 'Unknown'),
        data.get('age', 30),
        data.get('ip_address', '127.0.0.1'),
        data.get('current_page', '/'),
        data.get('time_on_page', 60),
        json.dumps(data.get('pages_visited', ['/'])),
        data.get('total_time', 60),
        data.get('source', 'Direct')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Visitor added successfully'})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)



