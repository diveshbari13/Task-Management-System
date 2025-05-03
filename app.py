from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///todo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key='your_secret_key'

db = SQLAlchemy(app)
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    date_joined = db.Column(db.DateTime, default=datetime.utcnow)
    dark_mode = db.Column(db.Boolean, default=False)

    tasks = db.relationship('Task', backref='user', lazy=True)

#  Database Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed=db.Column(db.Boolean, default=False)
    due_date=db.Column(db.DateTime, nullable=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    user=db.relationship('User',back_populates='tasks')
    priority= db.Column(db.String(10),default='Medium')

User.tasks=db.relationship('Task',back_populates='user')

# ️ Create database
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#  Home Route
@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    pending_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    high_priority = Task.query.filter_by(user_id=current_user.id, priority='High').count()
    if request.method == 'POST':
        task_content = request.form['task']
        priority= request.form['priority']
        due_date_str=request.form.get('due_date')
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None


        if task_content:
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None
            priority = request.form.get('priority', 'Medium')
            new_task = Task(content=task_content, due_date=due_date, priority=priority,user_id=current_user.id)

            db.session.add(new_task)
            db.session.commit()
        return redirect(url_for('home'))

    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date).all()
    now = datetime.now()
    return render_template('home.html', now=now, tasks=tasks, pending_tasks=pending_tasks,
                           completed_tasks=completed_tasks, high_priority=high_priority)


#  Delete Route
@app.route('/delete/<int:id>',methods=['POST'])
def delete(id):
    task_to_delete = Task.query.get_or_404(id)
    if task_to_delete.user_id==current_user.id:
        db.session.delete(task_to_delete)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/edit/<int:id>',methods=['GET','POST'])
def edit(id):
    pending_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    high_priority = Task.query.filter_by(user_id=current_user.id, priority='High').count()
    task=Task.query.get_or_404(id)
    if task.user_id!=current_user.id:
        flash("You do not have permission to edit this task",'danger')
        return redirect(url_for ('home'))

    if request.method=='POST':
        new_content=request.form['content']
        due_date_str = request.form.get('due_date')
        new_due_date = datetime.strptime(due_date_str, "%Y-%m-%d") if due_date_str else None
        task.priority = request.form.get('priority', 'Medium')
        if new_content:
            task.content=new_content
            task.due_date=new_due_date
            db.session.commit()
            return redirect(url_for('home'))

    return render_template('edit.html', task=task, pending_tasks=pending_tasks,completed_tasks=completed_tasks, high_priority=high_priority)


@app.route('/complete/<int:id>',methods=['POST'])
@login_required
def complete(id):
    task=Task.query.get_or_404(id)
    if task.user_id==current_user.id:
        task.completed= not task.completed
        db.session.commit()
    return redirect(url_for('home'))


@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        hashed_password=generate_password_hash(password)
        email = request.form["email"]

        if not email:
            flash("Email is required.", "danger")
            return redirect(url_for("register"))

        user_exists=User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already exists, Please choose a different username.', 'danger')
        else:
            new_user=User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful, You can now log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        user=User.query.filter_by(username=username).first()
        if user  and check_password_hash(user.password,password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/profile')
@login_required
def profile():
    pending_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    high_priority = Task.query.filter_by(user_id=current_user.id, priority='High').count()
    return render_template('profile.html', pending_tasks=pending_tasks,completed_tasks=completed_tasks,high_priority=high_priority)


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    pending_tasks = Task.query.filter_by(user_id=current_user.id, completed=False).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, completed=True).count()
    high_priority = Task.query.filter_by(user_id=current_user.id, priority='High').count()
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'profile':
            new_username = request.form['username']
            new_email = request.form['email']
            new_password = request.form['password']

            current_user.username = new_username
            current_user.email = new_email

            if new_password:
                current_user.password = generate_password_hash(new_password)

            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('settings'))

        elif form_type == 'appearance':
            dark_mode = request.form.get('dark_mode') == 'on'
            current_user.dark_mode = dark_mode
            db.session.commit()
            flash('Appearance preferences saved!', 'success')
            return redirect(url_for('settings'))

    return render_template('settings.html', dark_mode=current_user.dark_mode,pending_tasks=pending_tasks,completed_tasks=completed_tasks,high_priority=high_priority)



@app.route('/logout',methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))




if __name__ == '__main__':
    app.run(debug=True)
