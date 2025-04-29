#!/usr/bin/env python3
import os
import sys
import random
import argparse
from datetime import datetime, time, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from dotenv import load_dotenv
import time as time_module

# Add parent directory to path so we can import from there
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Import Flask application and models
from app import create_app
from models.models import (
    db, User, UserProfile, UserPhoto, LunchPreference, CuisinePreference,
    DietaryRestriction, UserAvailability, Restaurant, LunchMeeting,
    LunchMeetingParticipant, Notification, ConversationStarter, matches
)

# Data for generating random users
first_names = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth",
    "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
    "Christopher", "Nancy", "Daniel", "Lisa", "Matthew", "Margaret", "Anthony", "Betty", "Mark", "Sandra",
    "Donald", "Ashley", "Steven", "Dorothy", "Paul", "Kimberly", "Andrew", "Emily", "Joshua", "Donna"
]

last_names = [
    "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor",
    "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson",
    "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King",
    "Wright", "Lopez", "Hill", "Scott", "Green", "Adams", "Baker", "Gonzalez", "Nelson", "Carter"
]

departments = [
    "Computer Science", "Engineering", "Business", "Arts", "Medicine", "Law",
    "Mathematics", "Physics", "Chemistry", "Biology", "Economics", "Psychology",
    "Sociology", "History", "English", "Philosophy", "Political Science", 
    "Anthropology", "Data Science", "Environmental Science"
]

# Cuisine types
cuisines = [
    "American", "Italian", "Mexican", "Chinese", "Japanese", "Thai", "Indian", "Greek", "Mediterranean",
    "French", "German", "Korean", "Vietnamese", "Caribbean", "Spanish", "Middle Eastern"
]

# Restaurant data
restaurant_names = [
    "Campus Bistro", "Sushi Express", "Taco Town", "Pizza Palace", "Fresh Greens",
    "Curry House", "Noodle Bar", "Gourmet Cafe", "Burger Joint", "Mediterranean Delight",
    "Buffalo Wings", "Thai Spice", "Vegan Corner", "Steakhouse 55", "Seafood Harbor",
    "Pasta Paradise", "Breakfast Club", "Ramen House", "Sandwich Spot", "Coffee & Bagels"
]

locations = [
    "University Center", "Main Street", "College Avenue", "Campus Drive", "Health Sciences Building",
    "International Row", "Student Center", "Business School", "Sports Complex", "Arts District",
    "North Campus", "South Campus", "Downtown", "Tech Quad", "Library Plaza",
    "Research Park", "Medical Center", "Law Building", "Science Complex", "University Village"
]

# Dietary restrictions
restrictions = [
    "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Nut-Free", "Halal", "Kosher",
    "Pescatarian", "Keto", "Low-Carb", "Low-Fat", "Low-Sodium"
]

def clear_database():
    """Clear all data from the database"""
    print("Clearing database...")
    try:
        db.session.execute(text("DELETE FROM conversation_starters"))
        db.session.execute(text("DELETE FROM lunch_meeting_participants"))
        db.session.execute(text("DELETE FROM lunch_meetings"))
        db.session.execute(text("DELETE FROM messages"))
        db.session.execute(text("DELETE FROM matches"))
        db.session.execute(text("DELETE FROM user_availabilities"))
        db.session.execute(text("DELETE FROM dietary_restrictions"))
        db.session.execute(text("DELETE FROM cuisine_preferences"))
        db.session.execute(text("DELETE FROM lunch_preferences"))
        db.session.execute(text("DELETE FROM notifications"))
        db.session.execute(text("DELETE FROM user_photos"))
        db.session.execute(text("DELETE FROM user_profiles"))
        db.session.execute(text("DELETE FROM users"))
        db.session.execute(text("DELETE FROM restaurants"))
        db.session.commit()
        print("Database cleared successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing database: {e}")
        sys.exit(1)

