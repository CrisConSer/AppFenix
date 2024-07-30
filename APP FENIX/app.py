from flask import Flask, render_template, request, redirect, send_file, url_for
import sqlite3
import matplotlib.pyplot as plt
import io

app = Flask(__name__)

# Función para inicializar la base de datos
def init_db():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS matches (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            rival TEXT,
                            player1 TEXT,
                            player2 TEXT,
                            court TEXT,
                            points_player1 INTEGER,
                            points_player2 INTEGER,
                            points_couple TEXT,
                            result TEXT,
                            date TEXT,
                            time TEXT,
                            observations TEXT)''')
        conn.commit()

# Ruta principal
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM matches')
    matches = cursor.fetchall()
    conn.close()
    return render_template('index.html', matches=matches)


# Ruta para agregar un partido
@app.route('/add_match', methods=['POST'])
def add_match():
    rival = request.form.get('rival', '')
    player1 = request.form.get('player1', '')
    player2 = request.form.get('player2', '')
    court = request.form.get('court', '')
    points_player1 = request.form.get('points_player1', '')
    points_player2 = request.form.get('points_player2', '')
    points_couple = request.form.get('points_couple', '')
    result = request.form.get('result', '')
    match_date = request.form.get('match_date', '')  # Usamos match_date en lugar de date
    rival_names = request.form.get('rival_names', '')
    observations = request.form.get('observations', '')

    if not player1 or not player2 or not court or not points_player1 or not points_player2 or not result or not match_date:
        return "Todos los campos son obligatorios", 400

    try:
        points_player1 = int(points_player1)
        points_player2 = int(points_player2)
    except ValueError:
        return "Los puntos deben ser números enteros", 400

    if result not in ['Ganado', 'Perdido']:
        return "El resultado debe ser 'Ganado' o 'Perdido'", 400

    total_points = points_player1 + points_player2

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO matches (rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result, date, observations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result, match_date, observations))
        conn.commit()

    return redirect('/')


# Ruta para eliminar un partido
@app.route('/delete_match/<int:id>')
def delete_match(id):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM matches WHERE id = ?', (id,))
        conn.commit()
    return redirect('/')

# Ruta para editar un partido
@app.route('/edit_match/<int:match_id>', methods=['GET', 'POST'])
def edit_match_view(match_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        rival = request.form['rival']
        player1 = request.form['player1']
        player2 = request.form['player2']
        court = request.form['court']
        points_player1 = request.form['points_player1']
        points_player2 = request.form['points_player2']
        points_couple = request.form['points_couple']
        result = request.form.get('result')
        date = request.form['date']  # Asegúrate de usar el nombre correcto
        time = request.form['time']  # Si tienes un campo de hora separado
        observations = request.form['observations']

        # Actualizar la base de datos
        cursor.execute('''
            UPDATE matches
            SET rival = ?, player1 = ?, player2 = ?, court = ?, points_player1 = ?, points_player2 = ?, points_couple = ?, result = ?, date = ?, time = ?, observations = ?
            WHERE id = ?
        ''', (rival, player1, player2, court, points_player1, points_player2, points_couple, result, date, time, observations, match_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    # Obtener los datos del partido
    cursor.execute('SELECT * FROM matches WHERE id = ?', (match_id,))
    match = cursor.fetchone()
    conn.close()

    return render_template('edit_match.html', match=match, id=match_id)


# Ruta para la búsqueda de jugadoras
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        player_name = request.form['player_name']
        return redirect(f'/player/{player_name}')
    return render_template('search.html')

# Ruta para el perfil de una jugadora
@app.route('/player/<name>')
def player_profile(name):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM matches WHERE player1 = ? OR player2 = ?', (name, name))
        matches = cursor.fetchall()

        # Obtener estadísticas de partidos ganados y perdidos
        cursor.execute('SELECT result, COUNT(*) FROM matches WHERE player1 = ? OR player2 = ? GROUP BY result', (name, name))
        data = cursor.fetchall()
    
    results = {result: count for result, count in data}
    won = results.get('Ganado', 0)
    lost = results.get('Perdido', 0)

    return render_template('player_profile.html', name=name, matches=matches, won=won, lost=lost)

# Ruta para el gráfico de partidos ganados vs perdidos
@app.route('/plot')
def plot():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT result, COUNT(*) FROM matches GROUP BY result')
        data = cursor.fetchall()

    results = {result: count for result, count in data}
    won = results.get('Ganado', 0)
    lost = results.get('Perdido', 0)

    labels = ['Ganados', 'Perdidos']
    values = [won, lost]

    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title('Partidos Ganados vs Perdidos')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return send_file(buf, mimetype='image/png')

#Ruta de búsqueda por partidos ganados/perdidos

@app.route('/search_matches', methods=['GET', 'POST'])
def search_matches():
    results = []
    search_query = ""

    if request.method == 'POST':
        search_query = request.form['search_query']
        result_filter = request.form['result_filter']

        query = '''
        SELECT rival, player1, player2, court, points_player1, points_player2, points_couple, total_points, result 
        FROM matches 
        WHERE (player1 LIKE ? OR player2 LIKE ? OR rival LIKE ?) AND result = ?
        '''
        search_query_with_wildcards = f"%{search_query}%"
        
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute(query, (search_query_with_wildcards, search_query_with_wildcards, search_query_with_wildcards, result_filter))
            results = cursor.fetchall()

    return render_template('search_matches.html', results=results, search_query=search_query)

#Ruta para manjer la búsqueda de partidos por jugador
@app.route('/search_player', methods=['GET'])
def search_player():
    player = request.args.get('player')
    if not player:
        return "Debe ingresar un nombre de jugador para buscar", 400

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM matches
            WHERE player1 = ? OR player2 = ?
        ''', (player, player))
        matches = cursor.fetchall()
    
    return render_template('player_search.html', matches=matches)

