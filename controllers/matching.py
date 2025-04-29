import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, not_, func
import json

from models.models import db, User, UserProfile, UserPhoto, LunchPreference, UserAvailability, matches, Notification, Restaurant, LunchMeeting
from models.models import CuisinePreference, DietaryRestriction, ConversationStarter

matching = Blueprint('matching', __name__, url_prefix='/matching')

@matching.route('/')
@login_required
def index():
    """Landing page for matching section with tabs"""
    return redirect(url_for('matching.discover'))

@matching.route('/discover')
@login_required
def discover():
    """Show users that haven't been liked/matched/blocked yet (new users to discover)"""
    # Clear any previous discover session data
    if 'discover_users' in session:
        session.pop('discover_users', None)
    if 'discover_index' in session:
        session.pop('discover_index', None)
    
    # Get the first batch of 3 users
    users_data = get_next_batch_of_users(3)
    
    # Store in session
    session['discover_users'] = users_data
    session['discover_index'] = 0  # Next index to fetch from
    
    # Return users for display
    display_users = get_users_with_data(users_data)
    
    return render_template('matching/discover.html', users=display_users, section='discover')

def get_next_batch_of_users(limit=10):
    """Get the next batch of users for discovery"""
    
    # Get all users that have been interacted with (liked, matched, blocked)
    interacted_user_ids = db.session.query(matches.c.matched_user_id).filter(
        matches.c.user_id == current_user.id
    ).all()
    
    # Convert to a flat list
    interacted_user_ids = [id[0] for id in interacted_user_ids]
    
    # If there are previous users in the session, also exclude those
    if 'processed_user_ids' in session:
        interacted_user_ids.extend(session['processed_user_ids'])
    
    # Build a single efficient query with all needed joins
    # This loads users, profiles, photos, preferences, cuisines, dietary restrictions, and availability all at once
    query = db.session.query(
        User, 
        UserProfile, 
        UserPhoto, 
        LunchPreference, 
        CuisinePreference, 
        DietaryRestriction, 
        UserAvailability
    ).\
    join(UserProfile, User.id == UserProfile.user_id).\
    outerjoin(UserPhoto, User.id == UserPhoto.user_id).\
    outerjoin(LunchPreference, User.id == LunchPreference.user_id).\
    outerjoin(CuisinePreference, LunchPreference.id == CuisinePreference.lunch_preference_id).\
    outerjoin(DietaryRestriction, LunchPreference.id == DietaryRestriction.lunch_preference_id).\
    outerjoin(UserAvailability, User.id == UserAvailability.user_id).\
    filter(
        User.id != current_user.id,
        UserProfile.university == current_user.profile.university,
        ~User.id.in_(interacted_user_ids)
    ).\
    order_by(User.id)
    
    # Execute the query
    results = query.all()
    
    # Group results by user
    user_data_map = {}
    for user, profile, photo, preference, cuisine, restriction, availability in results:
        if user.id not in user_data_map:
            user_data_map[user.id] = {
                'user': user,
                'profile': profile,
                'photos': [],
                'preference': preference,
                'cuisines': [],
                'restrictions': [],
                'availabilities': []
            }
        
        if photo and photo not in user_data_map[user.id]['photos']:
            user_data_map[user.id]['photos'].append(photo)
        
        if cuisine and cuisine not in user_data_map[user.id]['cuisines']:
            user_data_map[user.id]['cuisines'].append(cuisine)
            
        if restriction and restriction not in user_data_map[user.id]['restrictions']:
            user_data_map[user.id]['restrictions'].append(restriction)
            
        if availability and availability not in user_data_map[user.id]['availabilities']:
            user_data_map[user.id]['availabilities'].append(availability)
    
    # Load current user data once
    current_user_preferences = current_user.lunch_preferences
    current_user_availabilities = current_user.availability
    current_cuisines = set()
    if current_user_preferences and current_user_preferences.cuisine_preferences:
        current_cuisines = set([cp.cuisine_type.lower() for cp in current_user_preferences.cuisine_preferences])
    
    # Process all users' data
    user_data = []
    
    for user_id, data in user_data_map.items():
        user = data['user']
        profile = data['profile']
        photos = data['photos']
        preference = data['preference']
        cuisines = data['cuisines']
        restrictions = data['restrictions']
        availabilities = data['availabilities']
        
        # Find primary photo
        primary_photo = next((photo for photo in photos if photo.is_primary), None)
        photo_url = primary_photo.photo_path if primary_photo else 'images/default-profile.png'
        
        # Initial score starts high for university match (already filtered above)
        score = 100
        
        # Check timing compatibility
        timing_match = False
        if current_user_availabilities and availabilities:
            for current_user_avail in current_user_availabilities:
                for user_avail in availabilities:
                    if (current_user_avail.day_of_week == user_avail.day_of_week and
                        current_user_avail.start_time <= user_avail.end_time and
                        current_user_avail.end_time >= user_avail.start_time):
                        timing_match = True
                        score += 30
                        break
                if timing_match:
                    break
        
        # Check food preference compatibility
        food_match = False
        user_cuisines = set()
        if cuisines:
            user_cuisines = set([cp.cuisine_type.lower() for cp in cuisines])
            
            # Add points for each matching cuisine
            common_cuisines = current_cuisines.intersection(user_cuisines)
            if common_cuisines:
                food_match = True
                score += len(common_cuisines) * 10
            
            # Budget compatibility
            if current_user_preferences and current_user_preferences.max_budget and preference and preference.max_budget:
                # If budgets are within 20% of each other
                budget_ratio = min(current_user_preferences.max_budget, preference.max_budget) / max(current_user_preferences.max_budget, preference.max_budget)
                if budget_ratio >= 0.8:
                    score += 15
        
        # Get recommended restaurants - do this in a single optimized query for all users
        recommended_restaurants = []
        if food_match and current_cuisines and user_cuisines:
            common_cuisines = current_cuisines.intersection(user_cuisines)
            if common_cuisines:
                cuisine_list = list(common_cuisines)
                
                # Find restaurants within budget constraints
                max_budget = float('inf')
                if current_user_preferences and preference:
                    max_budget = min(
                        current_user_preferences.max_budget or float('inf'),
                        preference.max_budget or float('inf')
                    )
                
                # Only do the restaurant query if we have valid constraints
                if cuisine_list and max_budget != float('inf'):
                    # Build a single efficient query
                    restaurant_query = Restaurant.query
                    
                    # Apply cuisine filter
                    cuisine_filters = []
                    for cuisine in cuisine_list:
                        cuisine_filters.append(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
                    
                    if cuisine_filters:
                        restaurant_query = restaurant_query.filter(or_(*cuisine_filters))
                    
                    # Apply budget filter
                    max_price_range = min(5, int(max_budget / 20) + 1)
                    restaurant_query = restaurant_query.filter(Restaurant.price_range <= max_price_range)
                    
                    # Get top 3 recommended restaurants
                    recommended_restaurants = restaurant_query.order_by(Restaurant.rating.desc()).limit(3).all()
        
        user_data.append({
            'user_id': user.id,
            'email': user.email,
            'profile': {
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'university': profile.university,
                'department': profile.department,
                'bio': profile.bio,
                'graduation_year': profile.graduation_year
            },
            'photo_url': photo_url,
            'all_photos': [{'id': photo.id, 'path': photo.photo_path, 'is_primary': photo.is_primary} for photo in photos],
            'preferences': preference.id if preference else None,
            'cuisine_preferences': [{'cuisine_type': cp.cuisine_type} for cp in cuisines] if cuisines else [],
            'dietary_restrictions': [{'restriction_type': dr.restriction_type} for dr in restrictions] if restrictions else [],
            'max_budget': preference.max_budget if preference else None,
            'availability': [{'day_of_week': avail.day_of_week, 'start_time': avail.start_time.strftime('%H:%M'), 'end_time': avail.end_time.strftime('%H:%M')} for avail in availabilities],
            'compatibility_score': score,
            'timing_match': timing_match,
            'food_match': food_match,
            'recommended_restaurants': [{'id': r.id, 'name': r.name, 'location': r.location, 'cuisine_type': r.cuisine_type, 'price_range': r.price_range, 'rating': r.rating} for r in recommended_restaurants]
        })
    
    # Sort by compatibility score (highest first)
    user_data.sort(key=lambda x: x['compatibility_score'], reverse=True)
    
    # Limit to requested number of users
    return user_data[:limit]

def get_users_with_data(user_data_list):
    """Convert session user data back to full objects for template rendering"""
    result = []
    
    for user_data in user_data_list:
        user = User.query.get(user_data['user_id'])
        if not user:
            continue
            
        # Convert availability strings back to datetime objects for template
        if 'availability' in user_data:
            for avail in user_data['availability']:
                # Store original strings for later use in the template
                avail['start_time_str'] = avail['start_time']
                avail['end_time_str'] = avail['end_time']
        
        # Add the user object for template compatibilty
        data = {
            'user': user,
            'profile': user.profile,
            'photo_url': user_data['photo_url'],
            'all_photos': [photo for photo in UserPhoto.query.filter_by(user_id=user.id).all()],
            'preferences': user.lunch_preferences,
            'compatibility_score': user_data['compatibility_score'],
            'timing_match': user_data['timing_match'],
            'food_match': user_data['food_match'],
            'recommended_restaurants': [Restaurant.query.get(r['id']) for r in user_data['recommended_restaurants']]
        }
        result.append(data)
    
    return result

@matching.route('/next_discover_user')
@login_required
def next_discover_user():
    """Returns the HTML for the next user to display"""
    try:
        if 'discover_users' not in session:
            # Initialize empty lists if not present
            session['discover_users'] = []
            session['discover_index'] = 0
            session['processed_user_ids'] = []
        
        users = session.get('discover_users', [])
        index = session.get('discover_index', 0)
        
        # Check if we need to get more users
        if not users or index >= len(users):
            # Initialize processed_user_ids if not exists
            if 'processed_user_ids' not in session:
                session['processed_user_ids'] = []
            
            # Add current batch to processed_user_ids
            processed_ids = session.get('processed_user_ids', [])
            for user_data in users:
                if user_data.get('user_id') not in processed_ids:
                    processed_ids.append(user_data.get('user_id'))
            session['processed_user_ids'] = processed_ids
            session.modified = True
            
            # Get next batch of users
            new_users = get_next_batch_of_users(3)
            
            # If no more users, return no results
            if not new_users:
                return jsonify({'success': False, 'message': 'No more users available'})
            
            # Update session with new batch
            session['discover_users'] = new_users
            session['discover_index'] = 0
            index = 0
            users = new_users
            session.modified = True
        
        # Get the next user
        next_user_data = users[index]
        
        # Update the index for next time
        session['discover_index'] = index + 1
        session.modified = True
        
        # Convert to full user data
        user_obj = get_users_with_data([next_user_data])
        if not user_obj:
            # If user not found, just return success false to trigger page refresh
            return jsonify({'success': False})
        
        # Render the user card HTML
        html = render_template('matching/user_card.html', user_data=user_obj[0])
        
        return jsonify({
            'success': True, 
            'html': html,
            'user_id': next_user_data.get('user_id')
        })
    except Exception as e:
        print(f"Error in next_discover_user: {str(e)}")
        # Clear the session data to start fresh
        if 'discover_users' in session:
            session.pop('discover_users')
        if 'discover_index' in session:
            session.pop('discover_index')
        session.modified = True
        # Return success false to trigger page refresh
        return jsonify({'success': False})

@matching.route('/liked')
@login_required
def liked_users():
    """Shows users that you have liked but haven't matched with yet"""
    try:
        # Get users who the current user has liked but not matched with yet
        liked_users_query = db.session.query(
            User, UserProfile, UserPhoto
        ).join(
            matches, 
            and_(
                matches.c.user_id == current_user.id,
                matches.c.matched_user_id == User.id,
                matches.c.status == 'pending'
            )
        ).join(
            UserProfile, UserProfile.user_id == User.id
        ).outerjoin(
            UserPhoto, and_(UserPhoto.user_id == User.id, UserPhoto.is_primary == True)
        ).all()
        
        # Debug info
        print(f"Found {len(liked_users_query)} liked users with pending status")
        
        users_data = []
        
        for user, profile, photo in liked_users_query:
            photo_url = photo.photo_path if photo else 'images/default-profile.png'
            
            # Get all photos for this user
            all_photos = UserPhoto.query.filter_by(user_id=user.id).all()
            
            # Calculate compatibility - same as in matched_users
            current_user_preferences = current_user.lunch_preferences
            current_user_availabilities = current_user.availability
            
            # Check timing compatibility
            timing_match = False
            if current_user_availabilities and user.availability:
                for current_user_avail in current_user_availabilities:
                    for user_avail in user.availability:
                        if (current_user_avail.day_of_week == user_avail.day_of_week and
                            current_user_avail.start_time <= user_avail.end_time and
                            current_user_avail.end_time >= user_avail.start_time):
                            timing_match = True
                            break
                    if timing_match:
                        break
            
            # Check food preference compatibility
            food_match = False
            if current_user_preferences and user.lunch_preferences:
                # Check cuisine preferences
                if current_user_preferences.cuisine_preferences and user.lunch_preferences.cuisine_preferences:
                    current_cuisines = set([cp.cuisine_type.lower() for cp in current_user_preferences.cuisine_preferences])
                    user_cuisines = set([cp.cuisine_type.lower() for cp in user.lunch_preferences.cuisine_preferences])
                    
                    # Check for common cuisines
                    common_cuisines = current_cuisines.intersection(user_cuisines)
                    if common_cuisines:
                        food_match = True
            
            # Format in the same structure as matched_users for template compatibility
            users_data.append({
                'user': user,
                'profile': profile,
                'photo_url': photo_url,
                'all_photos': all_photos,
                'preferences': user.lunch_preferences,
                'timing_match': timing_match,
                'food_match': food_match,
                'date_liked': db.session.query(matches.c.created_at).filter(
                    matches.c.user_id == current_user.id,
                    matches.c.matched_user_id == user.id
                ).scalar()
            })
        
        return render_template('matching/liked.html', users=users_data)
    except Exception as e:
        print(f"Error in liked_users: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('matching/liked.html', users=[])

@matching.route('/matched')
@login_required
def matched_users():
    """Shows users that you have matched with"""
    try:
        # Get all matched users (using the correct match_status column)
        matched_users_ids = db.session.query(matches.c.matched_user_id).filter(
            matches.c.user_id == current_user.id,
            matches.c.status == 'matched'
        ).all()
        
        matched_users_ids = [user_id[0] for user_id in matched_users_ids]
        
        # Also get users who matched with current user
        reverse_matched_users_ids = db.session.query(matches.c.user_id).filter(
            matches.c.matched_user_id == current_user.id,
            matches.c.status == 'matched'
        ).all()
        
        reverse_matched_users_ids = [user_id[0] for user_id in reverse_matched_users_ids]
        
        # Combine both lists (users current user matched with and users who matched with current user)
        all_matched_user_ids = list(set(matched_users_ids + reverse_matched_users_ids))
        
        # Debug info
        print(f"Found {len(matched_users_ids)} outgoing matches and {len(reverse_matched_users_ids)} incoming matches.")
        print(f"Total unique matched users: {len(all_matched_user_ids)}")
        
        # Get user data for all matched users
        users_data = []
        
        for user_id in all_matched_user_ids:
            user = User.query.get(user_id)
            if not user:
                print(f"Warning: User with ID {user_id} not found in database")
                continue
                
            # Get user's primary photo
            primary_photo = UserPhoto.query.filter_by(user_id=user.id, is_primary=True).first()
            photo_url = primary_photo.photo_path if primary_photo else 'images/default-profile.png'
            
            # Get all photos
            all_photos = UserPhoto.query.filter_by(user_id=user.id).all()
            
            # Find match data
            match_data = db.session.query(matches).filter(
                or_(
                    and_(matches.c.user_id == current_user.id, matches.c.matched_user_id == user.id),
                    and_(matches.c.user_id == user.id, matches.c.matched_user_id == current_user.id)
                ),
                matches.c.status == 'matched'
            ).first()
            
            if not match_data:
                print(f"Warning: No match data found for user {user_id} and current user {current_user.id}")
                continue
                
            # Calculate compatibility
            current_user_preferences = current_user.lunch_preferences
            current_user_availabilities = current_user.availability
            
            # Check timing compatibility
            timing_match = False
            if current_user_availabilities and user.availability:
                for current_user_avail in current_user_availabilities:
                    for user_avail in user.availability:
                        if (current_user_avail.day_of_week == user_avail.day_of_week and
                            current_user_avail.start_time <= user_avail.end_time and
                            current_user_avail.end_time >= user_avail.start_time):
                            timing_match = True
                            break
                    if timing_match:
                        break
            
            # Check food preference compatibility
            food_match = False
            common_cuisines = []
            if current_user_preferences and user.lunch_preferences:
                # Check cuisine preferences
                if current_user_preferences.cuisine_preferences and user.lunch_preferences.cuisine_preferences:
                    current_cuisines = set([cp.cuisine_type.lower() for cp in current_user_preferences.cuisine_preferences])
                    user_cuisines = set([cp.cuisine_type.lower() for cp in user.lunch_preferences.cuisine_preferences])
                    
                    # Check for common cuisines
                    common_cuisines = current_cuisines.intersection(user_cuisines)
                    if common_cuisines:
                        food_match = True
            
            # Get recommended restaurants based on common preferences
            recommended_restaurants = []
            if food_match:
                # Find restaurants matching both users' cuisine preferences
                if current_user_preferences and user.lunch_preferences and current_user_preferences.cuisine_preferences and user.lunch_preferences.cuisine_preferences:
                    # Convert set to list for SQLAlchemy query
                    cuisine_list = list(common_cuisines)
                    
                    # Find restaurants within budget constraints
                    max_budget = min(
                        current_user_preferences.max_budget or float('inf'),
                        user.lunch_preferences.max_budget or float('inf')
                    )
                    
                    restaurant_query = Restaurant.query
                    
                    # Apply cuisine filter if we have common cuisines
                    if cuisine_list:
                        cuisine_filters = []
                        for cuisine in cuisine_list:
                            cuisine_filters.append(Restaurant.cuisine_type.ilike(f'%{cuisine}%'))
                        
                        if cuisine_filters:
                            restaurant_query = restaurant_query.filter(or_(*cuisine_filters))
                    
                    # Apply budget filter
                    if max_budget != float('inf'):
                        # Assuming price_range 1-5, where 5 is most expensive
                        # We'll map budget to price range:
                        # $0-20: 1-2, $20-40: 2-3, $40-60: 3-4, $60+: 4-5
                        max_price_range = min(5, int(max_budget / 20) + 1)
                        restaurant_query = restaurant_query.filter(Restaurant.price_range <= max_price_range)
                    
                    # Get top 3 recommended restaurants
                    recommended_restaurants = restaurant_query.order_by(Restaurant.rating.desc()).limit(3).all()
            
            users_data.append({
                'user': user,
                'profile': user.profile,
                'photo_url': photo_url,
                'all_photos': all_photos,
                'preferences': user.lunch_preferences,
                'matched_date': match_data.matched_date if match_data and match_data.matched_date else datetime.utcnow(),
                'timing_match': timing_match,
                'food_match': food_match,
                'recommended_restaurants': recommended_restaurants
            })
        
        return render_template('matching/matched.html', matched_users=users_data)
    except Exception as e:
        print(f"Error in matched_users: {str(e)}")
        flash(f"An error occurred: {str(e)}", "danger")
        return render_template('matching/matched.html', matched_users=[])

# Legacy route for backward compatibility
@matching.route('/potential')
@login_required
def potential_matches():
    return redirect(url_for('matching.discover'))

# Legacy route for backward compatibility
@matching.route('/matches')
@login_required
def matches_list():
    return redirect(url_for('matching.matched_users'))

@matching.route('/like_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def like_user(user_id):
    """Like a user - this creates a Match if both users have liked each other"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if this user already exists in matches (avoid duplicates)
        existing_match = db.session.query(matches).filter(
            matches.c.user_id == current_user.id,
            matches.c.matched_user_id == user_id
        ).first()
        
        if not existing_match:
            # Create a new match
            db.session.execute(matches.insert().values(
                user_id=current_user.id,
                matched_user_id=user_id,
                status='pending',
                created_at=datetime.now()
            ))
            
            # Check if the other user has already liked the current user
            mutual_match = db.session.query(matches).filter(
                matches.c.user_id == user_id,
                matches.c.matched_user_id == current_user.id,
                matches.c.status == 'pending'
            ).first()
            
            if mutual_match:
                # Update both matches to 'matched'
                db.session.execute(matches.update().where(
                    matches.c.user_id == current_user.id,
                    matches.c.matched_user_id == user_id
                ).values(status='matched'))
                
                db.session.execute(matches.update().where(
                    matches.c.user_id == user_id,
                    matches.c.matched_user_id == current_user.id
                ).values(status='matched'))
                
                # Create notifications for both users
                new_notification_1 = Notification(
                    user_id=current_user.id,
                    notification_type='match',
                    related_user_id=user_id,
                    message=f"You matched with {user.profile.first_name}! You can now message each other.",
                    is_read=False
                )
                
                new_notification_2 = Notification(
                    user_id=user_id,
                    notification_type='match',
                    related_user_id=current_user.id,
                    message=f"You matched with {current_user.profile.first_name}! You can now message each other.",
                    is_read=False
                )
                
                db.session.add(new_notification_1)
                db.session.add(new_notification_2)
            
            db.session.commit()
        
        # Remove user from discover session
        if 'discover_users' in session:
            session['discover_users'] = [u for u in session['discover_users'] if u.get('user_id') != user_id]
            session.modified = True
        
        # Handle AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        return redirect(url_for('matching.discover'))
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in like_user: {str(e)}")
        
        # For AJAX requests, still return success to maintain UI flow
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        # For normal requests
        return redirect(url_for('matching.discover'))

@matching.route('/block_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def block_user(user_id):
    """Block a user or skip them - they won't show up in discover feed"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Check if this user already exists in matches (avoid duplicates)
        existing_match = db.session.query(matches).filter(
            matches.c.user_id == current_user.id,
            matches.c.matched_user_id == user_id
        ).first()
        
        if not existing_match:
            # Create a new match with status 'blocked'
            db.session.execute(matches.insert().values(
                user_id=current_user.id,
                matched_user_id=user_id,
                status='blocked',
                created_at=datetime.now()
            ))
            db.session.commit()
        
        # Remove user from discover session
        if 'discover_users' in session:
            session['discover_users'] = [u for u in session['discover_users'] if u.get('user_id') != user_id]
            session.modified = True
        
        # Handle AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        return redirect(url_for('matching.discover'))
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in block_user: {str(e)}")
        
        # For AJAX requests, still return success to maintain UI flow
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        # For normal requests
        return redirect(url_for('matching.discover'))

@matching.route('/unmatch_user/<int:user_id>', methods=['POST'])
@login_required
def unmatch_user(user_id):
    """Unmatch with a user - this will remove them from your matches list"""
    # Check if this is a valid user
    user = User.query.get_or_404(user_id)
    
    # Update both sides of the match
    db.session.execute(
        matches.update().where(
            and_(
                matches.c.user_id == current_user.id,
                matches.c.matched_user_id == user_id
            )
        ).values(status='unmatched')
    )
    
    db.session.execute(
        matches.update().where(
            and_(
                matches.c.user_id == user_id,
                matches.c.matched_user_id == current_user.id
            )
        ).values(status='unmatched')
    )
    
    db.session.commit()
    flash(f"You have unmatched {user.profile.first_name}.", 'info')
    return redirect(url_for('matching.matched_users')) 