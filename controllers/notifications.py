from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime

from models.models import db, User, UserProfile, Notification

notifications = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications.route('/')
@login_required
def view_notifications():
    # Get all unread notifications
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.created_at.desc()).all()
    
    # Get read notifications (limited to 20 for performance)
    read_notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=True
    ).order_by(Notification.created_at.desc()).limit(20).all()
    
    return render_template('notifications/list.html', 
                           unread_notifications=unread_notifications,
                           read_notifications=read_notifications)

@notifications.route('/mark_read/<int:notification_id>', methods=['POST'])
@login_required
def mark_read(notification_id):
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=current_user.id
    ).first_or_404()
    
    notification.is_read = True
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    
    return redirect(url_for('notifications.view_notifications'))

@notifications.route('/mark_all_read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).update({Notification.is_read: True})
    
    db.session.commit()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True)
    
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('notifications.view_notifications'))

@notifications.route('/count')
@login_required
def get_count():
    # Get count of unread notifications
    count = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).count()
    
    return jsonify(count=count) 