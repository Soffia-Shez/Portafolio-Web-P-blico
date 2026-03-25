import sqlite3
import uuid
import requests

from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'Clw_23'

def get_db_connection():
    conn = sqlite3.connect('portafolio.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM portafolio').fetchall()
    conn.close()


    filter_skill = request.args.get('skill')
    if filter_skill:
        filter_skill = filter_skill.strip().lower()
    else:
        filter_skill = None

    portafolios = []

    #Variable del loop
    for row in rows:
        skill_str = row['skills'] or ''
        skills = [s.strip() for s in skill_str.split(',') if s.strip()]
        skills_lower = [s.lower() for s in skills]

        # Filtrar si aplica
        if filter_skill is None or filter_skill in skills_lower:
            portafolios.append({
                "uuid": row["uuid"],
                "name": row["name"],
                "avatar": row["avatar"],
                "bio": row["bio"],
                "skills": skills
            })

    tool_icons = {
        "python": "fab fa-python",
        "java": "fab fa-java",
        "html": "fab fa-html5",
        "css": "fab fa-css3-alt",
        "javascript": "fab fa-js"
    }

    return render_template("all_portafolios.html",
        portafolios=portafolios,
        tool_icons=tool_icons,
        current_skill=filter_skill or ''
    )


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/generate', methods=['POST'])
def generate():
    uid = str(uuid.uuid4())

    if request.method == 'POST':
        name = request.form['name']
        bio = request.form['bio']
        github = request.form['github'].strip().replace('https://github.com/', '').replace('/', '')
        telegram = request.form['telegram']
        avatar = request.files.get('avatar')
        skills = request.form['skills']


        avatar_filename = ''
        if avatar and avatar.filename:
            filename = secure_filename(f"{uid}_{avatar.filename}")
            avatar_path = f"static/uploads/{filename}"
            avatar.save(avatar_path)

            avatar_filename = avatar_path.replace("static/", "")


        conn = get_db_connection()
        conn.execute("""
        INSERT INTO portafolio (uuid, name, bio, github, telegram, avatar, skills) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (uid, name, bio, github, telegram, avatar_filename, skills)
        )

        conn.commit()
        conn.close()


        print('Insertado en la base de datos')
        return redirect('/')


@app.route('/portafolio/<uuid>')
def view_portafolio(uuid):
    selected_skill = request.args.get('skill')
    conn = get_db_connection()

    info = conn.execute('SELECT * FROM portafolio WHERE uuid = ?', (uuid,)).fetchone()

    if info is None:
        return 'Portafolio not found', 404

    # Normaliza las skills: sin espacios, en minúscula y con comas
    skills_list = []
    if info['skills']:
        skills_list = [skill.strip().lower()
                       for skill in info['skills'].split(',')]

    recommended_profiles = conn.execute(
        'SELECT uuid, name FROM portafolio WHERE uuid != ?',
        (uuid,)
    ).fetchall()

    projects = conn.execute(
        'SELECT title, description, link FROM projects WHERE user_uuid = ?',
        (uuid,)
    ).fetchall()

    if not projects and info['github']:
        github_url = f"https://api.github.com/users/{info['github']}/repos"

        #Evitar error 500 en caso de que GitHub no exista
        try:
            response = requests.get(github_url, timeout=5)

            if response.status_code == 200:
                repos = response.json()[:6]

                for repo in repos:
                    conn.execute(
                        '''
                        INSERT INTO projects (user_uuid, title, description, link) 
                        VALUES (?, ?, ?, ?)
                        ''',
                        (
                            uuid,
                            repo['name'],
                            repo['description'] or 'No description',
                            repo['html_url']
                        )
                    )
                    conn.commit()

                    projects = conn.execute(
                        'SELECT title, description, link FROM projects WHERE user_uuid = ?',
                        (uuid,)
                    ).fetchall()

        except requests.RequestException:
            pass


    conn.close()

    tool_icons = {
        'python': '🐍',
        'flask': '🌶',
        'html': '📄',
        'css': '🎨',
        'html/css': '🖌️',
        'git': '🔧',
        'github': '🐙',
        'telegram': '✈️',
        'sql': '🗄️',
        'sqlite': '📘',
        'javascript': '⚡',
        'js': '⚡',
        'jinja': '🧩',
        'lua': '🗞️',
        'c++': '🖥️',
        'ruby': '📀'
    }

    context = {
        'name': info['name'],
        'bio': info['bio'],
        'github': info['github'],
        'telegram': info['telegram'],
        'avatar': info['avatar'],
        'skills': skills_list,
        'projects': projects,
        'tool_icons': tool_icons,
        'current_skill': selected_skill.lower() if selected_skill else None,
        'recommended_profiles': recommended_profiles
    }

    return render_template('portafolio_template.html', **context)

@app.route('/portafolio')
def portafolio_base():
    uuid = "21098d69-2ca0-4d87-9308-f1bc1e54492d"
    return redirect(url_for('view_portafolio', uuid=uuid))

if __name__ == "__main__":
    app.run(debug=False)