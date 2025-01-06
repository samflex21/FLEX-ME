from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort, session, make_response, send_file # type: ignore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message # type: ignore
from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient # type: ignore
from pymongo.server_api import ServerApi # type: ignore
import certifi # type: ignore
from flask import session, flash
from models import User
from functools import wraps
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from bson import Binary  # Add this import at the top
from flask_pymongo import PyMongo

import logging
import ssl
import os
from werkzeug.utils import secure_filename
import time
import stripe
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)

try:
    # Create a new client and connect to the server
    client = MongoClient(
        "mongodb+srv://whoelsebutv:X39QyOa45NHNWOxc@project.dexlu.mongodb.net/",
        server_api=ServerApi('1'),
        tlsCAFile=certifi.where()
    )
    
    # Send a ping to confirm a successful connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
    
    # connect to database lifeline
    db = client['lifeline']
    campaign_collection = db['campaigns']
    users_collection = db['users']
    
    # Create a new collection for profile pictures
    profile_pictures_collection = db['users_profile_pictures']
    
    # Add this to your MongoDB collections
    notifications_collection = db['notifications']
    
    def setup_mongodb_indexes():
        try:
            # Create unique index for username
            users_collection.create_index(
                [("username", 1)],
                unique=True,
                name="username_unique_index"
            )
            print("Username index created successfully")

            # Create unique index for email
            users_collection.create_index(
                [("email", 1)],
                unique=True,
                name="email_unique_index"
            )
            print("Email index created successfully")

        except Exception as e:
            print(f"Error creating indexes: {e}")

    # Set up indexes when the application starts
    setup_mongodb_indexes()
    
except Exception as e:
    print(f"Error connecting to MongoDB Atlas: {e}")
    # Initialize these to None so the app can still start even if DB connection fails
    client = None
    db = None
    campaign_collection = None
    users_collection = None

app = Flask(__name__, template_folder='pages')

# Add after app initialization
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
app.permanent_session_lifetime = timedelta(days=7)

# Add these configurations
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_pictures')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# MongoDB Configuration
app.config["MONGO_URI"] = "mongodb+srv://whoelsebutv:X39QyOa45NHNWOxc@project.dexlu.mongodb.net/lifeline?retryWrites=true&w=majority"
mongo = PyMongo(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add this function to calculate time ago
def time_ago(date):
    if not date:
        return "unknown time"
        
    try:
        now = datetime.now()
        diff = now - date

        # For seconds
        if diff.total_seconds() < 60:
            return "just now"
            
        # For minutes
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} min{'s' if minutes != 1 else ''} ago"
            
        # For hours
        elif diff.total_seconds() < 86400:  # 24 hours
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
            
        # For days
        elif diff.days < 30:
            return f"{diff.days} d{'s' if diff.days != 1 else ''} ago"
            
        # For months
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} mon{'s' if months != 1 else ''} ago"
            
        # For years
        else:
            years = diff.days // 365
            return f"{years} yr{'s' if years != 1 else ''} ago"
            
    except Exception as e:
        print(f"Error calculating time ago: {str(e)}")
        return "unknown time"

# Create base datetime for consistent sample data
base_date = datetime.now()

