from flask import Flask, request, render_template, redirect, url_for, flash, session
import json
import os
from werkzeug.utils import secure_filename
import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey123'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except Exception as e:
    print(f"Error creating upload folder: {e}")

DATA_FILE = '/opt/render/project/src/data.json'  # Persistent path on Render

if not os.path.exists(DATA_FILE):
    initial_data = {
        'users': {'client': {'password': 'client123', 'type': 'C'}, 'dev': {'password': 'devpass', 'type': 'D'}},
        'projects': {},
        'quotes': {},
        'agreements': {},
        'milestones': {},
        'payments': {},
        'portfolios': {},
        'chats': {}
    }
    save_data(initial_data)

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {
            'users': {'client': {'password': 'client123', 'type': 'C'}, 'dev': {'password': 'devpass', 'type': 'D'}},
            'projects': {},
            'quotes': {},
            'agreements': {},
            'milestones': {},
            'payments': {},
            'portfolios': {},
            'chats': {}
        }
    except Exception as e:
        print(f"Error loading data: {e}")
        return {'users': {}, 'projects': {}, 'quotes': {}, 'agreements': {}, 'milestones': {}, 'payments': {}, 'portfolios': {}, 'chats': {}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving data: {e}")

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        data = load_data()
        if username in data['users'] and data['users'][username]['password'] == password:
            session['username'] = username
            session['user_type'] = data['users'][username]['type']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_type', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        user_type = request.form.get('user_type', '')
        if not username or not password or user_type not in ['C', 'A', 'D']:
            flash('Invalid input!')
            return render_template('register.html')
        data = load_data()
        if username in data['users']:
            flash('Username already exists!')
        else:
            data['users'][username] = {'password': password, 'type': user_type}
            save_data(data)
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    data = load_data()
    try:
        if session['user_type'] == 'C':
            return render_template('client_dashboard.html', projects=data['projects'], quotes=data['quotes'], 
                                  agreements=data['agreements'], payments=data['payments'], username=session['username'])
        elif session['user_type'] == 'A':
            return render_template('artist_dashboard.html', projects=data['projects'], quotes=data['quotes'], 
                                  portfolios=data['portfolios'], agreements=data['agreements'], payments=data['payments'], 
                                  username=session['username'])
        else:  # Developer
            return render_template('admin.html', data=data)
    except Exception as e:
        flash(f"Error loading dashboard: {e}")
        return redirect(url_for('login'))

@app.route('/post_project', methods=['GET', 'POST'])
def post_project():
    if 'username' not in session or session['user_type'] != 'C':
        return redirect(url_for('login'))
    data = load_data()
    if request.method == 'POST':
        try:
            project_id = str(len(data['projects']) + 1)
            title = request.form.get('title', '')
            requirements = request.form.get('requirements', '')
            location = request.form.get('location', '')
            deadline = request.form.get('deadline', '')
            budget = request.form.get('budget', '')
            if not title or not requirements:
                flash('Title and requirements are required!')
                return redirect(url_for('dashboard'))
            files = request.files.getlist('images')
            filenames = []
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    filenames.append(filename)
            data['projects'][project_id] = {
                'title': title,
                'requirements': requirements,
                'images': filenames,
                'client': session['username'],
                'status': 'Open',
                'location': location,
                'deadline': deadline,
                'budget': budget,
                'timestamp': str(datetime.datetime.now())
            }
            save_data(data)
            flash('Project posted successfully!')
        except Exception as e:
            flash(f"Error posting project: {e}")
    return redirect(url_for('dashboard'))

@app.route('/edit_project/<project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'username' not in session or session['user_type'] != 'C':
        return redirect(url_for('login'))
    data = load_data()
    if project_id not in data['projects'] or data['projects'][project_id]['client'] != session['username']:
        flash('Unauthorized!')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        try:
            title = request.form.get('title', '')
            requirements = request.form.get('requirements', '')
            location = request.form.get('location', '')
            deadline = request.form.get('deadline', '')
            budget = request.form.get('budget', '')
            if not title or not requirements:
                flash('Title and requirements are required!')
            else:
                data['projects'][project_id]['title'] = title
                data['projects'][project_id]['requirements'] = requirements
                data['projects'][project_id]['location'] = location
                data['projects'][project_id]['deadline'] = deadline
                data['projects'][project_id]['budget'] = budget
                save_data(data)
                flash('Project updated!')
        except Exception as e:
            flash(f"Error updating project: {e}")
        return redirect(url_for('dashboard'))
    return render_template('edit_project.html', project=data['projects'][project_id])

@app.route('/delete_project/<project_id>', methods=['POST'])
def delete_project(project_id):
    if 'username' not in session or session['user_type'] != 'C':
        return redirect(url_for('login'))
    data = load_data()
    if project_id in data['projects'] and data['projects'][project_id]['client'] == session['username']:
        del data['projects'][project_id]
        save_data(data)
        flash('Project deleted!')
    return redirect(url_for('dashboard'))

@app.route('/flag_project/<project_id>', methods=['POST'])
def flag_project(project_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    data = load_data()
    if project_id in data['projects']:
        data['projects'][project_id]['status'] = 'Flagged' if data['projects'][project_id]['status'] != 'Flagged' else 'Open'
        save_data(data)
        flash(f"Project {project_id} status toggled!")
    return redirect(url_for('dashboard'))

@app.route('/submit_quote', methods=['POST'])
def submit_quote():
    if 'username' not in session or session['user_type'] != 'A':
        return redirect(url_for('login'))
    data = load_data()
    try:
        project_id = request.form.get('project_id', '')
        if project_id not in data['projects'] or data['projects'][project_id]['status'] != 'Open':
            flash('Invalid or closed project!')
        else:
            quote_id = f"{project_id}_{session['username']}"
            timeline = request.form.get('timeline', '')
            medium = request.form.get('medium', '')
            cost = request.form.get('cost', '')
            example_work = request.form.get('example_work', '')
            if not all([timeline, medium, cost, example_work]):
                flash('All quote fields are required!')
            else:
                data['quotes'][quote_id] = {
                    'project_id': project_id,
                    'artist': session['username'],
                    'timeline': timeline,
                    'medium': medium,
                    'cost': cost,
                    'example_work': example_work
                }
                save_data(data)
                flash('Quote submitted successfully!')
    except Exception as e:
        flash(f"Error submitting quote: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update_portfolio', methods=['POST'])
def update_portfolio():
    if 'username' not in session or session['user_type'] != 'A':
        return redirect(url_for('login'))
    data = load_data()
    try:
        files = request.files.getlist('portfolio_images')
        if not files or all(not f.filename for f in files):
            flash('No images selected!')
        else:
            if session['username'] not in data['portfolios']:
                data['portfolios'][session['username']] = []
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    data['portfolios'][session['username']].append(filename)
            save_data(data)
            flash('Portfolio updated with new images!')
    except Exception as e:
        flash(f"Error updating portfolio: {e}")
    return redirect(url_for('dashboard'))

@app.route('/select_artist/<project_id>', methods=['POST'])
def select_artist(project_id):
    if 'username' not in session or session['user_type'] != 'C':
        return redirect(url_for('login'))
    data = load_data()
    try:
        artist = request.form.get('artist', '')
        quote_id = f"{project_id}_{artist}"
        if quote_id not in data['quotes']:
            flash('Invalid artist selection!')
        else:
            total_payment = data['quotes'][quote_id]['cost']
            milestones = [m.strip() for m in request.form.get('milestones', '').split(',') if m.strip()]
            if len(milestones) > 5:
                flash('Maximum 5 milestones allowed!')
            elif not milestones:
                flash('Milestones are required!')
            else:
                data['agreements'][project_id] = {
                    'client': session['username'],
                    'artist': artist,
                    'total_payment': total_payment,
                    'milestones': {m: 'Pending' for m in milestones},
                    'status': 'Signed',
                    'agreement_text': f"Agreement for Project {project_id}: Client {session['username']} hires Artist {artist} for ${total_payment}. Milestones: {', '.join(milestones)}.",
                    'artist_accepted': False
                }
                data['projects'][project_id]['status'] = 'In Progress'
                data['payments'][project_id] = {'total': total_payment, 'released': '0'}
                save_data(data)
                flash(f'Agreement signed with {artist}! Please have the artist accept.')
    except Exception as e:
        flash(f"Error selecting artist: {e}")
    return redirect(url_for('dashboard'))

@app.route('/update_milestone/<project_id>', methods=['POST'])
def update_milestone(project_id):
    if 'username' not in session or session['user_type'] != 'A':
        return redirect(url_for('login'))
    data = load_data()
    try:
        milestone = request.form.get('milestone', '')
        if project_id in data['agreements'] and data['agreements'][project_id]['artist'] == session['username']:
            if milestone in data['agreements'][project_id]['milestones']:
                data['agreements'][project_id]['milestones'][milestone] = 'Completed'
                save_data(data)
                flash('Milestone updated!')
            else:
                flash('Invalid milestone!')
        else:
            flash('Unauthorized or invalid project!')
    except Exception as e:
        flash(f"Error updating milestone: {e}")
    return redirect(url_for('dashboard'))

@app.route('/release_payment/<project_id>', methods=['POST'])
def release_payment(project_id):
    if 'username' not in session or session['user_type'] != 'C':
        return redirect(url_for('login'))
    data = load_data()
    try:
        amount = request.form.get('amount', '')
        if not amount or float(amount) <= 0:
            flash('Invalid payment amount!')
        elif project_id in data['payments']:
            current = float(data['payments'][project_id]['released'].replace('$', ''))
            total = float(data['payments'][project_id]['total'].replace('$', ''))
            new_released = current + float(amount)
            if new_released > total:
                flash('Cannot release more than total amount!')
            else:
                data['payments'][project_id]['released'] = str(new_released)
                if all(status == 'Completed' for status in data['agreements'][project_id]['milestones'].values()) and new_released >= total:
                    data['projects'][project_id]['status'] = 'Completed'
                save_data(data)
                flash(f'${amount} released!')
        else:
            flash('Invalid project!')
    except ValueError:
        flash('Amount must be a number!')
    except Exception as e:
        flash(f"Error releasing payment: {e}")
    return redirect(url_for('dashboard'))

@app.route('/chat/<project_id>', methods=['GET', 'POST'])
def chat(project_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    data = load_data()
    if project_id not in data['agreements'] or session['username'] not in [data['agreements'][project_id]['client'], data['agreements'][project_id]['artist']]:
        flash('Unauthorized!')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        message = request.form.get('message', '')
        if message:
            chat_key = f"{project_id}_{data['agreements'][project_id]['client']}_{data['agreements'][project_id]['artist']}"
            if chat_key not in data['chats']:
                data['chats'][chat_key] = []
            data['chats'][chat_key].append({'sender': session['username'], 'message': message, 'timestamp': str(datetime.datetime.now())})
            save_data(data)
    return render_template('chat.html', project_id=project_id, chats=data['chats'].get(f"{project_id}_{data['agreements'][project_id]['client']}_{data['agreements'][project_id]['artist']}", []))

@app.route('/accept_agreement/<project_id>', methods=['POST'])
def accept_agreement(project_id):
    if 'username' not in session or session['user_type'] != 'A':
        return redirect(url_for('login'))
    data = load_data()
    if project_id in data['agreements'] and data['agreements'][project_id]['artist'] == session['username']:
        data['agreements'][project_id]['artist_accepted'] = True
        save_data(data)
        flash('Agreement accepted!')
    return redirect(url_for('dashboard'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'username' not in session or session['user_type'] != 'D':
        return redirect(url_for('login'))
    data = load_data()
    if request.method == 'POST':
        project_id = request.form.get('delete_project')
        if project_id and project_id in data['projects']:
            del data['projects'][project_id]
            save_data(data)
            flash('Project deleted by admin!')
    return render_template('admin.html', data=data)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)