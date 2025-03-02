from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
from flask import flash, redirect, url_for
# Инициализация объектов
app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Модели данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    email = db.Column(db.String(120))  # Новое поле email
    phone = db.Column(db.String(20))  # Поле телефон
    address = db.Column(db.String(255))  # Поле адрес
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.relationship('Note', back_populates='client')



class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Добавляем связь с моделью Client
    client = db.relationship('Client', back_populates='notes')

    def __repr__(self):
        return f"<Note for Client {self.client_id}>"


class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    interaction_type = db.Column(db.String(100))
    interaction_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f"<Interaction for Client {self.client_id}>"

# Функция загрузки пользователя для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Основные маршруты
@app.route('/clients')
@login_required
def clients():
    clients = Client.query.all()
    return render_template('client_list.html', clients=clients)

@app.route('/clients/new', methods=['GET', 'POST'])
@login_required
def new_client():
    if request.method == 'POST':
        new_client = Client(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            user_id=current_user.id  # Добавляем текущий user_id
        )
        db.session.add(new_client)
        db.session.commit()
        return redirect(url_for('clients'))
    return render_template('new_client.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('clients'))
        else:
            return 'Неверный логин или пароль', 401
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()  # Выход пользователя
    return redirect(url_for('login'))  # Перенаправление на страницу входа



# Стартовая страница (редирект на страницу с клиентами, если пользователь авторизован)
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('clients'))
    return redirect(url_for('login'))

# Новый маршрут для получения клиента по ID
@app.route('/api/clients/<int:id>', methods=['GET'])
def get_client(id):
    client = Client.query.get(id)
    if client:
        return jsonify({
            'id': client.id,
            'first_name': client.first_name,
            'last_name': client.last_name,
            'email': client.email,
            'phone': client.phone,
            'address': client.address
        })
    else:
        return jsonify({'message': 'Client not found'}), 404


@app.route('/edit_client/<int:client_id>', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    client = Client.query.get(client_id)
    if not client:
        flash('Клиент не найден!')
        return redirect(url_for('clients'))

    if request.method == 'POST':
        # Обновляем данные клиента
        client.first_name = request.form['first_name']
        client.last_name = request.form['last_name']
        client.email = request.form['email']
        db.session.commit()
        flash('Информация обновлена!')
        return redirect(url_for('clients'))

    return render_template('edit_client.html', client=client)
@app.route('/add_note', methods=['POST'])
@login_required
def add_note():
    client_id = request.form.get('client_id')
    note_content = request.form.get('note')

    # Проверяем, что были переданы данные
    if not client_id or not note_content:
        flash('Необходимо выбрать клиента и ввести заметку', 'danger')
        return redirect(url_for('index'))  # или другой редирект, если необходимо

    # Находим клиента по ID
    client = Client.query.get(client_id)
    if not client:
        flash('Клиент не найден', 'danger')
        return redirect(url_for('index'))

    # Добавляем заметку в базу данных
    new_note = Note(client_id=client.id, note=note_content)
    db.session.add(new_note)
    db.session.commit()

    flash('Заметка успешно добавлена!', 'success')
    return redirect(url_for('client_details', client_id=client.id))  # Редирект на страницу клиента


@app.route('/client/<int:client_id>', methods=['GET'])
@login_required
def client_details(client_id):
    client = Client.query.get_or_404(client_id)
    notes = Note.query.filter_by(client_id=client.id).all()

    return render_template('client_details.html', client=client, notes=notes)


@app.route('/client/<int:client_id>/notes')
@login_required
def view_notes(client_id):
    client = Client.query.get_or_404(client_id)
    notes = Note.query.filter_by(client_id=client.id).all()  # Получаем все заметки для клиента

    return render_template('view_notes.html', client=client, notes=notes)



@app.route('/note/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    # Получаем заметку из базы данных
    note = Note.query.get_or_404(note_id)

    # Проверяем, что текущий пользователь является владельцем клиента, связанного с заметкой
    if note.client.user_id != current_user.id:
        flash('У вас нет прав на удаление этой заметки.', 'danger')
        return redirect(url_for('client_details', client_id=note.client_id))

    # Удаляем заметку
    db.session.delete(note)
    db.session.commit()

    flash('Заметка успешно удалена.', 'success')
    return redirect(url_for('client_details', client_id=note.client_id))


@app.route('/delete_client/<int:client_id>', methods=['POST'])
@login_required
def delete_client(client_id):
    client = Client.query.get_or_404(client_id)
    if client.user_id != current_user.id:
        flash('Вы не можете удалить этого клиента.', 'danger')
        return redirect(url_for('clients'))

    db.session.delete(client)
    db.session.commit()
    flash('Клиент успешно удален.', 'success')
    return redirect(url_for('clients'))


# Запуск приложения
if __name__ == '__main__':
    # Создание базы данных, если она не существует
    with app.app_context():
        db.create_all()
    app.run(debug=True)
