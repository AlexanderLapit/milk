from flask import Flask, current_app, render_template
from extensions import db
from flask_login import LoginManager

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.DevelopmentConfig')
    app.jinja_env.globals.update(enumerate=enumerate)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():
        from models import User

        @login_manager.user_loader
        def load_user(user_id):
            return db.session.get(User, int(user_id))

        from routes import main_bp
        app.register_blueprint(main_bp)

        @app.errorhandler(404)
        def not_found_error(error):
            return render_template('errors/404.html'), 404

        @app.errorhandler(500)
        def internal_error(error):
            db.session.rollback()
            return render_template('errors/500.html'), 500

        db.create_all()
        create_admin_user()

    return app


def create_admin_user():
    """Создаёт пользователя admin, если его ещё нет."""
    from models import User

    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            role='admin',
            active=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Администратор 'admin' успешно создан.")
    else:
        print("ℹ️  Пользователь 'admin' уже существует.")


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)


def create_admin_user():
    """Создаёт пользователя admin, если его ещё нет."""
    from models import User

    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            role='admin',
            active=True
        )
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Администратор 'admin' успешно создан.")
    else:
        print("ℹ️  Пользователь 'admin' уже существует.")



if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)