def generate_users(count=100):
    """Generate specified number of users with all associated data"""
    print(f"Generating {count} users...")
    users = []
    
    for i in range(count):
        # Create a unique email using first name, last name and a number
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{i+1}@buffalo.edu"
        
        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash("12345678"),  # Simple password for testing
            created_at=datetime.now() - timedelta(days=random.randint(1, 90)),
            last_login=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create profile
        profile = UserProfile(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            university="University at Buffalo",
            department=random.choice(departments),
            bio=f"Hi, I'm {first_name}. I'm studying {random.choice(departments)} at UB. I enjoy {random.choice(['coffee', 'tea', 'sports', 'reading', 'movies', 'hiking', 'cooking', 'music'])} and meeting new people!",
            graduation_year=random.randint(2023, 2027),
            created_at=user.created_at,
            updated_at=user.created_at
        )
        db.session.add(profile)
        
        # Create photo
        photo = UserPhoto(
            user_id=user.id,
            photo_path=f"images/default-profile-{random.randint(1, 5)}.jpg",
            is_primary=True,
            upload_date=user.created_at
        )
        db.session.add(photo)
        
        # Create lunch preferences
        lunch_pref = LunchPreference(
            user_id=user.id,
            max_budget=random.choice([15.0, 20.0, 25.0, 30.0, None]),
            preferred_group_size=random.randint(2, 4),
            created_at=user.created_at,
            updated_at=user.created_at
        )
        db.session.add(lunch_pref)
        db.session.flush()
        
        # Add cuisine preferences
        selected_cuisines = random.sample([c.lower() for c in cuisines], random.randint(2, 5))
        
        for cuisine in selected_cuisines:
            cuisine_pref = CuisinePreference(
                lunch_preference_id=lunch_pref.id,
                cuisine_type=cuisine,
                created_at=user.created_at
            )
            db.session.add(cuisine_pref)
        
        # Add dietary restrictions
        if random.random() < 0.3:  # 30% chance of having restrictions
            selected_restrictions = random.sample([r.lower() for r in restrictions], random.randint(1, 2))
            for restriction in selected_restrictions:
                dietary_restriction = DietaryRestriction(
                    lunch_preference_id=lunch_pref.id,
                    restriction_type=restriction,
                    created_at=user.created_at
                )
                db.session.add(dietary_restriction)
        
        # Add availability
        for day in range(7):  # 0-6 for Monday-Sunday
            if random.random() < 0.7:  # 70% chance of being available on any given day
                start_hour = random.randint(11, 13)  # Between 11 AM and 1 PM
                end_hour = random.randint(13, 15)    # Between 1 PM and 3 PM
                
                if end_hour <= start_hour:
                    end_hour = start_hour + 1
                
                availability = UserAvailability(
                    user_id=user.id,
                    day_of_week=day,
                    start_time=time(start_hour, 0),
                    end_time=time(end_hour, 0),
                    created_at=user.created_at
                )
                db.session.add(availability)
        
        users.append(user)
        
        # Commit in batches to avoid memory issues
        if i % 100 == 0:
            try:
                db.session.commit()
                print(f"Committed batch of users: {i+1}/{count}")
            except Exception as e:
                db.session.rollback()
                print(f"Error committing batch of users: {e}")
                sys.exit(1)
    
    # Final commit for any remaining users
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error committing final batch of users: {e}")
        sys.exit(1)
    
    print(f"Successfully created {count} users")
    return users

def generate_restaurants(count=20):
    """Generate restaurant data"""
    print(f"Generating {count} restaurants...")
    
    for i in range(count):
        name = restaurant_names[i % len(restaurant_names)]
        if i >= len(restaurant_names):
            name = f"{name} {i//len(restaurant_names) + 1}"
            
        location = random.choice(locations)
        selected_cuisines = random.sample([c.lower() for c in cuisines], random.randint(1, 3))
        cuisine_type = ", ".join(selected_cuisines)
        
        restaurant = Restaurant(
            name=name,
            location=location,
            cuisine_type=cuisine_type,
            price_range=random.randint(1, 4),
            rating=round(random.uniform(3.0, 5.0), 1)
        )
        db.session.add(restaurant)
    
    try:
        db.session.commit()
        print(f"Successfully created {count} restaurants")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating restaurants: {e}")
        sys.exit(1)