# Centralized mock database for campaigns
MOCK_CAMPAIGNS = [
    {
        'id': 1,
        'user_initial': 'S',
        'name': 'Sarah Johnson',
        'time': '2m ago',
        'title': 'Help Sarah Fight Cancer',
        'category': 'medical',
        'amount_raised': 15000,
        'goal_amount': 20000,
        'progress': 75,
        'description': 'Sarah needs our help to fund her cancer treatment. Every contribution brings hope for recovery.',
        'location': 'New York, NY',
        'supporters': 128,
        'days_left': 15,
        'start_date': base_date - timedelta(days=3),
        'is_featured': True,
        'is_urgent': True
    },
    {
        'id': 2,
        'user_initial': 'J',
        'name': 'James Wilson',
        'time': '5m ago',
        'title': 'College Fund for James',
        'category': 'education',
        'amount_raised': 3000,
        'goal_amount': 5000,
        'progress': 60,
        'description': 'Help James achieve his dream of attending medical school. Your support shapes the future of healthcare.',
        'location': 'Los Angeles, CA',
        'supporters': 45,
        'days_left': 25,
        'start_date': base_date - timedelta(days=1),
        'is_featured': False,
        'is_urgent': True
    },
    {
        'id': 3,
        'user_initial': 'E',
        'name': 'Emma Thompson',
        'time': '10m ago',
        'title': 'Emergency House Fire Recovery',
        'category': 'emergency',
        'amount_raised': 8500,
        'goal_amount': 10000,
        'progress': 85,
        'description': 'Lost everything in a devastating house fire. Need support to rebuild and recover essential items.',
        'location': 'Chicago, IL',
        'supporters': 93,
        'days_left': 5,
        'start_date': base_date - timedelta(hours=12),
        'is_featured': True,
        'is_urgent': True
    },
    {
        'id': 4,
        'user_initial': 'M',
        'name': 'Mike Brown',
        'time': '1h ago',
        'title': 'Local Bakery Startup',
        'category': 'business',
        'amount_raised': 12000,
        'goal_amount': 15000,
        'progress': 80,
        'description': 'Help launch a community bakery providing job opportunities and fresh bread to local neighborhoods.',
        'location': 'Seattle, WA',
        'supporters': 156,
        'days_left': 20,
        'start_date': base_date - timedelta(days=5),
        'is_featured': True,
        'is_urgent': False
    },
    {
        'id': 5,
        'user_initial': 'L',
        'name': 'Lisa Chen',
        'time': '3h ago',
        'title': 'Special Needs Education Support',
        'category': 'education',
        'amount_raised': 4500,
        'goal_amount': 6000,
        'progress': 75,
        'description': 'Raising funds for specialized educational equipment for children with special needs.',
        'location': 'Boston, MA',
        'supporters': 67,
        'days_left': 30,
        'start_date': base_date - timedelta(days=2),
        'is_featured': False,
        'is_urgent': False
    },
    {
        'id': 6,
        'user_initial': 'R',
        'name': 'Robert Martinez',
        'time': '4h ago',
        'title': 'Emergency Surgery Fund',
        'category': 'medical',
        'amount_raised': 9500,
        'goal_amount': 12000,
        'progress': 79,
        'description': 'Urgent funding needed for life-saving surgery. Time is critical, and every donation helps.',
        'location': 'Miami, FL',
        'supporters': 112,
        'days_left': 3,
        'start_date': base_date - timedelta(hours=6),
        'is_featured': True,
        'is_urgent': True
    },
    {
        'id': 7,
        'user_initial': 'K',
        'name': 'Kevin Park',
        'time': '6h ago',
        'title': 'Tech Startup Innovation Fund',
        'category': 'business',
        'amount_raised': 18000,
        'goal_amount': 25000,
        'progress': 72,
        'description': 'Developing innovative software solutions for small businesses. Help us create jobs in tech.',
        'location': 'San Francisco, CA',
        'supporters': 89,
        'days_left': 45,
        'start_date': base_date - timedelta(days=7),
        'is_featured': True,
        'is_urgent': False
    },
    {
        'id': 8,
        'user_initial': 'A',
        'name': 'Amanda White',
        'time': '12h ago',
        'title': 'Hurricane Recovery Aid',
        'category': 'emergency',
        'amount_raised': 25000,
        'goal_amount': 30000,
        'progress': 83,
        'description': 'Supporting community recovery efforts after devastating hurricane damage.',
        'location': 'Houston, TX',
        'supporters': 245,
        'days_left': 10,
        'start_date': base_date - timedelta(days=4),
        'is_featured': True,
        'is_urgent': True
    }
]



# Add these configurations to your app
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'support@lifeline.com'  # Changed from 'support@flexme.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
app.config['MAIL_DEFAULT_SENDER'] = 'support@lifeline.com'  # Changed from 'support@flexme.com'
app.config['SECRET_KEY'] = 'your-secret-key'  # Required for flash messages

mail = Mail(app)

SUPPORT_LEVELS = {
    'BRONZE': {'quota': 10, 'description': 'New User'},
    'SILVER': {'quota': 15, 'description': 'Basic User'},
    'GOLD': {'quota': 20, 'description': 'Regular User'},
    'PLATINUM': {'quota': 25, 'description': 'Trusted User'},
    'DIAMOND': {'quota': 30, 'description': 'Advanced User/Business'}
}

# Add these to your existing MongoDB connection
db = client['lifeline']
users_collection = db['users']

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Add this function to calculate support quota based on trust level
def get_support_quota(trust_level):
    quotas = {
        'BRONZE': 10,
        'SILVER': 15,
        'GOLD': 20,
        'PLATINUM': 25,
        'DIAMOND': 30
    }
    return quotas.get(trust_level.upper(), 10)  # Default to 10% if trust level not found

@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get the 5 most recent campaigns
        recent_campaigns = list(campaign_collection.find().sort('created_at', -1).limit(5))
        
        # Get user data
        user = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        
        # Calculate support quota based on trust level
        trust_level = user.get('trust_level', 'BRONZE')
        support_quota = get_support_quota(trust_level)
        
        # Process campaigns and add user information
        for campaign in recent_campaigns:
            campaign['id'] = str(campaign['_id'])
            # Get campaign creator's information
            campaign_user = users_collection.find_one({'_id': campaign['user_id']})
            if campaign_user:
                campaign['username'] = campaign_user.get('username', 'Unknown User')
                campaign['user_id'] = str(campaign_user['_id'])
                # Check if user has profile picture
                campaign['user_has_profile_picture'] = profile_pictures_collection.find_one(
                    {'user_id': campaign_user['_id']}
                ) is not None
            
            progress = min(round((float(campaign.get('amount_raised', 0)) / float(campaign.get('goal_amount', 1))) * 100, 1), 100)
            campaign['progress'] = progress
            created_at = campaign.get('created_at', datetime.now())
            campaign['time'] = time_ago(created_at)

        # Create stats dictionary
        stats = {
            'support_quota': support_quota,
            'people_helped': user.get('people_helped', 0),
            'trust_level': trust_level
        }

        return render_template('dashboard.html', 
                             recent_campaigns=recent_campaigns,
                             stats=stats)
                             
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('home'))

