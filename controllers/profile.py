import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

from models.models import db, User, UserProfile, UserPhoto, LunchPreference, UserAvailability
from models.models import CuisinePreference, DietaryRestriction
from forms.profile_forms import ProfileForm, PhotoUploadForm, PreferencesForm, AvailabilityForm

profile = Blueprint('profile', __name__, url_prefix='/profile')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@profile.route('/')
@login_required
def view_profile():
    return render_template('profile/view.html', 
                           user=current_user, 
                           profile=current_user.profile,
                           photos=current_user.photos,
                           preferences=current_user.lunch_preferences,
                           availabilities=current_user.availability)

@profile.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user.profile)
    
    if form.validate_on_submit():
        current_user.profile.first_name = form.first_name.data
        current_user.profile.last_name = form.last_name.data
        current_user.profile.university = form.university.data
        current_user.profile.department = form.department.data
        current_user.profile.bio = form.bio.data
        current_user.profile.graduation_year = form.graduation_year.data
        current_user.profile.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile.view_profile'))
    
    return render_template('profile/edit.html', form=form)

@profile.route('/photos', methods=['GET', 'POST'])
@login_required
def manage_photos():
    form = PhotoUploadForm()
    
    if form.validate_on_submit():
        file = form.photo.data
        if file and allowed_file(file.filename):
            # Create a unique filename
            filename = secure_filename(file.filename)
            filename = f"{uuid.uuid4().hex}_{filename}"
            
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Create photo record
            is_primary = False
            if not len(current_user.photos):
                is_primary = True
            
            photo = UserPhoto(user_id=current_user.id, 
                             photo_path=f"images/uploads/{filename}",
                             is_primary=is_primary)
            
            db.session.add(photo)
            db.session.commit()
            
            flash('Photo uploaded successfully.', 'success')
            return redirect(url_for('profile.manage_photos'))
        else:
            flash('Invalid file type. Please upload a PNG, JPG, JPEG, or GIF.', 'danger')
    
    return render_template('profile/photos.html', form=form, photos=current_user.photos)

@profile.route('/photos/set_primary/<int:photo_id>', methods=['POST'])
@login_required
def set_primary_photo(photo_id):
    photo = UserPhoto.query.get_or_404(photo_id)
    
    # Ensure photo belongs to current user
    if photo.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('profile.manage_photos'))
    
    # Reset all photos to non-primary
    for p in current_user.photos:
        p.is_primary = False
    
    # Set selected photo as primary
    photo.is_primary = True
    db.session.commit()
    
    flash('Primary photo updated.', 'success')
    return redirect(url_for('profile.manage_photos'))

@profile.route('/photos/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = UserPhoto.query.get_or_404(photo_id)
    
    # Ensure photo belongs to current user
    if photo.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('profile.manage_photos'))
    
    # If deleting primary photo, set another as primary if available
    if photo.is_primary and len(current_user.photos) > 1:
        next_photo = UserPhoto.query.filter(UserPhoto.user_id == current_user.id, 
                                          UserPhoto.id != photo.id).first()
        if next_photo:
            next_photo.is_primary = True
    
    # Delete photo file
    file_path = os.path.join(current_app.root_path, 'static', photo.photo_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    db.session.delete(photo)
    db.session.commit()
    
    flash('Photo deleted.', 'success')
    return redirect(url_for('profile.manage_photos'))

@profile.route('/preferences', methods=['GET', 'POST'])
@login_required
def manage_preferences():
    # Get or create preferences using a join to reduce queries
    preferences = db.session.query(LunchPreference).\
        outerjoin(CuisinePreference).\
        outerjoin(DietaryRestriction).\
        filter(LunchPreference.user_id == current_user.id).\
        first()
    
    if not preferences:
        preferences = LunchPreference(user_id=current_user.id)
        db.session.add(preferences)
        db.session.commit()
    
    form = PreferencesForm(obj=preferences)
    
    if form.validate_on_submit():
        # Update basic preferences
        preferences.max_budget = form.max_budget.data
        preferences.preferred_group_size = form.preferred_group_size.data
        preferences.updated_at = datetime.utcnow()
        
        # Update cuisine preferences
        cuisines = [cuisine.strip() for cuisine in form.cuisine_preferences.data.split(',')] if form.cuisine_preferences.data else []
        
        # Get all current cuisine preferences in a single query
        existing_cuisines = db.session.query(CuisinePreference).\
            filter(CuisinePreference.lunch_preference_id == preferences.id).\
            all()
        
        # Create a set of existing cuisine types for faster lookups
        existing_cuisine_types = {c.cuisine_type for c in existing_cuisines}
        
        # Add new cuisines
        for cuisine in cuisines:
            if cuisine not in existing_cuisine_types:
                new_cuisine = CuisinePreference(
                    lunch_preference_id=preferences.id,
                    cuisine_type=cuisine
                )
                db.session.add(new_cuisine)
        
        # Remove cuisines that were unchecked
        for cuisine_pref in existing_cuisines:
            if cuisine_pref.cuisine_type not in cuisines:
                db.session.delete(cuisine_pref)
        
        # Update dietary restrictions
        restrictions = [restriction.strip() for restriction in form.dietary_restrictions.data.split(',')] if form.dietary_restrictions.data else []
        
        # Delete all existing dietary restrictions
        db.session.query(DietaryRestriction).\
            filter(DietaryRestriction.lunch_preference_id == preferences.id).\
            delete()
        
        # Add new restrictions
        for restriction in restrictions:
            if restriction:  # Skip empty strings
                new_restriction = DietaryRestriction(
                    lunch_preference_id=preferences.id,
                    restriction_type=restriction
                )
                db.session.add(new_restriction)
        
        db.session.commit()
        flash('Your lunch preferences have been updated.', 'success')
        return redirect(url_for('profile.view_profile'))
    
    # Get current selections for the form
    if preferences.cuisine_preferences:
        form.cuisine_preferences.data = ', '.join([cp.cuisine_type for cp in preferences.cuisine_preferences])
    
    if preferences.dietary_restrictions:
        form.dietary_restrictions.data = ', '.join([dr.restriction_type for dr in preferences.dietary_restrictions])
    
    return render_template('profile/preferences.html', form=form, preferences=preferences)

@profile.route('/availability', methods=['GET', 'POST'])
@login_required
def manage_availability():
    form = AvailabilityForm()
    
    if form.validate_on_submit():
        # Check if availability already exists for this time
        exists = UserAvailability.query.filter_by(
            user_id=current_user.id,
            day_of_week=form.day_of_week.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        ).first()
        
        if exists:
            flash('This availability slot already exists.', 'warning')
        else:
            availability = UserAvailability(
                user_id=current_user.id,
                day_of_week=form.day_of_week.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data
            )
            
            db.session.add(availability)
            db.session.commit()
            flash('Availability added.', 'success')
        
        return redirect(url_for('profile.manage_availability'))
    
    availabilities = UserAvailability.query.filter_by(user_id=current_user.id).order_by(
        UserAvailability.day_of_week, UserAvailability.start_time).all()
    
    return render_template('profile/availability.html', form=form, availabilities=availabilities)

@profile.route('/availability/delete/<int:availability_id>', methods=['POST'])
@login_required
def delete_availability(availability_id):
    availability = UserAvailability.query.get_or_404(availability_id)
    
    # Ensure availability belongs to current user
    if availability.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('profile.manage_availability'))
    
    db.session.delete(availability)
    db.session.commit()
    
    flash('Availability deleted.', 'success')
    return redirect(url_for('profile.manage_availability')) 