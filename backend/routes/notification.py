from flask import Blueprint, request, jsonify
from models import db, Notification, Child

notification_bp = Blueprint('notification', __name__, url_prefix='/api/notifications')

@notification_bp.route('/', methods=['GET'])
def get_all_notifications():
    """Get all notifications"""
    notifications = Notification.query.all()
    return jsonify([n.to_dict() for n in notifications])

@notification_bp.route('/child/<int:child_id>', methods=['GET'])
def get_child_notifications(child_id):
    """Get notifications for a specific child"""
    notifications = Notification.query.filter_by(child_id=child_id).all()
    return jsonify([n.to_dict() for n in notifications])

@notification_bp.route('/<int:notification_id>', methods=['GET'])
def get_notification(notification_id):
    """Get a specific notification"""
    notification = Notification.query.get_or_404(notification_id)
    return jsonify(notification.to_dict())

@notification_bp.route('/<int:notification_id>/mark-read', methods=['PUT'])
def mark_as_read(notification_id):
    """Mark notification as read"""
    notification = Notification.query.get_or_404(notification_id)
    
    try:
        notification.is_read = True
        db.session.commit()
        return jsonify(notification.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@notification_bp.route('/<int:notification_id>', methods=['DELETE'])
def delete_notification(notification_id):
    """Delete a notification"""
    notification = Notification.query.get_or_404(notification_id)
    
    try:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({'message': 'Notification deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