@app.route('/notifications')
def notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Get user's notifications
        notifications = list(notifications_collection.find(
            {'user_id': ObjectId(session['user_id'])}
        ).sort('created_at', -1))

        # Format dates and add icons
        for notification in notifications:
            notification['created_at'] = notification['created_at'].strftime('%B %d, %Y %I:%M %p')
            # Set default icon if none exists
            if 'icon' not in notification:
                notification['icon'] = 'fa-bell'

        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        print(f"Error loading notifications: {str(e)}")
        flash('Error loading notifications', 'error')
        return redirect(url_for('dashboard'))

@app.route('/mark_notification_read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        notifications_collection.update_one(
            {'_id': ObjectId(notification_id)},
            {'$set': {'read': True}}
        )
        return redirect(url_for('notifications'))
    except Exception as e:
        print(f"Error marking notification as read: {str(e)}")
        flash('Error updating notification', 'error')
        return redirect(url_for('notifications'))

@app.route('/profile')
def profile():
    # Just render the viewinguserprofile.html template
    return render_template('viewinguserprofile.html',
                         user={
                             'username': 'username',
                             'first_name': 'First',
                             'last_name': 'Last',
                             'has_profile_picture': False,
                             'trust_level': 'GOLD'
                         },
                         campaigns=[],
                         current_time=datetime.now().timestamp())

