from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from datetime import datetime
import os
from config.firebase_admin_setup import get_firestore_client
import uuid

info_bp = Blueprint('info', __name__)

@info_bp.route('/about')
def about():
    return render_template('info/about.html')

@info_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('info/contact.html')

@info_bp.route('/api/contact', methods=['POST'])
def contact_form():
    """Handle contact form submissions and store them in Firestore for admin notifications"""
    try:
        # Get form data
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Get Firestore client
        db = get_firestore_client()
        
        # Prepare contact submission data
        contact_data = {
            'id': str(uuid.uuid4()),
            'name': name,
            'email': email,
            'subject': subject,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'status': 'new',
            'read': False
        }
        
        # Save to Firestore collection
        db.collection('contact_submissions').document(contact_data['id']).set(contact_data)
        
        # Add notification for admin
        notification_data = {
            'id': str(uuid.uuid4()),
            'type': 'contact_form',
            'title': f"New Contact Form: {subject}",
            'content': f"New message from {name} ({email})",
            'timestamp': datetime.now().isoformat(),
            'read': False,
            'contact_id': contact_data['id']
        }
        
        db.collection('admin_notifications').document(notification_data['id']).set(notification_data)
        
        return {"success": True, "message": "Thank you! Your message has been sent. We'll get back to you shortly."}, 200
    except Exception as e:
        return {"success": False, "message": "There was an error processing your request. Please try again later."}, 500

@info_bp.route('/privacy')
def privacy():
    return render_template('info/privacy.html')

@info_bp.route('/terms')
def terms():
    return render_template('info/terms.html')

@info_bp.route('/faq')
def faq():
    return render_template('info/faq.html')

@info_bp.route('/how-it-works')
def how_it_works():
    return render_template('how-it-works.html')
