from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, abort
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='pages')

# Add this function to calculate time ago
def time_ago(date):
    now = datetime.now()
    diff = now - date

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    if diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    if diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    return "just now"

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

# Add this with your other mock data at the top
MOCK_PURCHASES = [
    {
        'id': 1,
        'campaign_title': 'Help Sarah Fight Cancer',
        'amount': 50.00,
        'date': '2024-03-15',
        'status': 'completed',
        'recipient': 'Sarah Johnson',
        'receipt_id': 'RCP-001-2024',
        'category': 'medical',
        'impact': 'Medical Treatment Support'
    },
    {
        'id': 2,
        'campaign_title': 'College Fund for James',
        'amount': 100.00,
        'date': '2024-03-10',
        'status': 'completed',
        'recipient': 'James Wilson',
        'receipt_id': 'RCP-002-2024',
        'category': 'education',
        'impact': 'Education Support'
    },
    {
        'id': 3,
        'campaign_title': 'Local Animal Shelter Support',
        'amount': 25.00,
        'date': '2024-03-05',
        'status': 'completed',
        'recipient': 'City Animal Shelter',
        'receipt_id': 'RCP-003-2024',
        'category': 'animals',
        'impact': 'Animal Care'
    }
]

# Add these configurations to your app
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'support@flexme.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'your-app-password'  # Replace with your app password
app.config['MAIL_DEFAULT_SENDER'] = 'support@flexme.com'
app.config['SECRET_KEY'] = 'your-secret-key'  # Required for flash messages

mail = Mail(app)

SUPPORT_LEVELS = {
    'BRONZE': {'quota': 5, 'description': 'New User'},
    'SILVER': {'quota': 10, 'description': 'Basic User'},
    'GOLD': {'quota': 15, 'description': 'Regular User'},
    'PLATINUM': {'quota': 20, 'description': 'Trusted User'},
    'DIAMOND': {'quota': 25, 'description': 'Advanced User/Business'}
}

@app.route('/')
@app.route('/dashboard')
def dashboard():
    # Get recent/live campaigns for dashboard (urgent ones)
    live_campaigns = [
        {
            "id": campaign['id'],
            "user_initial": campaign['user_initial'],
            "name": campaign['name'],
            "time": campaign['time'],
            "need": campaign['description'][:100] + "...",  # Truncate description
            "amount_raised": "{:,}".format(campaign['amount_raised']),
            "goal_amount": "{:,}".format(campaign['goal_amount']),
            "progress": campaign['progress']
        }
        for campaign in MOCK_CAMPAIGNS
        if campaign.get('is_urgent', False)  # Only show urgent campaigns in live feed
    ][:3]  # Limit to 3 most recent

    return render_template('dashboard.html', 
                         help_requests=live_campaigns,
                         user_level='GOLD',
                         support_quota=15)

@app.route('/notifications')
def notifications():
    notifications_data = {
        'notifications': [
            {
                'id': 1,
                'type': 'campaigns',
                'icon': 'fas fa-bullhorn',
                'title': 'Campaign Update',
                'message': 'Your campaign "New Laptop" has reached 75% of its goal!',
                'time': '2 hours ago'
            },
            {
                'id': 2,
                'type': 'help',
                'icon': 'fas fa-hand-holding-heart',
                'title': 'Help Request',
                'message': 'Sarah needs help with €200 for an iPhone repair',
                'time': '3 hours ago'
            },
            {
                'id': 3,
                'type': 'system',
                'icon': 'fas fa-cog',
                'title': 'System Update',
                'message': 'Your account has been verified successfully',
                'time': '1 day ago'
            }
        ]
    }
    return render_template('notifications.html', **notifications_data)

@app.route('/profile')
def profile():
    # Mock check for profile ownership (replace with actual authentication logic)
    is_owner = True  # This would normally check if the logged-in user matches the profile being viewed
    return render_template('userprofile.html', 
                         purchases=MOCK_PURCHASES,
                         is_owner=is_owner)

@app.route('/profile/<username>')  # Add this route for viewing other users' profiles
def view_profile(username):
    is_owner = False  # This would normally check if the logged-in user matches the username
    return render_template('userprofile.html',
                         purchases=None,  # Don't pass purchases data for other users
                         is_owner=is_owner)

@app.route('/profile/edit')
def edit_profile():
    return render_template('editprofile.html')

