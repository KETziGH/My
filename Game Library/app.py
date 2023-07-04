import os

from flask import Flask, render_template, request, redirect, url_for, session, g, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Get the absolute path of the current directory
current_directory = os.path.dirname(os.path.abspath(__file__))

# Set the absolute path of the database file
DATABASE = os.path.join(current_directory, 'library.db')


# Connect to the database
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

# Create the database tables if they don't exist
def initialize_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS members
                     (name TEXT, contact TEXT, email TEXT PRIMARY KEY, password TEXT, age INTEGER)''')
        db.execute('''CREATE TABLE IF NOT EXISTS games
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, category TEXT, publishers TEXT, picture TEXT, details TEXT)''')
        db.execute('''CREATE TABLE IF NOT EXISTS game_requests
                     (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, publisher TEXT, member_email TEXT)''')
        db.commit()

# Close the database connection
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize the database
initialize_db()


@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('games'))
    return render_template('index.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'email' in session:
        return redirect(url_for('games'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == 'admin@gmail.com' and password == 'admin':
            session['email'] = email
            return redirect(url_for('games'))
        else:
            # Check if the provided email and password match the database
            with get_db() as db:
                cursor = db.cursor()
                cursor.execute("SELECT * FROM members WHERE email = ? AND password = ?", (email, password))
                member = cursor.fetchone()

            if member:
                session['email'] = email
                return redirect(url_for('games'))
            else:
                return render_template('signin.html', error='Invalid email or password')

    return render_template('signin.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'email' in session:
        return redirect(url_for('games'))

    if request.method == 'POST':
        name = request.form['name']
        contact = request.form['contact']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        age = int(request.form['age'])

        if password != confirm_password:
            flash("Password and Confirm Password do not match", "error")
            return redirect(url_for('signup'))

        # Check if email already exists in the database
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT COUNT(*) FROM members WHERE email = ?", (email,))
            count = cursor.fetchone()[0]
            if count > 0:
                flash("Email address already exists", "error")
                return redirect(url_for('signup'))

            # Insert new member into the database
            cursor.execute("INSERT INTO members (name, contact, email, password, age) VALUES (?, ?, ?, ?, ?)",
                           (name, contact, email, password, age))
            db.commit()

        session['email'] = email
        return redirect(url_for('games'))

    return render_template('signup.html')



@app.route('/games')
def games():
    if 'email' not in session:
        return redirect(url_for('index'))

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM games")
        games = cursor.fetchall()

    return render_template('games.html', games=games)

@app.route('/show_image')
def show_image():
    if 'email' not in session:
        return redirect(url_for('index'))

    image_url = request.args.get('image')
    game_name = request.args.get('name')

    return render_template('show_image.html', image=image_url, game_name=game_name)

@app.route('/request_game', methods=['GET', 'POST'])
def request_game():
    if 'email' not in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        publisher = request.form['publisher']
        member_email = session['email']

        # Insert new game request into the database
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO game_requests (name, publisher, member_email) VALUES (?, ?, ?)",
                           (name, publisher, member_email))
            db.commit()

        return redirect(url_for('games'))

    return render_template('request_game.html')


@app.route('/add_game', methods=['GET', 'POST'])
def add_game():
    if 'email' not in session or session['email'] != 'admin@gmail.com':
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        publishers = request.form['publishers']  
        picture = request.form['picture']
        details = request.form['details']

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO games (name, category, publishers, picture, details) VALUES (?, ?, ?, ?, ?)",
               (name, category, publishers, picture, details))
            db.commit()

        return redirect(url_for('games'))

    return render_template('add_game.html')

@app.route('/remove_signup_members', methods=['POST'])
def remove_signup_members():
    if 'email' not in session or session['email'] != 'admin@gmail.com':
        return redirect(url_for('index'))

    member_email = request.form['member_email']
    
    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM members WHERE email = ?", (member_email,))
        db.commit()

    return redirect(url_for('games'))

@app.route('/remove_game', methods=['GET', 'POST'])
def remove_game():
    if 'email' not in session or session['email'] != 'admin@gmail.com':
        return redirect(url_for('index'))

    if request.method == 'POST':
        game_id = int(request.form['game_id'])

        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("DELETE FROM games WHERE id = ?", (game_id,))
            db.commit()

        return redirect(url_for('games'))

    with get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM games")
        games = cursor.fetchall()

        cursor.execute("SELECT * FROM members")
        members = cursor.fetchall()

    return render_template('remove_game.html', games=games, members=members)

@app.route('/history')
def history():
    if 'email' not in session:
        return redirect(url_for('index'))

    with get_db() as db:
        cursor = db.cursor()

        if session['email'] == 'admin@gmail.com':
            # Fetch all members' information for admin
            cursor.execute("SELECT name, contact, email, age FROM members")
            members = cursor.fetchall()

            cursor.execute("SELECT * FROM game_requests")
            game_requests = cursor.fetchall()

            return render_template('history.html', members=members, game_requests=game_requests)
        else:
            # Fetch member's information for other members
            cursor.execute("SELECT name, age FROM members WHERE email = ?", (session['email'],))
            member = cursor.fetchone()

            cursor.execute("SELECT * FROM game_requests")
            game_requests = cursor.fetchall()

            return render_template('history.html', member=member, game_requests=game_requests)

@app.route('/signout')
def signout():
    session.pop('email', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
