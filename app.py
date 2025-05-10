from flask import Flask, render_template

# Создание экземпляра приложения
app = Flask(__name__)

# Главная страница (карта + список преступлений)
@app.route('/')
def index():
    return render_template('index.html')

# Страница добавления нового преступления
@app.route('/add-crime')
def add_crime():
    return render_template('add_crime.html')

# Страница со списком всех преступлений
@app.route('/all-crimes')
def all_crimes():
    return render_template('all_crimes.html')

# Заготовка для прогноза патрулей
@app.route('/patrol-forecast')
def patrol_forecast():
    return render_template('patrol_forecast.html')

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')
# Запуск сервера
if __name__ == '__main__':
    # Убедитесь, что порт 5000 свободен. Если нет, измените его на другой (например, 8080).
    app.run(debug=True, port=5000)