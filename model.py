
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User:
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.created_at = datetime.utcnow()
        self.profile_picture = None
        self.bio = ""
        self.trust_level = "bronze"
        self.campaigns = []
        self.donations = []

    @staticmethod
    def verify_password(password_hash, password):
        return check_password_hash(password_hash, password) 