#Ruta para estadísticas generales
@app.route('/stats')
def stats():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM matches')
        total_matches = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM matches WHERE result = "Ganado"')
        won_matches = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM matches WHERE result = "Perdido"')
        lost_matches = cursor.fetchone()[0]

    if total_matches > 0:
        win_percentage = (won_matches / total_matches) * 100
    else:
        win_percentage = 0

    return render_template('stats.html', total_matches=total_matches, won_matches=won_matches, lost_matches=lost_matches, win_percentage=win_percentage)

# Ruta para parejas fuertes
@app.route('/strong_pairs')
def strong_pairs():
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p1.name AS player1, p2.name AS player2, COUNT(*) AS total_matches, 
                   SUM(CASE WHEN m.result = 'Ganado' THEN 1 ELSE 0 END) AS won_matches
            FROM matches m
            JOIN players p1 ON m.player1_id = p1.id
            JOIN players p2 ON m.player2_id = p2.id
            GROUP BY p1.name, p2.name
            HAVING total_matches > 5
            ORDER BY won_matches DESC
        ''')
        pairs = cursor.fetchall()

    return render_template('strong_pairs.html', pairs=pairs)



#Ruta para ver el listado del total de partidos jugados por jugadora
@app.route('/points')
def points():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            LOWER(TRIM(player)) AS player,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN result = 'Perdido' THEN 1 ELSE 0 END) AS losses,
            SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) AS total_points
        FROM (
            SELECT LOWER(TRIM(player1)) AS player, result FROM matches
            UNION ALL
            SELECT LOWER(TRIM(player2)) AS player, result FROM matches
        )
        GROUP BY player
        ORDER BY total_matches DESC
    ''')
    player_stats = cursor.fetchall()
    conn.close()
    return render_template('points.html', player_stats=player_stats)


#Rankin de Jugadoras
@app.route('/ranking')
def ranking():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            LOWER(TRIM(player)) AS player,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) AS wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_percentage
        FROM (
            SELECT LOWER(TRIM(player1)) AS player, result FROM matches
            UNION ALL
            SELECT LOWER(TRIM(player2)) AS player, result FROM matches
        )
        GROUP BY player
        ORDER BY win_percentage DESC, total_matches DESC
    ''')
    player_stats = cursor.fetchall()
    conn.close()
    return render_template('ranking.html', player_stats=player_stats)


#Tasa de Victoria
@app.route('/win_rate')
def win_rate():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            LOWER(TRIM(player)) AS player,
            COUNT(*) AS total_matches,
            SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) AS wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'Ganado' THEN 1 ELSE 0 END) / COUNT(*), 2) AS win_rate
        FROM (
            SELECT LOWER(TRIM(player1)) AS player, result FROM matches
            UNION ALL
            SELECT LOWER(TRIM(player2)) AS player, result FROM matches
        )
        GROUP BY player
        ORDER BY win_rate DESC
    ''')
    player_stats = cursor.fetchall()
    conn.close()
    return render_template('win_rate.html', player_stats=player_stats)


# Ruta para el gráfico de partidos ganados vs perdidos por jugador
@app.route('/plot_player/<name>')
def plot_player(name):
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT result, COUNT(*) FROM matches WHERE player1 = ? OR player2 = ? GROUP BY result', (name, name))
        data = cursor.fetchall()

    results = {result: count for result, count in data}
    won = results.get('Ganado', 0)
    lost = results.get('Perdido', 0)

    labels = ['Ganados', 'Perdidos']
    values = [won, lost]

    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140)
    plt.title(f'Partidos Ganados vs Perdidos de {name}')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return send_file(buf, mimetype='image/png')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0')
