from flask import Blueprint, request, jsonify
from models import db, Provider

provider_bp = Blueprint('provider', __name__, url_prefix='/api/providers')

@provider_bp.route('/', methods=['GET'])
def get_all_providers():
    """Get all providers"""
    providers = Provider.query.all()
    return jsonify([p.to_dict() for p in providers])

@provider_bp.route('/<int:provider_id>', methods=['GET'])
def get_provider(provider_id):
    """Get a specific provider"""
    provider = Provider.query.get_or_404(provider_id)
    return jsonify(provider.to_dict())

@provider_bp.route('/', methods=['POST'])
def create_provider():
    """Create a new provider"""
    data = request.get_json()
    
    try:
        provider = Provider(
            name=data['name'],
            provider_type=data.get('provider_type'),
            address=data.get('address'),
            phone=data.get('phone'),
            email=data.get('email'),
            website=data.get('website')
        )
        
        db.session.add(provider)
        db.session.commit()
        
        return jsonify(provider.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@provider_bp.route('/<int:provider_id>', methods=['PUT'])
def update_provider(provider_id):
    """Update a provider"""
    provider = Provider.query.get_or_404(provider_id)
    data = request.get_json()
    
    try:
        if 'name' in data:
            provider.name = data['name']
        if 'provider_type' in data:
            provider.provider_type = data['provider_type']
        if 'address' in data:
            provider.address = data['address']
        if 'phone' in data:
            provider.phone = data['phone']
        if 'email' in data:
            provider.email = data['email']
        if 'website' in data:
            provider.website = data['website']
        
        db.session.commit()
        return jsonify(provider.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@provider_bp.route('/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    """Delete a provider"""
    provider = Provider.query.get_or_404(provider_id)
    
    try:
        db.session.delete(provider)
        db.session.commit()
        return jsonify({'message': 'Provider deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
