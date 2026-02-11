from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, DecimalField, DateTimeField, SelectField, SubmitField, BooleanField, IntegerField
from wtforms.validators import InputRequired, Optional, NumberRange, Length, ValidationError
from models import User, Material, Organization, Order, Product
from datetime import datetime


class LoginForm(FlaskForm):
    """
    Форма авторизации зарегистрированных пользователей.
    """
    username = StringField('Логин:', validators=[InputRequired(message='Необходимо заполнить поле')])
    password = PasswordField('Пароль:', validators=[InputRequired(message='Необходимо заполнить поле')])
    submit = SubmitField('Войти')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user is None:
            raise ValidationError('Неверный логин или пароль.')

    def validate_password(self, field):
        user = User.query.filter_by(username=self.username.data).first()
        if user and not user.check_password(field.data):
            raise ValidationError('Неверный логин или пароль.')


class AddMaterialForm(FlaskForm):
    """
    Форма добавления нового материала.
    """
    name = StringField('Название материала:', validators=[InputRequired(), Length(max=100)])
    description = TextAreaField('Описание:')
    quantity = DecimalField('Количество:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    unit = StringField('Единица измерения:', validators=[InputRequired(), Length(max=20)])
    price_per_unit = DecimalField('Цена за единицу:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Добавить материал')


class EditMaterialForm(FlaskForm):
    """
    Форма редактирования существующего материала.
    """
    name = StringField('Название материала:', validators=[InputRequired(), Length(max=100)])
    description = TextAreaField('Описание:')
    quantity = DecimalField('Количество:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    unit = StringField('Единица измерения:', validators=[InputRequired(), Length(max=20)])
    price_per_unit = DecimalField('Цена за единицу:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Изменить материал')


class AddOrganizationForm(FlaskForm):
    """
    Форма добавления новой организации.
    """
    name = StringField('Название организации:', validators=[InputRequired(), Length(max=100)])
    inn = StringField('ИНН:', validators=[InputRequired(), Length(max=12)])
    address = StringField('Адрес:', validators=[InputRequired(), Length(max=200)])
    phone = StringField('Телефон:', validators=[InputRequired(), Length(max=20)])
    salesman = BooleanField('Организация-продавец')
    buyer = BooleanField('Организация-покупатель')
    submit = SubmitField('Добавить организацию')

    def validate_inn(self, field):
        org = Organization.query.filter_by(inn=field.data).first()
        if org:
            raise ValidationError('Данная организация уже существует.')


class EditOrganizationForm(FlaskForm):
    """
    Форма редактирования существующей организации.
    """
    name = StringField('Название организации:', validators=[InputRequired(), Length(max=100)])
    inn = StringField('ИНН:', validators=[InputRequired(), Length(max=12)])
    address = StringField('Адрес:', validators=[InputRequired(), Length(max=200)])
    phone = StringField('Телефон:', validators=[InputRequired(), Length(max=20)])
    salesman = BooleanField('Организация-продавец')
    buyer = BooleanField('Организация-покупатель')
    submit = SubmitField('Изменить организацию')


class AddOrderForm(FlaskForm):
    """
    Форма добавления нового заказа.
    """
    order_number = StringField('Номер заказа:', validators=[InputRequired(), Length(max=20)])
    organization_id = SelectField('Организация:', coerce=int, validators=[InputRequired()])
    total_price = DecimalField('Общая стоимость:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Добавить заказ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization_id.choices = [
            (org.id, org.name) for org in Organization.query.all()
        ]

    def validate_order_number(self, field):
        order = Order.query.filter_by(order_number=field.data).first()
        if order:
            raise ValidationError('Такой номер заказа уже существует.')


class EditOrderForm(FlaskForm):
    """
    Форма редактирования существующего заказа.
    """
    order_number = StringField('Номер заказа:', validators=[InputRequired(), Length(max=20)])
    organization_id = SelectField('Организация:', coerce=int, validators=[InputRequired()])
    total_price = DecimalField('Общая стоимость:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Изменить заказ')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization_id.choices = [
            (org.id, org.name) for org in Organization.query.all()
        ]


class AddUserForm(FlaskForm):
    """
    Форма добавления нового пользователя.
    """
    username = StringField('Имя пользователя:', validators=[InputRequired(), Length(max=64)])
    password = PasswordField('Пароль:', validators=[InputRequired(), Length(min=6, max=30)])
    role = SelectField('Роль:', choices=[('user', 'Пользователь'), ('admin', 'Администратор')], validators=[InputRequired()])
    active = BooleanField('Активен?', default=True)
    submit = SubmitField('Добавить пользователя')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Такое имя пользователя уже занято.')


class EditUserForm(FlaskForm):
    """
    Форма редактирования пользователя.
    """
    username = StringField('Имя пользователя:', validators=[InputRequired(), Length(max=64)])
    role = SelectField('Роль:', choices=[('user', 'Пользователь'), ('admin', 'Администратор')], validators=[InputRequired()])
    active = BooleanField('Активен?', default=True)
    submit = SubmitField('Изменить пользователя')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user and hasattr(self, 'user_id') and user.id != self.user_id:
            raise ValidationError('Такое имя пользователя уже занято.')


class FilterUsersForm(FlaskForm):
    """
    Форма фильтра для пользователей.
    """
    search_query = StringField('Поиск по имени пользователя или E-mail:', validators=[Optional()])
    role_filter = SelectField('Фильтр по роли:', choices=[('', 'Все'), ('user', 'Пользователь'), ('admin', 'Администратор')], validators=[Optional()])
    active_filter = SelectField('Фильтр по состоянию:', choices=[('', 'Все'), ('True', 'Активные'), ('False', 'Заблокированные')], validators=[Optional()])
    submit = SubmitField('Применить фильтр')


class FilterMaterialsForm(FlaskForm):
    """
    Форма фильтра для материалов.
    """
    search_query = StringField('Поиск по названию материала:', validators=[Optional()])
    min_quantity = DecimalField('Минимальное количество:', places=2, validators=[NumberRange(min=0)], default=None)
    max_quantity = DecimalField('Максимальное количество:', places=2, validators=[NumberRange(min=0)], default=None)
    submit = SubmitField('Применить фильтр')


class FilterOrganizationsForm(FlaskForm):
    """
    Форма фильтра для организаций.
    """
    search_query = StringField('Поиск по названию организации:', validators=[Optional()])
    salesman_filter = BooleanField('Только продавцы', default=False)
    buyer_filter = BooleanField('Только покупатели', default=False)
    submit = SubmitField('Применить фильтр')


class FilterOrdersForm(FlaskForm):
    """
    Форма фильтра для заказов.
    """
    search_query = StringField('Поиск по номеру заказа:', validators=[Optional()])
    date_from = DateTimeField('Начало периода:', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    date_to = DateTimeField('Окончание периода:', format='%Y-%m-%d %H:%M:%S', validators=[Optional()])
    submit = SubmitField('Применить фильтр')


class AddProductForm(FlaskForm):
    """
    Форма добавления нового товара.
    """
    name = StringField('Название продукта:', validators=[InputRequired(), Length(max=100)])
    weight = DecimalField('Вес (кг):', places=3, validators=[InputRequired(), NumberRange(min=0)])
    quantity = IntegerField('Количество:', validators=[InputRequired(), NumberRange(min=0)])
    cost = DecimalField('Стоимость:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Добавить продукт')

    def validate_name(self, field):
        product = Product.query.filter_by(name=field.data).first()
        if product:
            raise ValidationError('Товар с таким названием уже существует.')


class EditProductForm(FlaskForm):
    """
    Форма редактирования товара.
    """
    name = StringField('Название продукта:', validators=[InputRequired(), Length(max=100)])
    weight = DecimalField('Вес (кг):', places=3, validators=[InputRequired(), NumberRange(min=0)])
    quantity = IntegerField('Количество:', validators=[InputRequired(), NumberRange(min=0)])
    cost = DecimalField('Стоимость:', places=2, validators=[InputRequired(), NumberRange(min=0)])
    submit = SubmitField('Сохранить изменения')

    def __init__(self, original_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, field):
        if field.data != self.original_name:
            product = Product.query.filter_by(name=field.data).first()
            if product:
                raise ValidationError('Товар с таким названием уже существует.')