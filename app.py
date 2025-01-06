from flask import Flask, render_template, redirect, url_for, request, flash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message

app = Flask(__name__, template_folder='pages')

# Add configurations
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'support@flexme.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'
app.config['MAIL_DEFAULT_SENDER'] = 'support@flexme.com'
app.config['SECRET_KEY'] = 'your-secret-key'

mail = Mail(app)

# Mock database
campaigns_db = {
    1: {
        'title': 'New Laptop for College',
        'category': 'Education',
        'creator_name': 'John Doe',
        'start_date': '2024-01-15',
        'description': 'I need help purchasing a laptop for my computer science degree...',
        'amount_raised': 750,
        'goal_amount': 1000,
        'days_left': 15,
        'progress_percentage': 75,
        'top_contributors': [
            {'name': 'Anonymous', 'amount': 250},
            {'name': 'Jane Smith', 'amount': 200},
            {'name': 'Bob Wilson', 'amount': 150}
        ]
    },
    2: {
        'title': 'Emergency Medical Treatment',
        'category': 'Medical',
        'creator_name': 'Sarah Johnson',
        'start_date': '2024-02-01',
        'description': 'Urgent medical procedure needed...',
        'amount_raised': 2500,
        'goal_amount': 5000,
        'days_left': 10,
        'progress_percentage': 50,
        'top_contributors': [
            {'name': 'Anonymous', 'amount': 1000},
            {'name': 'Mike Brown', 'amount': 800},
            {'name': 'Lisa Davis', 'amount': 500}
        ]
    },
    3: {
        'title': 'Small Business Startup',
        'category': 'Business',
        'creator_name': 'Emily Chen',
        'start_date': '2024-01-20',
        'description': 'Help me start my dream bakery...',
        'amount_raised': 3000,
        'goal_amount': 10000,
        'days_left': 25,
        'progress_percentage': 30,
        'top_contributors': [
            {'name': 'David Wilson', 'amount': 1500},
            {'name': 'Anonymous', 'amount': 1000},
            {'name': 'Maria Garcia', 'amount': 500}
        ]
    },
    4: {
        'title': 'Home Repair After Storm',
        'category': 'Emergency',
        'creator_name': 'Tom Anderson',
        'start_date': '2024-02-05',
        'description': 'Need help repairing roof damage...',
        'amount_raised': 4000,
        'goal_amount': 6000,
        'days_left': 5,
        'progress_percentage': 66,
        'top_contributors': [
            {'name': 'Community Fund', 'amount': 2000},
            {'name': 'Anonymous', 'amount': 1200},
            {'name': 'James Wilson', 'amount': 800}
        ]
    },
    5: {
        'title': 'School Supplies for Kids',
        'category': 'Education',
        'creator_name': 'Mary Williams',
        'start_date': '2024-01-25',
        'description': 'Help provide supplies for underprivileged students...',
        'amount_raised': 1200,
        'goal_amount': 2000,
        'days_left': 20,
        'progress_percentage': 60,
        'top_contributors': [
            {'name': 'Local Business', 'amount': 500},
            {'name': 'Anonymous', 'amount': 400},
            {'name': 'Teacher Group', 'amount': 300}
        ]
    }
}

@app.route('/')
def index():
    return render_template('base.html')

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
                'type': 'contribution',
                'icon': 'fas fa-hand-holding-heart',
                'title': 'New Contribution',
                'message': 'John Doe contributed €50 to your campaign!',
                'time': '1 day ago'
            }
        ]
    }
    return render_template('notifications.html', **notifications_data)

@app.route('/profile')
def profile():
    return render_template('userprofile.html')

@app.route('/profile/edit')
def edit_profile():
    return render_template('editprofile.html')

@app.route('/profile/update', methods=['POST'])
def update_profile():
    return redirect(url_for('profile'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            msg = Message(
                'New Contact Form Submission',
                recipients=['support@flexme.com']
            )
            msg.body = f"""
            Name: {request.form.get('name')}
            Email: {request.form.get('email')}
            Message: {request.form.get('message')}
            """
            mail.send(msg)
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

@app.route('/dashboard')
def dashboard():
    # Get all campaigns for display
    active_campaigns = {
        k: v for k, v in campaigns_db.items() 
        if v['days_left'] > 0
    }
    
    # Calculate some stats for the dashboard
    total_raised = sum(c['amount_raised'] for c in campaigns_db.values())
    total_campaigns = len(campaigns_db)
    active_count = len(active_campaigns)
    
    dashboard_data = {
        'stats': {
            'total_raised': total_raised,
            'total_campaigns': total_campaigns,
            'active_campaigns': active_count,
            'success_rate': int((total_raised / sum(c['goal_amount'] for c in campaigns_db.values())) * 100)
        },
        'active_campaigns': active_campaigns
    }
    
    return render_template('dashboard.html', **dashboard_data)

@app.route('/campaigns')
def campaigns():
    return render_template('campaigns.html', campaigns=campaigns_db)

@app.route('/campaign/<int:campaign_id>')
def campaign_detail(campaign_id):
    campaign = campaigns_db.get(campaign_id)
    if campaign is None:
        return "Campaign not found", 404
    return render_template('campaign_detail.html', **campaign)

if __name__ == '__main__':
    app.run(debug=True)
