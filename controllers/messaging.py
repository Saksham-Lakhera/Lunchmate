from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import and_, or_, desc, func
import random

from models.models import db, User, UserProfile, UserPhoto, matches, ConversationStarter, LunchPreference, CuisinePreference, Restaurant

# For a real application, we'd create a proper Message model
# For simplicity in this prototype, we'll add a basic messages table
class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', cascade='all, delete-orphan'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'

messaging = Blueprint('messaging', __name__, url_prefix='/messaging')

@messaging.route('/conversations')
@login_required
def conversations():
    # Get all matched users
    matched_records = db.session.query(matches).filter(
        matches.c.user_id == current_user.id,
        matches.c.status == 'matched'
    ).all()
    
    matched_user_ids = [m.matched_user_id for m in matched_records]
    matched_users = User.query.filter(User.id.in_(matched_user_ids)).all()
    
    # Get last message and unread count for each conversation
    conversations = []
    for user in matched_users:
        # Get the last message
        last_message = Message.query.filter(
            or_(
                and_(Message.sender_id == current_user.id, Message.receiver_id == user.id),
                and_(Message.sender_id == user.id, Message.receiver_id == current_user.id)
            )
        ).order_by(desc(Message.created_at)).first()
        
        # Get unread count
        unread_count = Message.query.filter_by(
            sender_id=user.id,
            receiver_id=current_user.id,
            is_read=False
        ).count()
        
        # Get user photo
        primary_photo = UserPhoto.query.filter_by(user_id=user.id, is_primary=True).first()
        photo_url = primary_photo.photo_path if primary_photo else 'images/default-profile.png'
        
        conversations.append({
            'user': user,
            'profile': user.profile,
            'photo_url': photo_url,
            'last_message': last_message,
            'unread_count': unread_count
        })
    
    # Sort conversations by last message time, newest first
    conversations.sort(
        key=lambda x: x['last_message'].created_at if x['last_message'] else datetime.min, 
        reverse=True
    )
    
    return render_template('messaging/conversations.html', conversations=conversations)

@messaging.route('/conversation/<int:user_id>', methods=['GET', 'POST'])
@login_required
def conversation(user_id):
    # Check if this is a valid user and that they are matched
    user = db.session.query(User).\
        join(matches, 
             ((matches.c.user_id == user_id) & (matches.c.matched_user_id == current_user.id)) | 
             ((matches.c.user_id == current_user.id) & (matches.c.matched_user_id == user_id))).\
        filter(User.id == user_id).\
        filter(matches.c.status == 'matched').\
        first()
    
    if not user:
        flash('User not found or not matched with you.', 'danger')
        return redirect(url_for('messaging.conversations'))
    print("here")
    # Process message form
    if request.method == 'POST':
        print("okay")
        content = request.form.get('content', '').strip()
        print(content)
        
        if content:
            message = Message(
                sender_id=current_user.id,
                receiver_id=user_id,
                content=content.strip()
            )
            db.session.add(message)
            db.session.commit()
            
            # If AJAX request, return the message
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'id': message.id,
                    'content': message.content,
                    'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_sender': True
                })
    
    # Mark all messages from this user as read
    unread_messages = Message.query.filter_by(
        sender_id=user_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()
    
    for message in unread_messages:
        message.is_read = True
    
    db.session.commit()
    
    # Get all messages between the two users
    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at).all()
    
    # Get user info and primary photo in a single query with join
    user_with_photo = db.session.query(User, UserPhoto).\
        outerjoin(UserPhoto, and_(UserPhoto.user_id == User.id, UserPhoto.is_primary == True)).\
        filter(User.id == user_id).\
        first()
    
    if user_with_photo and user_with_photo[1]:
        photo_url = user_with_photo[1].photo_path
    else:
        photo_url = 'images/default-profile.png'
    
    # Get suggested conversation starters
    conversation_starters = get_conversation_starters_for_user(user_id)
    
    # Get common availability between users
    common_availability = get_common_availability(current_user.id, user_id)
    
    # Get recommended restaurants based on common preferences
    recommended_restaurants = get_recommended_restaurants(current_user.id, user_id)
    
    return render_template('messaging/conversation.html', 
                          user=user, 
                          profile=user.profile,
                          photo_url=photo_url,
                          messages=messages,
                          conversation_starters=conversation_starters,
                          common_availability=common_availability,
                          recommended_restaurants=recommended_restaurants)

@messaging.route('/api/messages/<int:user_id>/poll', methods=['GET'])
@login_required
def poll_messages(user_id):
    """API endpoint to poll for new messages"""
    last_id = request.args.get('last_id', 0, type=int)
    
    # Get new messages from the other user
    new_messages = Message.query.filter(
        Message.id > last_id,
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id
    ).order_by(Message.created_at).all()
    
    # Mark messages as read
    for message in new_messages:
        message.is_read = True
    
    db.session.commit()
    
    # Format messages for JSON response
    messages_data = [{
        'id': message.id,
        'content': message.content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_sender': False
    } for message in new_messages]
    
    return jsonify(messages_data)

@messaging.route('/api/conversation_starters/<int:user_id>', methods=['GET'])
@login_required
def get_conversation_starters(user_id):
    """API endpoint to get conversation starters for a matched user"""
    starters = get_conversation_starters_for_user(user_id)
    return jsonify(starters)

