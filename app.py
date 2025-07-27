from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from model import db, User, Task, Message
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from dateutil.parser import parse
from sqlalchemy import func
import uuid

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='your_email@gmail.com',        # Replace with your email
    MAIL_PASSWORD='your_email_password'          # Replace with your password
)

# Init
db.init_app(app)
mail = Mail(app)
login = LoginManager(app)
login.login_view = 'login'
s = URLSafeTimedSerializer(app.secret_key)

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# ------------------ Reminder System ------------------
def send_reminders():
    tomorrow = datetime.utcnow() + timedelta(days=1)
    tasks = Task.query.filter(
        Task.due != None,
        func.date(Task.due) == tomorrow.date(),
        Task.reminder_sent == False
    ).all()

    for t in tasks:
        user = User.query.get(t.user_id)
        msg = Message(
            subject="Task Reminder",
            sender=app.config['MAIL_USERNAME'],
            recipients=[user.username],  # Sends to user's registered email
            body=f"Reminder: '{t.content}' is due on {t.due.strftime('%Y-%m-%d')}"
        )
        try:
            mail.send(msg)
            t.reminder_sent = True
            db.session.commit()
        except Exception as e:
            print(f"Failed to send reminder: {e}")

# ------------------ Routes ------------------
@app.route('/')
@login_required
def index():
    send_reminders()
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due.asc().nullsfirst()).all()
    return render_template('index.html', tasks=tasks)

@app.route('/calendar')
@login_required
def calendar_view():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('calendar.html', tasks=tasks)

@app.route('/kanban')
@login_required
def kanban_view():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template('kanban.html', tasks=tasks)

@app.route('/add', methods=['POST'])
@login_required
def add():
    txt = request.form.get('content', '').strip()
    due_raw = request.form.get('due', '')
    try:
        dt = parse(due_raw) if due_raw else None
    except:
        dt = None

    repeat = ','.join(request.form.getlist('repeat_days'))
    prio = int(request.form.get('priority', 3))
    cat = request.form.get('category', 'Personal')

    if txt:
        t = Task(
            user_id=current_user.id,
            content=txt,
            due=dt,
            repeat_days=repeat,
            priority=prio,
            category=cat
        )
        db.session.add(t)
        db.session.commit()
    return redirect(url_for('index'))

# ✅ REPLACED SHARE ROUTE
@app.route('/share/<uuid>', methods=['GET', 'POST'])
@login_required
def share(uuid):
    task = Task.query.filter_by(share_uuid=uuid).first_or_404()

    if request.method == 'POST':
        email = request.form.get('email')
        phone = request.form.get('phone')
        share_link = url_for('shared', uuid=uuid, _external=True)

        if email:
            try:
                msg = Message(
                    subject="Shared Task",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[email],
                    body=f"A task was shared with you:\n\n{task.content}\n\nView it here: {share_link}"
                )
                mail.send(msg)
                flash('Task shared via email!')
            except Exception as e:
                flash(f'Failed to send email: {e}')
        elif phone:
            # Optional: integrate SMS (like Twilio) here
            flash(f"Task link ready to send via SMS manually: {share_link}")
        else:
            flash('Please enter an email or phone number.')

    return render_template('share_form.html', task=task)

@app.route('/shared/<uuid>')
def shared(uuid):
    t = Task.query.filter_by(share_uuid=uuid).first_or_404()
    return render_template('shared_task.html', task=t)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    t = Task.query.get_or_404(id)
    if t.user_id == current_user.id:
        db.session.delete(t)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msgs = Message.query.order_by(Message.created.desc()).limit(10).all()
    if request.method == 'POST':
        u = request.form['username']
        pw = request.form['password']
        msgt = request.form.get('message', '').strip()

        if User.query.filter_by(username=u).first():
            return 'User exists'

        usr = User(username=u, password=generate_password_hash(pw))
        db.session.add(usr)

        if msgt:
            db.session.flush()  # Ensure usr.id is available
            db.session.add(Message(user_id=usr.id, username=u, text=msgt))

        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html', messages=msgs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usr = User.query.filter_by(username=request.form['username']).first()
        if usr and check_password_hash(usr.password, request.form['password']):
            login_user(usr)
            return redirect(url_for('index'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(username=email).first()
        if user:
            token = s.dumps(email, salt='reset')
            link = url_for('reset_password', token=token, _external=True)
            msg = Message(
                subject="Reset Your Password",
                sender=app.config['MAIL_USERNAME'],
                recipients=[email],
                body=f'Click to reset your password: {link}'
            )
            mail.send(msg)
            flash('Reset link sent!')
        else:
            flash('Email not found.')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='reset', max_age=3600)
    except:
        return 'Token expired or invalid.'
    if request.method == 'POST':
        new_password = request.form['password']
        user = User.query.filter_by(username=email).first()
        user.password = generate_password_hash(new_password)
        db.session.commit()
        flash('Password updated.')
        return redirect(url_for('login'))
    return render_template('reset_password.html')

# ------------------ Run App ------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
