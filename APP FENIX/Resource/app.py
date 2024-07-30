from flask import Flask, render_template, request, redirect
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt

app = Flask(__name__)

# Función para calcular estadísticas básicas de un jugador
@app.route('/player_stats/<name>')
def player_stats(name):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM matches WHERE player1 = ? OR player2 = ?', (name, name))
        total_matches = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(total_points) FROM matches WHERE player1 = ? OR player2 = ?', (name, name))
        total_points = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM matches WHERE (player1 = ? OR player2 = ?) AND result = "Ganado"', (name, name))
        wins = cursor.fetchone()[0]

    win_percentage = (wins / total_matches) * 100 if total_matches > 0 else 0
    average_points = total_points / total_matches if total_matches > 0 else 0

    return render_template('player_stats.html', name=name, total_matches=total_matches, wins=wins, win_percentage=win_percentage, average_points=average_points)

# Función para predecir resultados de partidos
@app.route('/predict_match', methods=['POST'])
def predict_match():
    player1 = request.form['player1']
    player2 = request.form['player2']

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT points_player1, points_player2, result FROM matches WHERE player1 = ? AND player2 = ?', (player1, player2))
        data = cursor.fetchall()

    X = [(match[0], match[1]) for match in data]
    y = [1 if match[2] == 'Ganado' else 0 for match in data]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    clf = DecisionTreeClassifier()
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    prediction = clf.predict([(int(request.form['points_player1']), int(request.form['points_player2']))])[0]
    result = 'Ganado' if prediction == 1 else 'Perdido'

    return render_template('prediction_result.html', player1=player1, player2=player2, points_player1=request.form['points_player1'], points_player2=request.form['points_player2'], result=result, accuracy=accuracy)

@app.route('/player_performance/<name>')
def player_performance(name):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT points_player1, points_player2, result FROM matches WHERE player1 = ? OR player2 = ?', (name, name))
        matches = cursor.fetchall()

    points_player1 = [match[0] for match in matches if match[0] is not None]
    points_player2 = [match[1] for match in matches if match[1] is not None]
    results = ['Ganado' if match[2] == 'Ganado' else 'Perdido' for match in matches]

    plt.figure(figsize=(10, 6))

    plt.plot(points_player1, label='Puntos Jugador 1', marker='o')
    plt.plot(points_player2, label='Puntos Jugador 2', marker='x')
    plt.title(f'Rendimiento de {name}')
    plt.xlabel('Partidos')
    plt.ylabel('Puntos')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig('static/player_performance.png')  # Guarda el gráfico como una imagen

    return render_template('player_performance.html', name=name)


def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        # Crear la tabla si no existe
        cursor.execute('''CREATE TABLE IF NOT EXISTS matches (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            rival TEXT,
                            player1 TEXT,
                            player2 TEXT,
                            court TEXT,
                            points_player1 INTEGER,
                            points_player2 INTEGER,
                            points_couple TEXT,
                            total_points INTEGER,
                            result TEXT)''')
        # Verificar y añadir la columna points_couple si no existe
        cursor.execute("PRAGMA table_info(matches)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'points_couple' not in columns:
            cursor.execute('ALTER TABLE matches ADD COLUMN points_couple TEXT')
        conn.commit()

@app.route('/')
def index():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result FROM matches')
        matches = cursor.fetchall()
    return render_template('index.html', matches=matches)

@app.route('/add_match', methods=['POST'])
def add_match():
    rival = request.form['rival']
    player1 = request.form['player1']
    player2 = request.form['player2']
    court = request.form['court']
    points_player1 = request.form['points_player1']
    points_player2 = request.form['points_player2']
    points_couple = request.form['points_couple']
    result = request.form.get('result')  # Checkbox

    if not player1 or not player2 or not court or not points_player1 or not points_player2 or result is None:
        return "Todos los campos son obligatorios", 400
    
    try:
        points_player1 = int(points_player1)
        points_player2 = int(points_player2)
    except ValueError:
        return "Los puntos deben ser números enteros", 400

    total_points = points_player1 + points_player2

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO matches (rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', 
                       (rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result))
        conn.commit()
    
    return redirect('/')

@app.route('/delete_match/<int:id>')
def delete_match(id):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM matches WHERE id = ?', (id,))
        conn.commit()
    return redirect('/')

@app.route('/edit_match/<int:id>', methods=['GET', 'POST'])
def edit_match_view(id):
    if request.method == 'POST':
        rival = request.form['rival']
        player1 = request.form['player1']
        player2 = request.form['player2']
        court = request.form['court']
        points_player1 = request.form['points_player1']
        points_player2 = request.form['points_player2']
        points_couple = request.form['points_couple']
        result = request.form.get('result')  # Checkbox

        if not player1 or not player2 or not court or not points_player1 or not points_player2 or result is None:
            return "Todos los campos son obligatorios", 400

        try:
            points_player1 = int(points_player1)
            points_player2 = int(points_player2)
        except ValueError:
            return "Los puntos deben ser números enteros", 400

        total_points = points_player1 + points_player2

        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE matches SET rival = ?, player1 = ?, player2 = ?, court = ?, points_player1 = ?, points_player2 = ?, points_couple = ?, total_points = ?, result = ? WHERE id = ?',
                           (rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result, id))
            conn.commit()
        return redirect('/')
    
    else:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT rival, player1, player2, court, points_player1, points_player2, points_couple, result FROM matches WHERE id = ?', (id,))
            match = cursor.fetchone()
        return render_template('edit_match.html', match=match, id=id)

@app.route('/player/<name>')
def player_profile(name):
    with sqlite3.connect('database.db') as conn:
        conn.row_factory = sqlite3.Row  # Para acceder a las columnas por nombre
        cursor = conn.cursor()
        cursor.execute('SELECT *, CASE WHEN result = "Ganado" THEN "Ganado" ELSE "Perdido" END AS status FROM matches WHERE player1 = ? OR player2 = ?', (name, name))
        matches = cursor.fetchall()
    return render_template('player_profile.html', name=name, matches=matches)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        player_name = request.form['player_name']
        return redirect(f'/player/{player_name}')
    return render_template('search.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
