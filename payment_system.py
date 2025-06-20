"""
Enhanced Payment System with Stripe and PayPal Integration
Supports both one-time payments and recurring subscriptions
"""

import stripe
import paypalrestsdk
from flask import Flask, request, jsonify, render_template, redirect, url_for
import json
import sqlite3
from datetime import datetime, timedelta
import uuid
import hmac
import hashlib
import os

# Payment configuration
STRIPE_CONFIG = {
    'publishable_key': 'pk_test_your_stripe_publishable_key',  # Replace with your Stripe publishable key
    'secret_key': 'sk_test_your_stripe_secret_key',  # Replace with your Stripe secret key
    'webhook_secret': 'whsec_your_webhook_secret'  # Replace with your webhook secret
}

PAYPAL_CONFIG = {
    'mode': 'sandbox',  # Change to 'live' for production
    'client_id': 'your_paypal_client_id',  # Replace with your PayPal client ID
    'client_secret': 'your_paypal_client_secret',  # Replace with your PayPal client secret
    'webhook_id': 'your_paypal_webhook_id'  # Replace with your PayPal webhook ID
}

# Initialize payment providers
stripe.api_key = STRIPE_CONFIG['secret_key']

paypalrestsdk.configure({
    'mode': PAYPAL_CONFIG['mode'],
    'client_id': PAYPAL_CONFIG['client_id'],
    'client_secret': PAYPAL_CONFIG['client_secret']
})