@app.route('/profile/<username>')
def view_user_profile(username):
    try:
        # Get user data from database
        user = users_collection.find_one({'username': username})
        
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('dashboard'))

        # Debug print
        print(f"Found user: {user['username']}")

        # Get user's campaigns
        campaigns = list(campaign_collection.find({
            'user_id': ObjectId(user['_id'])
        }).sort('created_at', -1))

        # Debug print
        print(f"Found {len(campaigns)} campaigns for user")

        # Process campaigns
        processed_campaigns = []
        for campaign in campaigns:
            try:
                processed_campaign = {
                    'id': str(campaign['_id']),
                    'title': campaign.get('title', 'Untitled Campaign'),
                    'description': campaign.get('description', ''),
                    'amount_raised': float(campaign.get('amount_raised', 0)),
                    'goal_amount': float(campaign.get('goal_amount', 0)),
                    'created_at': campaign.get('created_at', datetime.now()),
                    'status': campaign.get('status', 'active'),
                    'progress': 0
                }
                
                # Calculate progress
                if processed_campaign['goal_amount'] > 0:
                    progress = (processed_campaign['amount_raised'] / processed_campaign['goal_amount']) * 100
                    processed_campaign['progress'] = min(round(progress, 1), 100)
                
                processed_campaigns.append(processed_campaign)
                
            except Exception as e:
                print(f"Error processing campaign {campaign.get('_id')}: {str(e)}")
                continue

        # Debug print
        print(f"Processed {len(processed_campaigns)} campaigns successfully")

        # Add user info needed for template
        user_data = {
            '_id': str(user['_id']),
            'username': user['username'],
            'first_name': user.get('first_name', ''),
            'last_name': user.get('last_name', ''),
            'bio': user.get('bio', ''),
            'trust_level': user.get('trust_level', 'BRONZE'),
            'has_profile_picture': user.get('has_profile_picture', False)
        }

        return render_template('viewinguserprofile.html',
                             user=user_data,
                             campaigns=processed_campaigns,
                             current_time=datetime.now().timestamp())

    except Exception as e:
        print(f"Error in view_user_profile: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('dashboard'))

@app.route('/edit_profile')
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get user data and provide default values for missing fields
    user_data = users_collection.find_one({'_id': ObjectId(session['user_id'])})
    
    # Create a user dictionary with default values
    user = {
        'first_name': user_data.get('first_name', ''),
        'last_name': user_data.get('last_name', ''),
        'username': user_data.get('username', ''),
        'email': user_data.get('email', ''),
        'bio': user_data.get('bio', ''),
        'location': user_data.get('location', ''),
        'phone': user_data.get('phone', ''),
        'profile_picture': user_data.get('profile_picture', None),
        'trust_level': user_data.get('trust_level', 'Bronze')
    }

    return render_template('editprofile.html', user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        user_id = session['user_id']
        
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and file.filename and allowed_file(file.filename):
                # Read the file content
                file_content = file.read()
                
                # Debug print
                print(f"Uploading profile picture for user {user_id}")
                
                # Create profile picture document
                profile_pic_data = {
                    'user_id': ObjectId(user_id),
                    'filename': secure_filename(file.filename),
                    'content_type': file.content_type,
                    'data': Binary(file_content),
                    'uploaded_at': datetime.utcnow()
                }
                
                # Store in MongoDB
                result = profile_pictures_collection.update_one(
                    {'user_id': ObjectId(user_id)},
                    {'$set': profile_pic_data},
                    upsert=True
                )
                
                # Debug print
                print(f"Profile picture upload result: {result.modified_count} modified, {result.upserted_id} upserted")
                
                # Update user's profile picture status in users collection
                users_collection.update_one(
                    {'_id': ObjectId(user_id)},
                    {'$set': {'has_profile_picture': True}}
                )
                
                # Update session
                session['has_profile_picture'] = True
                
                # Debug print
                print(f"Session updated: {session}")

        # Update other user information
        update_data = {
            'first_name': request.form.get('first_name', ''),
            'last_name': request.form.get('last_name', ''),
            'username': request.form.get('username', ''),
            'email': request.form.get('email', ''),
            'bio': request.form.get('bio', ''),
            'location': request.form.get('location', ''),
            'phone': request.form.get('phone', '')
        }

        # Update the database
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )

        # Update session data
        session['username'] = update_data['username']

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('userprofile'))

    except Exception as e:
        print(f"Error in update_profile: {str(e)}")
        flash(f'Error updating profile: {str(e)}', 'error')
        return redirect(url_for('edit_profile'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('name')
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')

            # Create email message
            msg = Message(
                subject=f'New Contact Form Submission: {subject}',
                recipients=['support@lifeline.com'],  # Changed from 'support@flexme.com'
                body=f"""
                New message from {name} ({email}):
                
                Subject: {subject}
                Message:
                {message}
                """,
                reply_to=email
            )

            # Send email
            mail.send(msg)

            # Send confirmation email to user
            confirm_msg = Message(
                subject='Thank you for contacting Lifeline',  # Changed from 'Thank you for contacting FlexMe'
                recipients=[email],
                body=f"""
                Dear {name},

                Thank you for contacting Lifeline. We have received your message and will get back to you shortly.

                Your message details:
                Subject: {subject}
                Message:
                {message}

                Best regards,
                The Lifeline Team
                """
            )
            mail.send(confirm_msg)

            flash('Your message has been sent successfully!', 'success')
            return redirect(url_for('contact'))

        except Exception as e:
            print(f"Error sending email: {e}")
            flash('Sorry, there was an error sending your message. Please try again later.', 'error')
            return redirect(url_for('contact'))

    return render_template('contactus.html')

@app.route('/shipping')
def shipping():
    return render_template('shipping.html')

@app.route('/about')
def about():
    return render_template('aboutus.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/campaigns')
def campaigns():
    try:
        # Debug: Print MongoDB connection info
        print("MongoDB URI:", app.config["MONGO_URI"])
        
        # Debug: Try to list all campaigns first
        all_campaigns = list(mongo.db.campaigns.find())
        print(f"Total campaigns in database: {len(all_campaigns)}")
        
        # Get filter parameters
        category = request.args.get('category', 'all')
        amount_range = request.args.get('amount', 'all')
        sort = request.args.get('sort', 'newest')
        
        print(f"Filters - Category: {category}, Amount: {amount_range}, Sort: {sort}")

        # Build query
        query = {}
        if category != 'all':
            query['category'] = category.lower()

        # Handle amount range filter
        if amount_range != 'all':
            if amount_range == '10000+':
                query['goal_amount'] = {'$gte': 10000}
            else:
                min_amount, max_amount = map(float, amount_range.split('-'))
                query['goal_amount'] = {'$gte': min_amount, '$lte': max_amount}

        print(f"MongoDB Query: {query}")

        # Get filtered campaigns from MongoDB
        campaigns = list(mongo.db.campaigns.find(query))
        print(f"Found {len(campaigns)} campaigns after filtering")

        # Debug: Print each campaign
        for campaign in campaigns:
            print(f"Campaign ID: {campaign.get('_id')}, Title: {campaign.get('title')}")

        # Process each campaign
        processed_campaigns = []
        for campaign in campaigns:
            try:
                processed_campaign = {
                    'id': str(campaign['_id']),
                    'title': campaign.get('title', 'Untitled Campaign'),
                    'category': campaign.get('category', 'other'),
                    'amount_raised': float(campaign.get('amount_raised', 0)),
                    'goal_amount': float(campaign.get('goal_amount', 0)),
                    'name': campaign.get('name', 'Anonymous'),
                    'description': campaign.get('description', ''),
                    'created_at': campaign.get('created_at', datetime.now())
                }

                # Calculate progress
                try:
                    progress = (processed_campaign['amount_raised'] / processed_campaign['goal_amount']) * 100
                    processed_campaign['progress'] = min(round(progress, 1), 100)
                except (ZeroDivisionError, KeyError):
                    processed_campaign['progress'] = 0

                # Format time
                time_diff = datetime.now() - processed_campaign['created_at']
                if time_diff.days == 0:
                    processed_campaign['time'] = 'Today'
                elif time_diff.days == 1:
                    processed_campaign['time'] = 'Yesterday'
                else:
                    processed_campaign['time'] = f"{time_diff.days} days ago"

                processed_campaigns.append(processed_campaign)
                print(f"Processed campaign: {processed_campaign['title']}")

            except Exception as e:
                print(f"Error processing campaign {campaign.get('_id')}: {str(e)}")
                continue

        # Apply sorting
        if sort == 'oldest':
            processed_campaigns.sort(key=lambda x: x['created_at'])
        elif sort == 'most-funded':
            processed_campaigns.sort(key=lambda x: x['progress'], reverse=True)
        elif sort == 'least-funded':
            processed_campaigns.sort(key=lambda x: x['progress'])
        elif sort == 'most-urgent':
            processed_campaigns.sort(key=lambda x: x.get('days_left', float('inf')))
        else:  # newest
            processed_campaigns.sort(key=lambda x: x['created_at'], reverse=True)

        print(f"Final number of campaigns to display: {len(processed_campaigns)}")
        return render_template('campaigns.html', campaigns=processed_campaigns)

    except Exception as e:
        print(f"Error in campaigns route: {str(e)}")
        import traceback
        traceback.print_exc()
        return render_template('campaigns.html', campaigns=[])

def format_time_ago(timestamp):
    try:
        now = datetime.utcnow()
        diff = now - timestamp

        if diff.days > 7:
            return timestamp.strftime('%B %d, %Y')
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "just now"
    except Exception as e:
        print(f"Error formatting time: {str(e)}")
        return "time error"

@app.template_filter('format_datetime')
def format_datetime(value):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')
    return value.strftime('%B %d, %Y at %I:%M %p')

@app.template_filter('time_ago')
def time_ago_filter(date):
    return time_ago(date)

@app.route('/campaign/<campaign_id>')
def campaign_detail(campaign_id):
    try:
        # Find the campaign in MongoDB
        campaign = campaign_collection.find_one({'_id': ObjectId(campaign_id)})
        
        if not campaign:
            flash('Campaign not found', 'error')
            return redirect(url_for('dashboard'))
        
        # Get the creator's username
        creator = users_collection.find_one({'_id': ObjectId(campaign['user_id'])})
        campaign['username'] = creator['username'] if creator else 'Unknown'
        
        # Handle the creation date (start_date)
        start_date = campaign.get('created_at')
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        campaign['start_date'] = start_date.strftime('%B %d, %Y')
        
        # Handle the deadline
        deadline = campaign.get('deadline')
        if isinstance(deadline, str):
            deadline = datetime.strptime(deadline, '%Y-%m-%d')
        
        current_date = datetime.now()
        days_left = (deadline - current_date).days
        campaign['days_left'] = max(0, days_left)
        
        # Add the campaign id as a string
        campaign['id'] = str(campaign['_id'])
        
        # Calculate progress
        if campaign.get('goal_amount', 0) > 0:
            progress = (float(campaign.get('amount_raised', 0)) / float(campaign.get('goal_amount'))) * 100
            campaign['progress'] = min(round(progress, 1), 100)
        else:
            campaign['progress'] = 0

        return render_template('campaign_detail.html', 
                            campaign=campaign,
                            current_date=current_date)
                            
    except Exception as e:
        print(f"Error in campaign detail: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('dashboard'))

@app.route('/search/autocomplete')
def search_autocomplete():
    query = request.args.get('query', '').lower().strip()
    suggestions = []
    
    if query:
        for campaign in MOCK_CAMPAIGNS:
            if query in campaign['title'].lower():
                suggestions.append({
                    'title': campaign['title'],
                    'category': campaign['category']
                })
            if len(suggestions) >= 5:  # Limit to 5 suggestions
                break
                
    return jsonify(suggestions)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    print(f"Search query received: '{query}'")  # Debug log
    
    if query:
        try:
            # Get MongoDB collection
            db = client['lifeline']
            campaign_collection = db['campaigns']
            
            # Print total documents for debugging
            total_docs = campaign_collection.count_documents({})
            print(f"Total documents in collection: {total_docs}")
            
            # Create search pattern
            search_pattern = re.compile(query, re.IGNORECASE)
            
            # Search query
            search_query = {
                '$or': [
                    {'title': {'$regex': search_pattern}},
                    {'description': {'$regex': search_pattern}},
                    {'category': {'$regex': search_pattern}},
                    {'name': {'$regex': search_pattern}}
                ]
            }
            
            # Execute search
            mongo_results = list(campaign_collection.find(search_query))
            print(f"Found {len(mongo_results)} results for query: '{query}'")
            
            # Process results
            results = []
            for campaign in mongo_results:
                try:
                    # Calculate progress
                    amount_raised = float(campaign.get('amount_raised', 0))
                    goal_amount = float(campaign.get('goal_amount', 1))
                    progress = int((amount_raised / goal_amount) * 100) if goal_amount > 0 else 0
                    
                    processed_campaign = {
                        'id': str(campaign['_id']),
                        'title': campaign.get('title', ''),
                        'description': campaign.get('description', ''),
                        'category': campaign.get('category', ''),
                        'name': campaign.get('name', ''),
                        'amount_raised': amount_raised,
                        'goal_amount': goal_amount,
                        'progress': progress,
                        'days_left': campaign.get('days_left', 30)
                    }
                    results.append(processed_campaign)
                    print(f"Processed campaign: {processed_campaign['title']}")  # Debug log
                    
                except Exception as e:
                    print(f"Error processing campaign {campaign.get('_id')}: {str(e)}")
                    continue
            
            return render_template('search.html', 
                                query=query, 
                                results=results)
            
        except Exception as e:
            print(f"Search error: {str(e)}")
            flash('An error occurred while searching', 'error')
            return render_template('search.html', query=query, results=[])
    
    return render_template('search.html', query=query, results=[])

@app.route('/payment/<string:campaign_id>')
def payment(campaign_id):
    # Get campaign details
    campaign = next(
        (campaign for campaign in MOCK_CAMPAIGNS if campaign['id'] == campaign_id),
        None
    )
    
    if campaign is None:
        abort(404)
    
    # Get pre-selected amount if any
    amount = request.args.get('amount', None)
    
    return render_template('payment.html', 
                         campaign=campaign,
                         preselected_amount=amount)

@app.route('/create_campaign', methods=['GET', 'POST'])
@login_required
def create_campaign():
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title')
            category = request.form.get('category')
            goal = float(request.form.get('goal'))
            deadline = request.form.get('deadline')
            description = request.form.get('description')
            location = request.form.get('location')

            # Handle image upload
            image_filename = None
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    image_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

            # Get current user
            user = users_collection.find_one({'_id': ObjectId(session['user_id'])})

            # Create campaign document
            campaign = {
                'user_id': ObjectId(session['user_id']),
                'name': f"{user['first_name']} {user['last_name']}",
                'title': title,
                'category': category,
                'goal_amount': goal,
                'deadline': deadline,
                'description': description,
                'location': location,
                'image': image_filename,
                'amount_raised': 0,
                'progress': 0,
                'created_at': datetime.utcnow(),
                'status': 'active',
                'supporters': []
            }

            # Insert into MongoDB
            result = campaign_collection.insert_one(campaign)

            if result.inserted_id:
                flash('Campaign created successfully!', 'success')
                return redirect(url_for('campaign_detail', campaign_id=str(result.inserted_id)))
            else:
                flash('Error creating campaign', 'error')

        except Exception as e:
            print(f"Error creating campaign: {str(e)}")
            flash('Error creating campaign', 'error')

        return redirect(url_for('create_campaign'))

    return render_template('create_campaign.html')

@app.route('/purchases')
def purchases():
    # Calculate total amount donated
    total_donated = sum(purchase['amount'] for purchase in MOCK_PURCHASES)
    
    return render_template('purchases.html', 
                         purchases=MOCK_PURCHASES,
                         total_donated=total_donated)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate passwords match
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        if users_collection.find_one({'$or': [{'username': username}, {'email': email}]}):
            flash('Username or email already exists', 'error')
            return redirect(url_for('signup'))
        
        # Create new user
        new_user = User(username, email, password)
        user_data = {
            'username': new_user.username,
            'email': new_user.email,
            'password_hash': new_user.password_hash,
            'created_at': new_user.created_at,
            'profile_picture': new_user.profile_picture,
            'bio': new_user.bio,
            'trust_level': new_user.trust_level,
            'campaigns': new_user.campaigns,
            'donations': new_user.donations
        }
        
        try:
            users_collection.insert_one(user_data)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('An error occurred during registration.', 'error')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            # Find user by username instead of email
            user = users_collection.find_one({'username': username})
            
            # Check if user exists and password matches
            if user and check_password_hash(user['password_hash'], password):
                # Set session variables
                session['user_id'] = str(user['_id'])
                session['username'] = user.get('username', '')
                session['has_profile_picture'] = user.get('has_profile_picture', False)
                
                # Create welcome notification
                welcome_notification = {
                    'user_id': ObjectId(user['_id']),
                    'message': f"Welcome back, {user.get('username', '')}! We're glad to see you.",
                    'created_at': datetime.utcnow(),
                    'read': False,
                    'icon': 'fa-star',
                    'type': 'welcome'
                }
                
                # Insert notification
                notifications_collection.insert_one(welcome_notification)
                
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')
        
        return redirect(url_for('login'))

    return render_template('login.html')

# Add this route to check if user is logged in
@app.route('/check_session')
def check_session():
    return jsonify({
        'logged_in': 'user_id' in session,
        'session_data': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'email': session.get('email')
        }
    })

def check_database_structure():
    try:
        # List all collections
        collections = db.list_collection_names()
        print("\nCurrent collections in database 'project':")
        for collection in collections:
            print(f"- {collection}")
            
        # Check indexes for users collection
        print("\nIndexes in users collection:")
        indexes = users_collection.list_indexes()
        for index in indexes:
            print(f"Index: {index['name']}, Key: {index['key']}")
            
    except Exception as e:
        print(f"Error checking database structure: {e}")

# Call this after your MongoDB connection setup
check_database_structure()

@app.route('/api/signup', methods=['POST'])
def api_signup():
    try:
        data = request.get_json()
        print("Received signup data:", data)  # Debug print
        
        # Extract data from request
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        first_name = data.get('firstName')
        last_name = data.get('lastName')
        phone = data.get('phone')
        
        # Print the MongoDB connection status
        print("MongoDB connection status:", client.server_info())  # Debug print
        
        # Create user document
        user_data = {
            'firstName': first_name,
            'lastName': last_name,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'phone': phone,
            'created_at': datetime.now(),
            'profile_picture': '',
            'bio': '',
            'trust_level': 'BRONZE',
            'campaigns': [],
            'donations': [],
            'last_login': datetime.now(),
            'is_active': True,
            'settings': {
                'notifications': True,
                'privacy': 'public'
            }
        }
        
        print("Attempting to insert user:", user_data)  # Debug print
        
        # Insert into MongoDB
        result = users_collection.insert_one(user_data)
        
        print("Insert result:", result.inserted_id)  # Debug print
        
        if result.inserted_id:
            return jsonify({
                'message': 'Registration successful',
                'user_id': str(result.inserted_id)
            }), 200
        else:
            return jsonify({'message': 'Failed to create user'}), 500
            
    except Exception as e:
        print(f"Error during signup: {e}")  # Debug print
        return jsonify({'message': 'An error occurred during registration'}), 500

@app.route('/userprofile')
def userprofile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        # Get user data from database
        user_data = users_collection.find_one({'_id': ObjectId(session['user_id'])})
        
        if not user_data:
            flash('User not found', 'error')
            return redirect(url_for('login'))

        # Fetch user's campaigns from campaign collection
        user_campaigns = list(campaign_collection.find({
            'user_id': ObjectId(session['user_id'])
        }).sort('created_at', -1))  # Sort by creation date, newest first

        # Process campaigns and separate active from completed
        active_campaigns = []
        completed_campaigns = []

        for campaign in user_campaigns:
            # Add formatted time
            campaign['time'] = time_ago(campaign.get('created_at', datetime.now()))
            # Ensure amount_raised is a float
            campaign['amount_raised'] = float(campaign.get('amount_raised', 0))
            campaign['goal_amount'] = float(campaign.get('goal_amount', 0))
            
            # Categorize campaigns
            if campaign.get('status') == 'completed':
                completed_campaigns.append(campaign)
            else:
                active_campaigns.append(campaign)

        # Check if user has profile picture
        has_profile_picture = profile_pictures_collection.find_one({'user_id': ObjectId(session['user_id'])}) is not None
        
        # Create user dictionary with default values and add campaigns
        user = {
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username', ''),
            'email': user_data.get('email', ''),
            'bio': user_data.get('bio', ''),
            'location': user_data.get('location', ''),
            'phone': user_data.get('phone', ''),
            'has_profile_picture': has_profile_picture,
            'trust_level': user_data.get('trust_level', 'Bronze'),
            'campaigns': user_campaigns,  # All campaigns
            'active_campaigns': active_campaigns,
            'completed_campaigns': completed_campaigns
        }

        # Update session with profile picture status
        session['has_profile_picture'] = has_profile_picture
        
        # Debug print
        print(f"Found {len(active_campaigns)} active and {len(completed_campaigns)} completed campaigns")

        return render_template('userprofile.html',
                             user=user,
                             is_owner=True)

    except Exception as e:
        print(f"Error in userprofile: {str(e)}")
        flash('Error loading profile', 'error')
        return redirect(url_for('dashboard'))

@app.route('/check_users')
def check_users():
    try:
        users = list(users_collection.find())
        return jsonify({
            'user_count': len(users),
            'users': [{
                'username': user['username'],
                'email': user['email'],
                'firstName': user['firstName'],
                'lastName': user['lastName'],
                'trust_level': user['trust_level']
            } for user in users]
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Test the connection
try:
    client.admin.command('ping')
    print("MongoDB connection successful!")
except Exception as e:
    print("MongoDB connection failed:", e)

# Add this route to check if data is being stored
@app.route('/check_mongodb')
def check_mongodb():
    try:
        # Count users
        user_count = users_collection.count_documents({})
        # Get all users (limit to 10 for safety)
        users = list(users_collection.find().limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for user in users:
            user['_id'] = str(user['_id'])
            # Remove password hash for security
            if 'password_hash' in user:
                del user['password_hash']
        
        return jsonify({
            'connection': 'successful',
            'database': 'lifeline',
            'collection': 'users',
            'user_count': user_count,
            'sample_users': users
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# Add this new route to debug session data
@app.route('/debug_session')
def debug_session():
    if 'user_id' in session:
        return jsonify({
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'profile_picture': session.get('profile_picture')
        })
    return jsonify({'error': 'Not logged in'})

# Add a new route to serve profile pictures
@app.route('/profile_picture/<user_id>')
def get_profile_picture(user_id):
    try:
        print(f"Fetching profile picture for user {user_id}")
        
        profile_pic = profile_pictures_collection.find_one({'user_id': ObjectId(user_id)})
        
        if profile_pic and 'data' in profile_pic:
            print(f"Found profile picture with content type: {profile_pic['content_type']}")
            
            response = make_response(profile_pic['data'])
            response.headers.set('Content-Type', profile_pic['content_type'])
            response.headers.set('Cache-Control', 'no-cache')
            return response
        else:
            print("No profile picture found")
            # Make sure this path exists in your project
            return send_file('static/images/default_profile.png', mimetype='image/png')
    except Exception as e:
        print(f"Error serving profile picture: {str(e)}")
        # Make sure this path exists in your project
        return send_file('static/images/default_profile.png', mimetype='image/png')

@app.context_processor
def utility_processor():
    return {'current_time': datetime.now().timestamp()}

# Add this context processor to provide notification count to all templates
@app.context_processor
def notification_processor():
    if 'user_id' in session:
        try:
            count = notifications_collection.count_documents({
                'user_id': ObjectId(session['user_id']),
                'read': False
            })
            return {'notification_count': count}
        except Exception as e:
            print(f"Error counting notifications: {str(e)}")
            return {'notification_count': 0}
    return {'notification_count': 0}

# Helper function to format currency
@app.template_filter('currency')
def currency_filter(value):
    try:
        return "${:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return "$0.00"

@app.route('/donate/<campaign_id>', methods=['GET', 'POST'])
def donate(campaign_id):
    try:
        # Fetch campaign details from database
        campaign = campaign_collection.find_one({'_id': ObjectId(campaign_id)})
        
        if not campaign:
            flash('Campaign not found', 'error')
            return redirect(url_for('dashboard'))

        # Process campaign data
        processed_campaign = {
            'id': str(campaign['_id']),
            'title': campaign['title'],
            'name': campaign.get('name', 'Unknown Creator'),
            'amount_raised': float(campaign.get('amount_raised', 0)),
            'goal_amount': float(campaign.get('goal_amount', 0)),
            'progress': int((float(campaign.get('amount_raised', 0)) / float(campaign.get('goal_amount', 1))) * 100)
        }

        # Add console log to check if key is being passed
        print(f"Stripe Public Key: {app.config['STRIPE_PUBLIC_KEY']}")

        return render_template('payment.html', 
                             campaign=processed_campaign,
                             stripe_public_key=app.config['STRIPE_PUBLIC_KEY'])

    except Exception as e:
        print(f"Error in donate: {str(e)}")
        flash('Error processing donation', 'error')
        return redirect(url_for('dashboard'))

# Initialize Stripe with your secret key
stripe.api_key = 'your_stripe_secret_key'
STRIPE_PUBLIC_KEY = 'your_stripe_publishable_key'

@app.route('/create-payment-intent', methods=['POST'])
def create_payment_intent():
    try:
        data = request.json
        amount = data.get('amount', 10)
        
        # Create a PaymentIntent with the order amount and currency
        intent = stripe.PaymentIntent.create(
            amount=int(float(amount) * 100),  # Convert to cents
            currency='eur',
            automatic_payment_methods={
                'enabled': True,
            }
        )
        
        print(f"Created payment intent: {intent.id}")  # Debug log
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
        
    except Exception as e:
        print(f"Error creating payment intent: {str(e)}")
        return jsonify({'error': str(e)}), 403

@app.route('/payment-success')
def payment_success():
    payment_intent_id = request.args.get('payment_intent')
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    
    if payment_intent.status == 'succeeded':
        # Update your database here
        flash('Payment successful! Thank you for your donation.', 'success')
    else:
        flash('Payment failed. Please try again.', 'error')
    
    return redirect(url_for('dashboard'))

# Make sure these are set near the top of your file
app.config['STRIPE_PUBLIC_KEY'] = 'pk_test_...'  # Your actual publishable key
app.config['STRIPE_SECRET_KEY'] = 'sk_test_...'  # Your actual secret key
stripe.api_key = app.config['STRIPE_SECRET_KEY']

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    print("Server is running at: http://0.0.0.0:5000")  # Add this line to verify
