from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    profile_pic = db.Column(db.String(255))
    # postsリレーションシップはAttendancePostモデルが定義された後に追加

    def __repr__(self):
        return f'<User {self.name}>'

class AttendancePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(255), nullable=False) # Google Calendar Event ID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_name = db.Column(db.String(255), nullable=False) # 投稿者名
    status = db.Column(db.String(50), nullable=False)  # 出席, 欠席, 未定
    comment = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('posts', lazy='dynamic'))

    def __repr__(self):
        return f'<AttendancePost {self.user_name} - {self.event_id} - {self.status}>'
