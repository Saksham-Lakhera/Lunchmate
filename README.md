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

## Database Insertion

1. Create the database 'lunchapp' (or any other name)
2. Run 'python script/fill_db.py' and it will fill the database with all the required value.

## Running the App
Execute the command
 ```
   python app.py
   ```