@app.route('/profile/update', methods=['POST'])
def update_profile():
    # Here you would handle the form submission and update the user's profile
    # For now, just redirect back to the profile page
    return redirect(url_for('profile'))

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
                recipients=['support@flexme.com'],
                body=f"""
                New message from {name} ({email}):
                
                Subject: {subject}
                Message:
                {message}
                """,
                # Add reply-to header so you can reply directly to the sender
                reply_to=email
            )

            # Send email
            mail.send(msg)

            # Send confirmation email to user
            confirm_msg = Message(
                subject='Thank you for contacting FlexMe',
                recipients=[email],
                body=f"""
                Dear {name},

                Thank you for contacting FlexMe. We have received your message and will get back to you shortly.

                Your message details:
                Subject: {subject}
                Message:
                {message}

                Best regards,
                The FlexMe Team
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
    # Add your logout logic here (clear session, etc.)
    return redirect(url_for('home'))

@app.route('/campaigns')
def campaigns():
    # Get filter parameters
    category = request.args.get('category', 'all')
    amount_range = request.args.get('amount', 'all')
    sort = request.args.get('sort', 'newest')
    
    # Start with all campaigns
    filtered_campaigns = MOCK_CAMPAIGNS.copy()
    
    # Apply category filter
    if category != 'all':
        filtered_campaigns = [c for c in filtered_campaigns if c['category'].lower() == category.lower()]
    
    # Apply amount filter
    if amount_range != 'all':
        if amount_range == '10000+':
            filtered_campaigns = [c for c in filtered_campaigns if c['amount_raised'] >= 10000]
        else:
            min_amount, max_amount = map(int, amount_range.split('-'))
            filtered_campaigns = [c for c in filtered_campaigns 
                                if min_amount <= c['amount_raised'] <= max_amount]
    
    # Apply sorting
    if sort == 'newest':
        filtered_campaigns = sorted(filtered_campaigns, key=lambda x: x['start_date'], reverse=True)
    elif sort == 'oldest':
        filtered_campaigns = sorted(filtered_campaigns, key=lambda x: x['start_date'])
    elif sort == 'most-funded':
        filtered_campaigns = sorted(filtered_campaigns, key=lambda x: x['progress'], reverse=True)
    elif sort == 'least-funded':
        filtered_campaigns = sorted(filtered_campaigns, key=lambda x: x['progress'])
    elif sort == 'most-urgent':
        filtered_campaigns = sorted(filtered_campaigns, key=lambda x: x['days_left'])
    
    return render_template('campaigns.html', 
                         campaigns=filtered_campaigns,
                         current_category=category)

@app.template_filter('format_datetime')
def format_datetime(value):
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d')
    return value.strftime('%B %d, %Y at %I:%M %p')

@app.template_filter('time_ago')
def time_ago_filter(date):
    return time_ago(date)

@app.route('/campaign/<int:campaign_id>')
def campaign_detail(campaign_id):
    # Find the campaign with matching ID
    campaign = next(
        (campaign for campaign in MOCK_CAMPAIGNS if campaign['id'] == campaign_id),
        None
    )
    
    if campaign is None:
        abort(404)
    
    # Prepare campaign data for template
    campaign_data = {
        'campaign_id': campaign_id,
        'category': campaign['category'],
        'campaign_title': campaign['title'],
        'creator_name': campaign['name'],
        'start_date': campaign['start_date'].strftime('%B %d, %Y'),
        'days_left': campaign['days_left'],
        'description': campaign['description'],
        'amount_raised': campaign['amount_raised'],
        'goal_amount': campaign['goal_amount'],
        'progress_percentage': campaign['progress']
    }
    
    return render_template('campaign_detail.html', **campaign_data)

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
    query = request.args.get('query', '').lower().strip()
    search_results = []
    
    if query:
        for campaign in MOCK_CAMPAIGNS:
            if (query in campaign['title'].lower() or 
                query in campaign['description'].lower() or 
                query in campaign['category'].lower()):
                search_results.append(campaign)
    
    return render_template('search.html', 
                         results=search_results, 
                         query=query)

@app.route('/payment/<int:campaign_id>')
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

@app.route('/create-campaign', methods=['GET', 'POST'])
def create_campaign():
    if request.method == 'POST':
        # Handle form submission (to be implemented)
        # This would typically save to a database
        return redirect(url_for('campaigns'))
    
    return render_template('create_campaign.html')

@app.route('/purchases')
def purchases():
    # Calculate total amount donated
    total_donated = sum(purchase['amount'] for purchase in MOCK_PURCHASES)
    
    return render_template('purchases.html', 
                         purchases=MOCK_PURCHASES,
                         total_donated=total_donated)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    print("Server is running at: http://0.0.0.0:5000")  # Add this line to verify
