from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, IntegerField, SelectField, FloatField, TimeField, SubmitField
from wtforms import SelectMultipleField, widgets
from wtforms.validators import DataRequired, Optional, NumberRange, Length
from datetime import datetime

class ProfileForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    university = StringField('University', validators=[DataRequired()])
    department = StringField('Department', validators=[Optional()])
    bio = TextAreaField('About Me', validators=[Optional(), Length(max=500)])
    graduation_year = IntegerField('Graduation Year', validators=[Optional(), NumberRange(min=datetime.now().year, max=datetime.now().year + 10)])
    submit = SubmitField('Update Profile')

class PhotoUploadForm(FlaskForm):
    photo = FileField('Upload Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])
    submit = SubmitField('Upload')

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class PreferencesForm(FlaskForm):
    cuisine_preferences = StringField('Cuisine Preferences', validators=[Optional()],
                                      description='Enter cuisines separated by commas (e.g., Italian, Chinese, Mexican)')
    dietary_restrictions = StringField('Dietary Restrictions', validators=[Optional()],
                                       description='Enter dietary restrictions separated by commas (e.g., Vegan, Gluten Free)')
    max_budget = FloatField('Maximum Budget ($)', validators=[Optional(), NumberRange(min=0)])
    preferred_group_size = SelectField('Preferred Group Size', 
                                      choices=[(1, 'One-on-one'), (2, 'Small group (3-4)'), (3, 'Large group (5+)')],
                                      coerce=int,
                                      validators=[DataRequired()])
    submit = SubmitField('Update Preferences')

class AvailabilityForm(FlaskForm):
    day_of_week = SelectField('Day of Week', 
                             choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), 
                                     (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')],
                             coerce=int,
                             validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    submit = SubmitField('Add Availability') 