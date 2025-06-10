from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, account_id):
        self.id = account_id
