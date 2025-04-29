# LunchMate: Social Lunch Matching App for University Students

LunchMate is a web application that helps university students connect with other students for lunch meetups. It provides a platform similar to Tinder but focused on lunch meetings instead of dating.

## Features

- User authentication (register, login, logout)
- Profile management (personal information, photos, lunch preferences)
- Availability scheduling
- Matching system (like Tinder)
- Real-time messaging between matched users
- Restaurant recommendations
- Conversation starters based on user interests
- Common availability display for easy scheduling

## Database Schema

The application uses a relational database with the following tables:

- Users: Stores user authentication information
- UserProfiles: Stores detailed user information
- UserPhotos: Stores user profile photos
- LunchPreferences: Stores user preferences for lunch
- CuisinePreference: Stores individual cuisine preferences for users (one-to-many with LunchPreferences)
- DietaryRestriction: Stores individual dietary restrictions for users (one-to-many with LunchPreferences)
- UserAvailability: Stores user availability for lunch
- Matches: Manages connections between users
- Messages: Stores conversations between matched users
- Restaurants: Stores information about restaurants
- LunchMeetings: Tracks scheduled lunch meetings

## Technologies Used

- Backend: Flask (Python)
- Database: SQLAlchemy ORM with SQLite (can be configured for MySQL/PostgreSQL)
- Frontend: HTML, CSS, JavaScript, Bootstrap 5
- Authentication: Flask-Login
- Form Handling: Flask-WTF

## Setup and Installation

1. Clone the repository
   ```
   git clone <repository-url>
   cd lunchmate
   ```

2. Create and activate a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the dependencies
   ```
   pip install -r requirements.txt
   ```

4. Set environment variables (create a .env file in the project root)
   ```
   SECRET_KEY=your-secret-key
   DATABASE_URI=sqlite:///lunchmate.db
   ```

5. Initialize the database
   ```
   flask run
   ```
   (The database will be automatically created on first run)

6. Access the application
   ```
   http://localhost:5000
   ```

## Database Migration

If you're upgrading from a previous version, you'll need to migrate your database to the new normalized schema. We've converted LunchPreference from using comma-separated strings to a normalized schema with separate tables.

To run the migration:

1. First, ensure you have a backup of your database
   ```
   cp lunchmate.db lunchmate.db.backup
   ```

2. Run the migration script
   ```
   ./run_migration.sh
   ```
   
   This script will:
   - Create a timestamped backup of your database
   - Migrate data from old columns to new normalized tables
   - Remove the old columns from the database schema
   - Print a summary of the migration

For more details about the migration process, see [README_MIGRATION.md](README_MIGRATION.md).

## Project Structure

```
lunchmate/
├── app.py                 # Main application file
├── models/                # Database models
│   └── models.py          # SQLAlchemy models
├── controllers/           # Route controllers
│   ├── auth.py            # Authentication routes
│   ├── profile.py         # Profile management routes
│   ├── matching.py        # Matching system routes
│   └── messaging.py       # Messaging routes
├── forms/                 # Form definitions
│   ├── auth_forms.py      # Authentication forms
│   └── profile_forms.py   # Profile management forms
├── static/                # Static files
│   ├── css/               # CSS stylesheets
│   ├── js/                # JavaScript files
│   └── images/            # Image files
├── templates/             # HTML templates
│   ├── base.html          # Base template
│   ├── index.html         # Landing page
│   ├── auth/              # Authentication templates
│   ├── profile/           # Profile templates
│   ├── matching/          # Matching templates
│   └── messaging/         # Messaging templates
├── migrate_preferences.py # Migration script for preferences
├── alter_schema.py        # Schema alteration script
├── run_migration.sh       # Migration runner script
├── add_conversation_starters.py # Add conversation starters table and seed data
└── requirements.txt       # Python dependencies
```

## Future Enhancements

- Email verification for university emails
- AI-powered matching algorithm
- Group lunch scheduling
- Integration with campus dining systems
- Mobile app version
- Smarter conversation starters based on deeper user profiling

## Conversation Starters Feature

The app now includes AI-generated conversation starters to help users break the ice when messaging matches. These starters are:

1. Personalized based on user interests (food preferences, education, etc.)
2. Categorized by topic (Food, Education, Hobbies, General)
3. Easily accessible in the messaging interface
4. Displayed alongside common availability to facilitate scheduling

To add the conversation starters feature to your deployment:

1. Run the migration script
   ```
   python add_conversation_starters.py
   ```

2. Restart your application
   ```
   flask run
   ``` 