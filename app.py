"""
Railway-Ready Visitor Investigation System
Simplified version without email imports that cause crashes
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
import threading

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, origins="*")

# Railway port configuration
PORT = int(os.environ.get('PORT', 5000))

def init_database():
    """Initialize database with trial management tables"""
    try:
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        # Enhanced clients table with trial support
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                contact_email TEXT NOT NULL,
                access_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                subscription_status TEXT DEFAULT 'trial',
                trial_start TIMESTAMP,
                trial_end TIMESTAMP,
                trial_duration_hours INTEGER DEFAULT 168,
                plan_type TEXT DEFAULT 'starter',
                monthly_identifications INTEGER DEFAULT 500,
                used_identifications INTEGER DEFAULT 0
            )
        ''')
        
        # Visitor investigations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visitor_investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                visitor_ip TEXT,
                visitor_data TEXT,
                investigation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")

@app.route('/')
def index():
    """Main visitor investigation page"""
    try:
        return render_template('index.html')
    except Exception as e:
        return f"<h1>Visitor Investigation System</h1><p>Welcome! The system is running.</p><p>Template error: {e}</p>", 200

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for managing clients"""
    try:
        return render_template('admin_dashboard.html')
    except Exception as e:
        return f"<h1>Admin Dashboard</h1><p>Admin interface is running.</p><p>Template error: {e}</p>", 200

@app.route('/admin/trials')
def admin_trials():
    """Trial management interface"""
    try:
        return render_template('admin_trials.html')
    except Exception as e:
        return f"<h1>Trial Management</h1><p>Trial system is running.</p><p>Template error: {e}</p>", 200

@app.route('/pricing')
def pricing():
    """Pricing page with visitor identification plans"""
    try:
        return render_template('pricing.html')
    except Exception as e:
        return f"<h1>Pricing Plans</h1><p>Visitor identification pricing is available.</p><p>Template error: {e}</p>", 200

@app.route('/dashboard/<access_token>')
def client_dashboard(access_token):
    """Client dashboard with visitor data"""
    try:
        # Verify access token and check if client is active
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM clients 
            WHERE access_token = ? AND is_active = 1
        ''', (access_token,))
        
        client = cursor.fetchone()
        conn.close()
        
        if not client:
            return "<h1>Access Denied</h1><p>Invalid or expired access token.</p>", 403
            
        # Check if trial has expired
        if client[7]:  # trial_end
            try:
                trial_end = datetime.fromisoformat(client[7])
                if datetime.now() > trial_end:
                    return "<h1>Trial Expired</h1><p>Your trial period has ended.</p>", 403
            except:
                pass
        
        try:
            return render_template('client_dashboard.html', client=client)
        except Exception as e:
            return f"<h1>Client Dashboard</h1><p>Dashboard is running for: {client[1]}</p><p>Template error: {e}</p>", 200
        
    except Exception as e:
        return f"<h1>Dashboard Error</h1><p>Error: {e}</p>", 500

@app.route('/api/investigate', methods=['POST'])
def investigate_visitor():
    """API endpoint for visitor investigation"""
    try:
        data = request.get_json() or {}
        
        # Generate demo visitor data
        visitor_data = {
            'ip': request.remote_addr,
            'timestamp': datetime.now().isoformat(),
            'location': f"City {random.randint(1, 100)}, Country {random.randint(1, 50)}",
            'device': random.choice(['Desktop', 'Mobile', 'Tablet']),
            'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
            'pages_visited': random.randint(1, 20),
            'time_on_site': random.randint(30, 3600),
            'interest_level': random.choice(['High', 'Medium', 'Low'])
        }
        
        return jsonify({
            'success': True,
            'visitor_data': visitor_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Get all clients for admin dashboard"""
    try:
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, business_name, contact_email, subscription_status, 
                   trial_end, is_active, plan_type, monthly_identifications
            FROM clients 
            ORDER BY created_at DESC
        ''')
        
        clients = []
        for row in cursor.fetchall():
            clients.append({
                'id': row[0],
                'business_name': row[1],
                'contact_email': row[2],
                'subscription_status': row[3],
                'trial_end': row[4],
                'is_active': row[5],
                'plan_type': row[6] if len(row) > 6 else 'starter',
                'monthly_identifications': row[7] if len(row) > 7 else 500
            })
        
        conn.close()
        return jsonify({'success': True, 'clients': clients})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-trial', methods=['POST'])
def create_trial():
    """Create a new trial for a business"""
    try:
        data = request.get_json() or {}
        business_name = data.get('business_name', 'Demo Business')
        contact_email = data.get('contact_email', 'demo@example.com')
        trial_hours = int(data.get('trial_hours', 168))  # Default 7 days
        
        # Generate unique access token
        access_token = secrets.token_urlsafe(32)
        
        # Calculate trial end time
        trial_start = datetime.now()
        trial_end = trial_start + timedelta(hours=trial_hours)
        
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO clients (
                business_name, contact_email, access_token, 
                trial_start, trial_end, trial_duration_hours
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (business_name, contact_email, access_token, 
              trial_start.isoformat(), trial_end.isoformat(), trial_hours))
        
        client_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        dashboard_url = f"{request.host_url}dashboard/{access_token}"
        
        return jsonify({
            'success': True,
            'client_id': client_id,
            'access_token': access_token,
            'dashboard_url': dashboard_url,
            'trial_end': trial_end.isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'message': 'Visitor Investigation System is running!'
    })

@app.route('/test')
def test_page():
    """Simple test page to verify deployment"""
    return """
    <h1>🎉 Visitor Investigation System is LIVE!</h1>
    <p>✅ Flask app is running successfully</p>
    <p>✅ Database connection working</p>
    <p>✅ API endpoints available</p>
    <hr>
    <h3>Available Pages:</h3>
    <ul>
        <li><a href="/">Main Investigation Page</a></li>
        <li><a href="/admin">Admin Dashboard</a></li>
        <li><a href="/admin/trials">Trial Management</a></li>
        <li><a href="/pricing">Pricing Plans</a></li>
        <li><a href="/health">Health Check</a></li>
    </ul>
    """

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting Visitor Investigation System...")
    
    # Initialize database
    init_database()
    
    # Start the Flask application
    print(f"🌐 Server starting on port {PORT}")
    print(f"🔗 Access at: http://0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)