def get_conversation_starters_for_user(user_id):
    """Get personalized conversation starters based on user interests"""
    starters = []
    
    # Get the other user's preferences with a join to avoid multiple queries
    user_and_preferences = db.session.query(User, LunchPreference).\
        outerjoin(LunchPreference, LunchPreference.user_id == User.id).\
        filter(User.id == user_id).\
        first()
    
    user = user_and_preferences[0] if user_and_preferences else None
    user_preferences = user_and_preferences[1] if user_and_preferences and len(user_and_preferences) > 1 else None
    
    # Try to find interest-based starters
    if user_preferences:
        # Get cuisine preferences
        cuisine_prefs = CuisinePreference.query.filter_by(lunch_preference_id=user_preferences.id).all()
        if cuisine_prefs:
            # Look for food-related conversation starters
            food_starters = ConversationStarter.query.filter_by(category='Food').limit(3).all()
            starters.extend(food_starters)
            
        # Add university/education starters based on user profile
        if user.profile:
            education_starters = ConversationStarter.query.filter_by(category='Education').limit(2).all()
            starters.extend(education_starters)
    
    # If we don't have enough starters yet, add some general ones
    if len(starters) < 5:
        general_starters = ConversationStarter.query.filter_by(category='General').limit(5 - len(starters)).all()
        starters.extend(general_starters)
    
    # If still no starters, get random ones
    if not starters:
        # Use order_by random instead of func.random() which might not be supported
        starters = ConversationStarter.query.order_by(func.random()).limit(5).all()
        # Fallback if random function doesn't work in the database
        if not starters:
            starters = ConversationStarter.query.limit(5).all()
            # Shuffle the results in memory
            random.shuffle(starters)
    
    # Convert to dictionary for easier use in template
    return [{'id': s.question_id, 'question': s.question, 'category': s.category} for s in starters]

def get_common_availability(user1_id, user2_id):
    """Find common availability times between two users"""
    from models.models import UserAvailability
    
    # Query both users' availability in a single query
    availabilities = db.session.query(
        UserAvailability.user_id,
        UserAvailability.day_of_week,
        UserAvailability.start_time,
        UserAvailability.end_time
    ).filter(
        UserAvailability.user_id.in_([user1_id, user2_id])
    ).all()
    
    # Separate the results by user
    user1_availability = [a for a in availabilities if a.user_id == user1_id]
    user2_availability = [a for a in availabilities if a.user_id == user2_id]
    
    # Convert to days
    days = {0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'}
    
    # Build availability map for each user by day
    user1_avail_map = {}
    for avail in user1_availability:
        day = days[avail.day_of_week]
        if day not in user1_avail_map:
            user1_avail_map[day] = []
        user1_avail_map[day].append({'start': avail.start_time, 'end': avail.end_time})
    
    user2_avail_map = {}
    for avail in user2_availability:
        day = days[avail.day_of_week]
        if day not in user2_avail_map:
            user2_avail_map[day] = []
        user2_avail_map[day].append({'start': avail.start_time, 'end': avail.end_time})
    
    # Find overlapping times
    common_times = {}
    for day in days.values():
        if day in user1_avail_map and day in user2_avail_map:
            common_times[day] = []
            for time1 in user1_avail_map[day]:
                for time2 in user2_avail_map[day]:
                    # Check for overlap
                    latest_start = max(time1['start'], time2['start'])
                    earliest_end = min(time1['end'], time2['end'])
                    if latest_start < earliest_end:
                        common_times[day].append({
                            'start': latest_start.strftime('%I:%M %p'),
                            'end': earliest_end.strftime('%I:%M %p')
                        })
    
    return common_times 

def get_recommended_restaurants(user1_id, user2_id):
    """Get recommended restaurants based on common food preferences between two users"""
    from models.models import Restaurant, LunchPreference, CuisinePreference
    from sqlalchemy import or_
    
    # Get both users' lunch preferences
    user1_preferences = LunchPreference.query.filter_by(user_id=user1_id).first()
    user2_preferences = LunchPreference.query.filter_by(user_id=user2_id).first()
    
    if not user1_preferences or not user2_preferences:
        return []
    
    # Get cuisine preferences for both users
    user1_cuisines = [cp.cuisine_type.lower() for cp in user1_preferences.cuisine_preferences]
    user2_cuisines = [cp.cuisine_type.lower() for cp in user2_preferences.cuisine_preferences]
    
    # Find common cuisines
    common_cuisines = set(user1_cuisines).intersection(set(user2_cuisines))
    
    # If no common cuisines, return recommendations from all their cuisines
    cuisine_list = list(common_cuisines) if common_cuisines else list(set(user1_cuisines + user2_cuisines))
    
    if not cuisine_list:
        return []
    
    # Find restaurants within budget constraints
    max_budget = min(
        user1_preferences.max_budget or float('inf'),
        user2_preferences.max_budget or float('inf')
    )
    
    restaurant_query = Restaurant.query
    
    # Apply cuisine filter
    cuisine_filters = []
    for cuisine in cuisine_list:
        cuisine_filters.append(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
    
    if cuisine_filters:
        restaurant_query = restaurant_query.filter(or_(*cuisine_filters))
    
    # Apply budget filter
    if max_budget != float('inf'):
        max_price_range = min(5, int(max_budget / 20) + 1)
        restaurant_query = restaurant_query.filter(Restaurant.price_range <= max_price_range)
    
    # Get top 5 recommended restaurants
    recommended_restaurants = restaurant_query.order_by(Restaurant.rating.desc()).limit(5).all()
    
    return recommended_restaurants 