def init_payment_database():
    """Initialize payment-related database tables"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    # Payment plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price_monthly DECIMAL(10,2),
            price_yearly DECIMAL(10,2),
            max_users INTEGER DEFAULT 5,
            max_websites INTEGER DEFAULT 1,
            features TEXT,
            stripe_price_id_monthly TEXT,
            stripe_price_id_yearly TEXT,
            paypal_plan_id_monthly TEXT,
            paypal_plan_id_yearly TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Subscriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            payment_provider TEXT NOT NULL,
            provider_subscription_id TEXT,
            status TEXT DEFAULT 'active',
            billing_cycle TEXT DEFAULT 'monthly',
            amount DECIMAL(10,2),
            currency TEXT DEFAULT 'USD',
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            trial_end TIMESTAMP,
            cancel_at_period_end BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (client_id),
            FOREIGN KEY (plan_id) REFERENCES payment_plans (plan_id)
        )
    ''')
    
    # Payment transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            subscription_id TEXT,
            payment_provider TEXT NOT NULL,
            provider_transaction_id TEXT,
            amount DECIMAL(10,2) NOT NULL,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'pending',
            payment_method TEXT,
            description TEXT,
            invoice_url TEXT,
            receipt_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (client_id),
            FOREIGN KEY (subscription_id) REFERENCES subscriptions (subscription_id)
        )
    ''')
    
    # Payment methods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            payment_provider TEXT NOT NULL,
            provider_method_id TEXT,
            type TEXT,
            last_four TEXT,
            brand TEXT,
            exp_month INTEGER,
            exp_year INTEGER,
            is_default BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    # Billing addresses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            address_id TEXT UNIQUE NOT NULL,
            client_id TEXT NOT NULL,
            name TEXT,
            company TEXT,
            line1 TEXT,
            line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT,
            phone TEXT,
            is_default BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients (client_id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_default_payment_plans():
    """Create default payment plans"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    plans = [
        {
            'plan_id': 'basic',
            'name': 'Basic Plan',
            'description': 'Perfect for small businesses',
            'price_monthly': 29.99,
            'price_yearly': 299.99,
            'max_users': 5,
            'max_websites': 1,
            'features': json.dumps([
                'Up to 5 users',
                '1 website tracking',
                'Basic visitor analytics',
                'Email support',
                'CSV export'
            ])
        },
        {
            'plan_id': 'professional',
            'name': 'Professional Plan',
            'description': 'For growing businesses',
            'price_monthly': 79.99,
            'price_yearly': 799.99,
            'max_users': 15,
            'max_websites': 5,
            'features': json.dumps([
                'Up to 15 users',
                '5 websites tracking',
                'Advanced analytics',
                'Priority support',
                'Excel & CSV export',
                'API access',
                'Custom reports'
            ])
        },
        {
            'plan_id': 'enterprise',
            'name': 'Enterprise Plan',
            'description': 'For large organizations',
            'price_monthly': 199.99,
            'price_yearly': 1999.99,
            'max_users': 50,
            'max_websites': 25,
            'features': json.dumps([
                'Up to 50 users',
                '25 websites tracking',
                'Enterprise analytics',
                'Dedicated support',
                'All export formats',
                'Full API access',
                'Custom integrations',
                'White-label options'
            ])
        }
    ]
    
    for plan in plans:
        cursor.execute('''
            INSERT OR REPLACE INTO payment_plans 
            (plan_id, name, description, price_monthly, price_yearly, max_users, max_websites, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (plan['plan_id'], plan['name'], plan['description'], plan['price_monthly'],
              plan['price_yearly'], plan['max_users'], plan['max_websites'], plan['features']))
    
    conn.commit()
    conn.close()

def create_stripe_subscription(client_id, plan_id, billing_cycle, payment_method_id, billing_address=None):
    """Create a Stripe subscription"""
    try:
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        # Get plan details
        cursor.execute('SELECT * FROM payment_plans WHERE plan_id = ?', (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            return {'success': False, 'error': 'Plan not found'}
        
        # Get client details
        cursor.execute('SELECT * FROM clients WHERE client_id = ?', (client_id,))
        client = cursor.fetchone()
        if not client:
            return {'success': False, 'error': 'Client not found'}
        
        # Create or retrieve Stripe customer
        customer = stripe.Customer.create(
            email=client[3],  # contact_email
            name=client[2],   # business_name
            payment_method=payment_method_id,
            invoice_settings={'default_payment_method': payment_method_id}
        )
        
        # Determine price based on billing cycle
        amount = plan[4] if billing_cycle == 'monthly' else plan[5]  # price_monthly or price_yearly
        
        # Create Stripe subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': plan[2],  # name
                        'description': plan[3]  # description
                    },
                    'unit_amount': int(amount * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month' if billing_cycle == 'monthly' else 'year'
                    }
                }
            }],
            expand=['latest_invoice.payment_intent']
        )
        
        # Save subscription to database
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        cursor.execute('''
            INSERT INTO subscriptions 
            (subscription_id, client_id, plan_id, payment_provider, provider_subscription_id,
             status, billing_cycle, amount, current_period_start, current_period_end)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (subscription_id, client_id, plan_id, 'stripe', subscription.id,
              subscription.status, billing_cycle, amount,
              datetime.fromtimestamp(subscription.current_period_start).isoformat(),
              datetime.fromtimestamp(subscription.current_period_end).isoformat()))
        
        # Update client subscription status
        cursor.execute('''
            UPDATE clients 
            SET subscription_status = 'active', plan_type = ?, account_type = 'full'
            WHERE client_id = ?
        ''', (plan_id, client_id))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'subscription_id': subscription_id,
            'stripe_subscription_id': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def create_paypal_subscription(client_id, plan_id, billing_cycle, return_url, cancel_url):
    """Create a PayPal subscription"""
    try:
        conn = sqlite3.connect('client_management.db')
        cursor = conn.cursor()
        
        # Get plan details
        cursor.execute('SELECT * FROM payment_plans WHERE plan_id = ?', (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            return {'success': False, 'error': 'Plan not found'}
        
        # Determine price based on billing cycle
        amount = plan[4] if billing_cycle == 'monthly' else plan[5]  # price_monthly or price_yearly
        interval = 'MONTH' if billing_cycle == 'monthly' else 'YEAR'
        
        # Create PayPal billing plan
        billing_plan = paypalrestsdk.BillingPlan({
            'name': f"{plan[2]} - {billing_cycle.title()}",
            'description': plan[3],
            'type': 'INFINITE',
            'payment_definitions': [{
                'name': f"{plan[2]} Payment",
                'type': 'REGULAR',
                'frequency': interval,
                'frequency_interval': '1',
                'amount': {
                    'value': str(amount),
                    'currency': 'USD'
                },
                'cycles': '0'  # Infinite
            }],
            'merchant_preferences': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'auto_bill_amount': 'YES',
                'initial_fail_amount_action': 'CONTINUE',
                'max_fail_attempts': '3'
            }
        })
        
        if billing_plan.create():
            # Activate the billing plan
            if billing_plan.activate():
                # Create billing agreement
                billing_agreement = paypalrestsdk.BillingAgreement({
                    'name': f"{plan[2]} Subscription",
                    'description': plan[3],
                    'start_date': (datetime.now() + timedelta(minutes=1)).isoformat() + 'Z',
                    'plan': {
                        'id': billing_plan.id
                    },
                    'payer': {
                        'payment_method': 'paypal'
                    }
                })
                
                if billing_agreement.create():
                    # Save subscription to database (pending approval)
                    subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
                    cursor.execute('''
                        INSERT INTO subscriptions 
                        (subscription_id, client_id, plan_id, payment_provider, provider_subscription_id,
                         status, billing_cycle, amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (subscription_id, client_id, plan_id, 'paypal', billing_agreement.id,
                          'pending_approval', billing_cycle, amount))
                    
                    conn.commit()
                    conn.close()
                    
                    # Get approval URL
                    for link in billing_agreement.links:
                        if link.rel == 'approval_url':
                            return {
                                'success': True,
                                'subscription_id': subscription_id,
                                'approval_url': link.href,
                                'paypal_agreement_id': billing_agreement.id
                            }
                
        return {'success': False, 'error': 'Failed to create PayPal subscription'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_stripe_webhook(payload, signature):
    """Handle Stripe webhook events"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_CONFIG['webhook_secret']
        )
        
        if event['type'] == 'invoice.payment_succeeded':
            # Handle successful payment
            invoice = event['data']['object']
            subscription_id = invoice['subscription']
            
            # Update subscription status
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'active', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
            ''', (datetime.now().isoformat(), subscription_id))
            
            # Update client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'active'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
                )
            ''', (subscription_id,))
            
            conn.commit()
            conn.close()
            
        elif event['type'] == 'invoice.payment_failed':
            # Handle failed payment
            invoice = event['data']['object']
            subscription_id = invoice['subscription']
            
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'past_due', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
            ''', (datetime.now().isoformat(), subscription_id))
            
            # Restrict client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'past_due'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
                )
            ''', (subscription_id,))
            
            conn.commit()
            conn.close()
            
        elif event['type'] == 'customer.subscription.deleted':
            # Handle subscription cancellation
            subscription = event['data']['object']
            subscription_id = subscription['id']
            
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'canceled', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
            ''', (datetime.now().isoformat(), subscription_id))
            
            # Restrict client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'canceled'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'stripe'
                )
            ''', (subscription_id,))
            
            conn.commit()
            conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def handle_paypal_webhook(payload, headers):
    """Handle PayPal webhook events"""
    try:
        # Verify PayPal webhook signature (implement based on PayPal documentation)
        
        event = json.loads(payload)
        event_type = event.get('event_type')
        
        if event_type == 'BILLING.SUBSCRIPTION.ACTIVATED':
            # Handle subscription activation
            subscription = event['resource']
            agreement_id = subscription['id']
            
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'active', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
            ''', (datetime.now().isoformat(), agreement_id))
            
            # Update client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'active'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
                )
            ''', (agreement_id,))
            
            conn.commit()
            conn.close()
            
        elif event_type == 'BILLING.SUBSCRIPTION.PAYMENT.FAILED':
            # Handle failed payment
            subscription = event['resource']
            agreement_id = subscription['billing_agreement_id']
            
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'past_due', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
            ''', (datetime.now().isoformat(), agreement_id))
            
            # Restrict client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'past_due'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
                )
            ''', (agreement_id,))
            
            conn.commit()
            conn.close()
            
        elif event_type == 'BILLING.SUBSCRIPTION.CANCELLED':
            # Handle subscription cancellation
            subscription = event['resource']
            agreement_id = subscription['id']
            
            conn = sqlite3.connect('client_management.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE subscriptions 
                SET status = 'canceled', updated_at = ?
                WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
            ''', (datetime.now().isoformat(), agreement_id))
            
            # Restrict client access
            cursor.execute('''
                UPDATE clients 
                SET subscription_status = 'canceled'
                WHERE client_id = (
                    SELECT client_id FROM subscriptions 
                    WHERE provider_subscription_id = ? AND payment_provider = 'paypal'
                )
            ''', (agreement_id,))
            
            conn.commit()
            conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_client_subscription_status(client_id):
    """Get current subscription status for a client"""
    conn = sqlite3.connect('client_management.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, pp.name, pp.max_users, pp.max_websites, pp.features
        FROM subscriptions s
        JOIN payment_plans pp ON s.plan_id = pp.plan_id
        WHERE s.client_id = ? AND s.status IN ('active', 'trialing', 'past_due')
        ORDER BY s.created_at DESC
        LIMIT 1
    ''', (client_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'has_subscription': True,
            'subscription_id': result[1],
            'plan_id': result[3],
            'payment_provider': result[4],
            'status': result[6],
            'billing_cycle': result[7],
            'amount': result[8],
            'current_period_end': result[11],
            'plan_name': result[15],
            'max_users': result[16],
            'max_websites': result[17],
            'features': json.loads(result[18]) if result[18] else []
        }
    else:
        return {'has_subscription': False}

# Initialize payment system
init_payment_database()
create_default_payment_plans()

print("💳 Payment System Initialized")
print("✅ Stripe integration ready")
print("✅ PayPal integration ready")
print("✅ Subscription management ready")
print("✅ Webhook handling ready")