def create_matches(users, max_matches_per_user=5):
    """Create matches between users"""
    print("Creating matches between users...")
    user_ids = [user.id for user in users]
    
    # Track all created matches to avoid duplicates
    created_matches = set()
    
    for user in users:
        # For each match type (pending, matched, unmatched, blocked), we'll create a certain number
        # To simulate real app usage:
        # - 60% chance to create up to max_matches_per_user 'matched' relationships
        # - 80% chance to create up to max_matches_per_user 'pending' relationships (pending likes)
        # - 30% chance to create up to max_matches_per_user/3 'unmatched' relationships
        # - 20% chance to create up to max_matches_per_user/3 'blocked' relationships
        
        # 1. Create MATCHED relationships
        if random.random() < 0.6:
            num_matches = random.randint(0, max_matches_per_user)
            potential_matches = [uid for uid in user_ids if uid != user.id and (min(user.id, uid), max(user.id, uid)) not in created_matches]
            
            num_matches = min(num_matches, len(potential_matches))
            if num_matches > 0:
                selected_matches = random.sample(potential_matches, num_matches)
                
                for match_id in selected_matches:
                    # Ensure user_id is always the smaller ID to avoid duplicates
                    user1_id = min(user.id, match_id)
                    user2_id = max(user.id, match_id)
                    
                    # Track this match to avoid duplicates
                    match_key = (user1_id, user2_id)
                    if match_key in created_matches:
                        continue
                    created_matches.add(match_key)
                    
                    match_date = datetime.now() - timedelta(days=random.randint(1, 30))
                    
                    # Create first direction (user1 to user2)
                    stmt = matches.insert().values(
                        user_id=user1_id,
                        matched_user_id=user2_id,
                        status='matched',
                        matched_date=match_date,
                        created_at=match_date
                    )
                    db.session.execute(stmt)
                    
                    # Create reverse direction (user2 to user1)
                    stmt = matches.insert().values(
                        user_id=user2_id,
                        matched_user_id=user1_id,
                        status='matched',
                        matched_date=match_date,
                        created_at=match_date
                    )
                    db.session.execute(stmt)
                    
                    # Create some messages for this match
                    if random.random() < 0.8:  # 80% chance of having messages
                        create_messages(user1_id, user2_id)
        
        # 2. Create PENDING relationships (pending matches)
        if random.random() < 0.8:
            num_likes = random.randint(0, max_matches_per_user)
            potential_likes = [uid for uid in user_ids if uid != user.id and (min(user.id, uid), max(user.id, uid)) not in created_matches]
            
            num_likes = min(num_likes, len(potential_likes))
            if num_likes > 0:
                selected_likes = random.sample(potential_likes, num_likes)
                
                for like_id in selected_likes:
                    match_key = (min(user.id, like_id), max(user.id, like_id))
                    if match_key in created_matches:
                        continue
                    created_matches.add(match_key)
                    
                    like_date = datetime.now() - timedelta(days=random.randint(1, 15))
                    
                    # Only create one direction - user likes other_user
                    stmt = matches.insert().values(
                        user_id=user.id,
                        matched_user_id=like_id,
                        status='pending',
                        created_at=like_date
                    )
                    db.session.execute(stmt)
        
        # 3. Create UNMATCHED relationships
        if random.random() < 0.3:
            num_unmatches = random.randint(0, max(1, max_matches_per_user // 3))
            potential_unmatches = [uid for uid in user_ids if uid != user.id and (min(user.id, uid), max(user.id, uid)) not in created_matches]
            
            num_unmatches = min(num_unmatches, len(potential_unmatches))
            if num_unmatches > 0:
                selected_unmatches = random.sample(potential_unmatches, num_unmatches)
                
                for unmatch_id in selected_unmatches:
                    match_key = (min(user.id, unmatch_id), max(user.id, unmatch_id))
                    if match_key in created_matches:
                        continue
                    created_matches.add(match_key)
                    
                    unmatch_date = datetime.now() - timedelta(days=random.randint(1, 20))
                    
                    # Only create one direction - user unmatched with other_user
                    stmt = matches.insert().values(
                        user_id=user.id,
                        matched_user_id=unmatch_id,
                        status='unmatched',
                        created_at=unmatch_date
                    )
                    db.session.execute(stmt)
        
        # 4. Create BLOCKED relationships
        if random.random() < 0.2:
            num_blocks = random.randint(0, max(1, max_matches_per_user // 3))
            potential_blocks = [uid for uid in user_ids if uid != user.id and (min(user.id, uid), max(user.id, uid)) not in created_matches]
            
            num_blocks = min(num_blocks, len(potential_blocks))
            if num_blocks > 0:
                selected_blocks = random.sample(potential_blocks, num_blocks)
                
                for block_id in selected_blocks:
                    match_key = (min(user.id, block_id), max(user.id, block_id))
                    if match_key in created_matches:
                        continue
                    created_matches.add(match_key)
                    
                    block_date = datetime.now() - timedelta(days=random.randint(1, 10))
                    
                    # Only create one direction - user blocks other_user
                    stmt = matches.insert().values(
                        user_id=user.id,
                        matched_user_id=block_id,
                        status='blocked',
                        created_at=block_date
                    )
                    db.session.execute(stmt)
    
    try:
        db.session.commit()
        print("Successfully created matches")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating matches: {e}")
        sys.exit(1)

def create_messages(user1_id, user2_id):
    """Create messages between two matched users"""
    # Import Message model locally to avoid circular import
    from controllers.messaging import Message
    
    # Generate between 1 and 10 messages
    num_messages = random.randint(1, 10)
    
    now = datetime.now()
    message_date = now - timedelta(days=random.randint(1, 30))
    
    starters = [
        "Hey, how's it going?", 
        "Hi there! What are you studying?",
        "Hello! Looking forward to lunch sometime!",
        "Hey! What kind of food do you like?",
        "Hi! What's your favorite restaurant around campus?"
    ]
    
    responses = [
        "I'm doing great, thanks for asking!",
        "I'm studying Computer Science. How about you?",
        "I'm looking forward to it too!",
        "I love Italian food! What about you?",
        "I really like the Thai place near campus."
    ]
    
    follow_ups = [
        "That sounds interesting! When are you free for lunch?",
        "Cool! Do you have any restaurant suggestions?",
        "Nice! What days work best for you usually?",
        "Great! Should we plan something for next week?",
        "Awesome! I'd love to try that place"
    ]
    
    # First message
    sender_id = random.choice([user1_id, user2_id])
    receiver_id = user2_id if sender_id == user1_id else user1_id
    
    first_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        content=random.choice(starters),
        created_at=message_date,
        is_read=True
    )
    db.session.add(first_message)
    
    # Remaining messages (alternate sender)
    for i in range(1, num_messages):
        # Alternate sender
        sender_id, receiver_id = receiver_id, sender_id
        
        # Increment message time
        message_date += timedelta(minutes=random.randint(5, 60))
        
        # Select message content based on position in conversation
        if i == 1:
            content = random.choice(responses)
        else:
            content = random.choice(follow_ups)
        
        # Create message
        message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            created_at=message_date,
            is_read=(random.random() < 0.9)  # 90% chance of being read
        )
        db.session.add(message)

def create_lunch_meetings(users, count=30):
    """Create lunch meetings between matched users"""
    print(f"Creating {count} lunch meetings...")
    
    # Get all restaurants
    restaurants = Restaurant.query.all()
    if not restaurants:
        print("No restaurants found. Skipping lunch meeting creation.")
        return
    
    # Get all matches
    all_matches = db.session.query(matches).all()
    if not all_matches:
        print("No matches found. Skipping lunch meeting creation.")
        return
    
    # Create lunch meetings
    for i in range(count):
        # Select a random match
        match = random.choice(all_matches)
        user1_id, user2_id = match.user_id, match.matched_user_id
        
        # Select a random restaurant
        restaurant = random.choice(restaurants)
        
        # Generate a random future date for the meeting (1-14 days in the future)
        meeting_date = datetime.now() + timedelta(days=random.randint(1, 14))
        meeting_hour = random.randint(11, 14)  # Between 11 AM and 2 PM
        meeting_time = meeting_date.replace(hour=meeting_hour, minute=0, second=0, microsecond=0)
        
        # Create meeting
        lunch_meeting = LunchMeeting(
            restaurant_id=restaurant.id,
            scheduled_time=meeting_time,
            status=random.choice(['scheduled', 'completed']),
            created_at=datetime.now() - timedelta(days=random.randint(1, 7))
        )
        db.session.add(lunch_meeting)
        db.session.flush()  # Get ID
        
        # Add participants
        participant1 = LunchMeetingParticipant(
            lunch_meeting_id=lunch_meeting.id,
            user_id=user1_id,
            status='confirmed',
            created_at=lunch_meeting.created_at
        )
        db.session.add(participant1)
        
        participant2 = LunchMeetingParticipant(
            lunch_meeting_id=lunch_meeting.id,
            user_id=user2_id,
            status='confirmed',
            created_at=lunch_meeting.created_at
        )
        db.session.add(participant2)
    
    try:
        db.session.commit()
        print(f"Successfully created {count} lunch meetings")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating lunch meetings: {e}")
        sys.exit(1)

def generate_conversation_starters(count=20):
    """Generate conversation starters for the app"""
    print(f"Generating {count} conversation starters...")
    
    starters = [
        {"question": "What's your favorite food on campus?", "category": "Food"},
        {"question": "If you could have lunch with any famous person, who would it be?", "category": "General"},
        {"question": "What's your go-to order at a coffee shop?", "category": "Food"},
        {"question": "What's the best restaurant you've discovered since coming to UB?", "category": "Food"},
        {"question": "Do you cook? What's your signature dish?", "category": "Food"},
        {"question": "What's the strangest food combination you actually enjoy?", "category": "Food"},
        {"question": "If you could eat only one cuisine for the rest of your life, what would it be?", "category": "Food"},
        {"question": "What food from home do you miss the most?", "category": "Food"},
        {"question": "What's your favorite comfort food during exam season?", "category": "Food"},
        {"question": "Do you have any food allergies or restrictions?", "category": "Food"},
        {"question": "Are you a breakfast person? What's your favorite breakfast?", "category": "Food"},
        {"question": "Sweet or savory breakfast?", "category": "Food"},
        {"question": "What's your stance on pineapple on pizza?", "category": "Food"},
        {"question": "What's a local restaurant you think everyone should try?", "category": "Food"},
        {"question": "Coffee or tea?", "category": "Food"},
        {"question": "What's the most unusual food you've ever tried?", "category": "Food"},
        {"question": "Do you have a favorite food truck on campus?", "category": "Food"},
        {"question": "What's your ideal dinner date spot?", "category": "Food"},
        {"question": "Are you a foodie? What's your favorite cuisine to explore?", "category": "Food"},
        {"question": "If you could master cooking one type of cuisine, what would it be?", "category": "Food"},
        {"question": "What's your major? Are you enjoying your classes?", "category": "Education"},
        {"question": "What made you choose UB for your studies?", "category": "Education"},
        {"question": "What's your favorite place to study on campus?", "category": "Education"},
        {"question": "What are your career plans after graduation?", "category": "Education"},
        {"question": "What's been your favorite class so far?", "category": "Education"}
    ]
    
    # Ensure we have enough unique starters
    if count > len(starters):
        count = len(starters)
    
    # Select random subset of starters
    selected_starters = random.sample(starters, count)
    
    for starter in selected_starters:
        cs = ConversationStarter(
            question=starter["question"],
            category=starter["category"],
            created_at=datetime.now()
        )
        db.session.add(cs)
    
    try:
        db.session.commit()
        print(f"Successfully created {count} conversation starters")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating conversation starters: {e}")
        sys.exit(1)

def generate_notifications(users, count=50):
    """Generate sample notifications for users"""
    print(f"Generating {count} notifications...")
    
    notification_types = [
        "match", "message", "lunch_invitation", "lunch_confirmation", "system"
    ]
    
    notification_messages = {
        "match": "You have a new match with {}!",
        "message": "You have a new message from {}!",
        "lunch_invitation": "{} invited you to lunch at {}!",
        "lunch_confirmation": "Your lunch with {} at {} is confirmed!",
        "system": "Welcome to LunchMate! Complete your profile to start matching."
    }
    
    for i in range(count):
        # Select a random user
        user = random.choice(users)
        
        # Select a notification type
        notification_type = random.choice(notification_types)
        
        # Generate notification content based on type
        if notification_type == "system":
            message = notification_messages[notification_type]
            related_user_id = None
        else:
            # Get another random user for the notification
            other_user = random.choice([u for u in users if u.id != user.id])
            other_name = f"{other_user.profile.first_name} {other_user.profile.last_name}"
            related_user_id = other_user.id
            
            if "lunch" in notification_type:
                restaurant = Restaurant.query.order_by(db.func.random()).first()
                message = notification_messages[notification_type].format(other_name, restaurant.name)
            else:
                message = notification_messages[notification_type].format(other_name)
        
        # Create the notification
        notification = Notification(
            user_id=user.id,
            notification_type=notification_type,
            message=message,
            related_user_id=related_user_id,
            is_read=random.choice([True, False]),
            created_at=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        db.session.add(notification)
    
    try:
        db.session.commit()
        print(f"Successfully created {count} notifications")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating notifications: {e}")
        sys.exit(1)

def populate_database(user_count=100, restaurant_count=20, meeting_count=30, 
                     starter_count=20, notification_count=50, max_matches=5, clear=True):
    """Main function to populate the database with sample data"""
    try:
        if clear:
            clear_database()
        
        users = generate_users(user_count)
        generate_restaurants(restaurant_count)
        create_matches(users, max_matches)
        create_lunch_meetings(users, meeting_count)
        generate_conversation_starters(starter_count)
        generate_notifications(users, notification_count)
        
        print("\nDatabase population completed successfully!")
        print(f"Generated {user_count} users, {restaurant_count} restaurants, and {meeting_count} lunch meetings.")
        print("All users have password: 12345678")
        
        # Show a sample user for testing
        sample_user = random.choice(users)
        print(f"\nSample user for testing:")
        print(f"Email: {sample_user.email}")
        print(f"Password: 12345678")
        print(f"Name: {sample_user.profile.first_name} {sample_user.profile.last_name}")
        
    except Exception as e:
        print(f"Error populating database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fill the LunchMate database with sample data')
    parser.add_argument('--users', type=int, default=100, help='Number of users to generate (default: 100)')
    parser.add_argument('--restaurants', type=int, default=20, help='Number of restaurants to generate (default: 20)')
    parser.add_argument('--meetings', type=int, default=30, help='Number of lunch meetings to generate (default: 30)')
    parser.add_argument('--starters', type=int, default=20, help='Number of conversation starters to generate (default: 20)')
    parser.add_argument('--notifications', type=int, default=50, help='Number of notifications to generate (default: 50)')
    parser.add_argument('--matches', type=int, default=5, help='Maximum number of matches per user (default: 5)')
    parser.add_argument('--no-clear', action='store_true', help='Do not clear the database before populating')
    args = parser.parse_args()
    
    # Create Flask app context
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        start_time = time_module.time()
        
        populate_database(
            user_count=args.users,
            restaurant_count=args.restaurants,
            meeting_count=args.meetings,
            starter_count=args.starters,
            notification_count=args.notifications,
            max_matches=args.matches,
            clear=not args.no_clear
        )
        
        end_time = time_module.time()
        print(f"Total execution time: {end_time - start_time:.2f} seconds") 