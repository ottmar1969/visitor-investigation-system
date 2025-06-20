"""
Railway-Ready Visitor Investigation System
Fixed for deployment with proper port binding and error handling
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
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import requests
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import threading
import schedule

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app, origins="*")

# Railway port configuration
PORT = int(os.environ.get('PORT', 5000))

# Email configuration (configure with your SMTP settings)
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'your-email@gmail.com',
    'password': 'your-app-password',
    'from_name': 'Visitor Investigation System'
}

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
                used_identifications INTEGER DEFAULT 0,
                last_payment TIMESTAMP,
                payment_method TEXT,
                stripe_customer_id TEXT,
                paypal_subscription_id TEXT,
                country_restrictions TEXT,
                allowed_countries TEXT,
                blocked_countries TEXT,
                max_concurrent_sessions INTEGER DEFAULT 1,
                current_sessions INTEGER DEFAULT 0
            )
        ''')
        
        # Users table for client dashboard access
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'viewer',
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                country_access TEXT,
                session_limit INTEGER DEFAULT 1,
                access_expires TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
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
        
        # Payment transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                amount DECIMAL(10,2),
                currency TEXT DEFAULT 'USD',
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
        return f"Template error: {e}", 500

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard for managing clients"""
    try:
        return render_template('admin_dashboard.html')
    except Exception as e:
        return f"Template error: {e}", 500

@app.route('/admin/trials')
def admin_trials():
    """Trial management interface"""
    try:
        return render_template('admin_trials.html')
    except Exception as e:
        return f"Template error: {e}", 500

@app.route('/pricing')
def pricing():
    """Pricing page with visitor identification plans"""
    try:
        return render_template('pricing.html')
    except Exception as e:
        return f"Template error: {e}", 500

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
            return render_template('access_denied.html'), 403
            
        # Check if trial has expired
        if client[6]:  # trial_end
            trial_end = datetime.fromisoformat(client[6])
            if datetime.now() > trial_end:
                return render_template('access_denied.html'), 403
        
        return render_template('client_dashboard.html', client=client)
        
    except Exception as e:
        return f"Dashboard error: {e}", 500

@app.route('/api/investigate', methods=['POST'])
def investigate_visitor():
    """API endpoint for visitor investigation"""
    try:
        data = request.get_json()
        
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
                'plan_type': row[6],
                'monthly_identifications': row[7]
            })
        
        conn.close()
        return jsonify({'success': True, 'clients': clients})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create-trial', methods=['POST'])
def create_trial():
    """Create a new trial for a business"""
    try:
        data = request.get_json()
        business_name = data.get('business_name')
        contact_email = data.get('contact_email')
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
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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
    app.run(host='0.0.0.0', port=PORT, debug=False)

