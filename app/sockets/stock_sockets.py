from flask_socketio import emit, join_room, leave_room
from flask import session, request
import logging

def register_stock_sockets(socketio):
    """Register SocketIO events for Stock Analysis"""
    
    @socketio.on('join_task_room')
    def handle_join_task_room(data):
        user_uid = session.get('firebase_user_uid')
        if not user_uid:
            return  # Ignore unauthenticated
            
        ticker = data.get('ticker')
        if ticker:
            room = f"{user_uid}_{ticker}"
            join_room(room)
            logging.info(f"User {user_uid} joined room {room}")

    @socketio.on('analysis_progress')
    def handle_analysis_progress(data):
        # Client likely doesn't emit this, server does??
        # Usually server emits to client.
        # But if client sends ack, handle here.
        pass
    
    # Add other stock-specific events here
