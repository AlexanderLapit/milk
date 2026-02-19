import signal
import sys
import time

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file, current_app, session
from flask_login import login_required, login_user, logout_user, current_user

from backup_system import full_backup, get_last_full_backup_time, get_last_backup_time, incremental_backup, \
    differential_backup, read_backup_log, restore_backup
from models import User, Material, Organization, Order, Report, Product
from forms import (
    LoginForm, AddMaterialForm, EditMaterialForm, AddOrganizationForm,
    EditOrganizationForm, AddOrderForm, EditOrderForm, FilterUsersForm,
    FilterMaterialsForm, FilterOrganizationsForm, FilterOrdersForm,
    AddUserForm, EditUserForm, AddProductForm, EditProductForm
)
from datetime import datetime
from sqlalchemy import func
from extensions import db
import os
import json

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def home():
    return render_template('home.html')


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html', form=form)


@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.home'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        sections = [
            {'title': 'Пользователи', 'url': url_for('main.users_list')},
            {'title': 'Материалы', 'url': url_for('main.materials_list')},
            {'title': 'Организации', 'url': url_for('main.organizations_list')},
            {'title': 'Заказы', 'url': url_for('main.orders_list')},
            {'title': 'Отчеты', 'url': url_for('main.reports_list')},
            {'title': 'Настройки', 'url': url_for('main.settings')}
        ]
    else:
        sections = [
            {'title': 'Материалы', 'url': url_for('main.materials_list')},
            {'title': 'Организации', 'url': url_for('main.organizations_list')},
            {'title': 'Заказы', 'url': url_for('main.orders_list')},
            {'title': 'Отчеты', 'url': url_for('main.reports_list')}
        ]
    return render_template('dashboard.html', sections=sections)


# --- Пользователи ---
@main_bp.route('/users', methods=['GET', 'POST'])
@login_required
def users_list():
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    filter_form = FilterUsersForm()
    query = User.query

    if filter_form.validate_on_submit():
        search = filter_form.search_query.data.strip().lower() if filter_form.search_query.data else None
        role = filter_form.role_filter.data or None
        active = filter_form.active_filter.data

        if search:
            query = query.filter(User.username.ilike(f'%{search}%'))
        if role:
            query = query.filter(User.role == role)
        if active == 'True':
            query = query.filter(User.active == True)
        elif active == 'False':
            query = query.filter(User.active == False)

    filtered_users = query.all()
    return render_template('admin/users.html', users=filtered_users, filter_form=filter_form)


@main_bp.route('/add-user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    form = AddUserForm()
    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            role=form.role.data,
            active=form.active.data
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash(f"Пользователь {new_user.username} успешно добавлен.", 'success')
        return redirect(url_for('main.users_list'))
    return render_template('admin/add_user.html', form=form)


@main_bp.route('/edit-user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(id)
    form = EditUserForm(obj=user)
    form.user_id = user.id

    if form.validate_on_submit():
        user.username = form.username.data
        user.role = form.role.data
        user.active = form.active.data
        db.session.commit()
        flash(f"Данные пользователя {user.username} успешно обновлены.", 'success')
        return redirect(url_for('main.users_list'))
    return render_template('admin/edit_user.html', form=form, user=user)


@main_bp.route('/delete-user/<int:id>')
@login_required
def delete_user(id):
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Нельзя удалить самого себя.", "danger")
        return redirect(url_for('main.users_list'))

    db.session.delete(user)
    db.session.commit()
    flash(f"Пользователь {user.username} удалён.", "success")
    return redirect(url_for('main.users_list'))


# --- Материалы ---
@main_bp.route('/materials', methods=['GET', 'POST'])
@login_required
def materials_list():
    filter_form = FilterMaterialsForm()
    query = Material.query

    if filter_form.validate_on_submit():
        search = filter_form.search_query.data.strip() if filter_form.search_query.data else None
        min_qty = filter_form.min_quantity.data
        max_qty = filter_form.max_quantity.data

        if search:
            query = query.filter(Material.name.contains(search))
        if min_qty is not None:
            query = query.filter(Material.quantity >= min_qty)
        if max_qty is not None:
            query = query.filter(Material.quantity <= max_qty)

    filtered_materials = query.all()
    return render_template('materials.html', materials=filtered_materials, filter_form=filter_form)


@main_bp.route('/add-material', methods=['GET', 'POST'])
@login_required
def add_material():
    form = AddMaterialForm()
    if form.validate_on_submit():
        new_material = Material(
            name=form.name.data,
            description=form.description.data,
            quantity=float(form.quantity.data),
            unit=form.unit.data,
            price_per_unit=float(form.price_per_unit.data)
        )
        db.session.add(new_material)
        db.session.commit()
        flash(f"Материал {new_material.name} успешно добавлен.", 'success')
        return redirect(url_for('main.materials_list'))
    return render_template('add_material.html', form=form)


@main_bp.route('/edit-material/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_material(id):
    material = Material.query.get_or_404(id)
    form = EditMaterialForm(obj=material)
    if form.validate_on_submit():
        material.name = form.name.data
        material.description = form.description.data
        material.quantity = float(form.quantity.data)
        material.unit = form.unit.data
        material.price_per_unit = float(form.price_per_unit.data)
        db.session.commit()
        flash(f"Материал {material.name} успешно обновлён.", 'success')
        return redirect(url_for('main.materials_list'))
    return render_template('edit_material.html', form=form, material=material)


@main_bp.route('/delete-material/<int:id>')
@login_required
def delete_material(id):
    material = Material.query.get_or_404(id)
    db.session.delete(material)
    db.session.commit()
    flash(f"Материал {material.name} удалён.", "success")
    return redirect(url_for('main.materials_list'))


# --- Организации ---
@main_bp.route('/organizations', methods=['GET', 'POST'])
@login_required
def organizations_list():
    filter_form = FilterOrganizationsForm()
    query = Organization.query

    if filter_form.validate_on_submit():
        search = filter_form.search_query.data.strip() if filter_form.search_query.data else None
        salesman = filter_form.salesman_filter.data
        buyer = filter_form.buyer_filter.data

        if search:
            query = query.filter(Organization.name.contains(search))
        if salesman:
            query = query.filter(Organization.salesman == True)
        if buyer:
            query = query.filter(Organization.buyer == True)

    filtered_organizations = query.all()
    return render_template('organizations.html', organizations=filtered_organizations, filter_form=filter_form)


@main_bp.route('/add-organization', methods=['GET', 'POST'])
@login_required
def add_organization():
    form = AddOrganizationForm()
    if form.validate_on_submit():
        new_org = Organization(
            name=form.name.data,
            inn=form.inn.data,
            address=form.address.data,
            phone=form.phone.data,
            salesman=form.salesman.data,
            buyer=form.buyer.data
        )
        db.session.add(new_org)
        db.session.commit()
        flash(f"Организация {new_org.name} успешно добавлена.", 'success')
        return redirect(url_for('main.organizations_list'))
    return render_template('add_organization.html', form=form)


@main_bp.route('/edit-organization/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_organization(id):
    org = Organization.query.get_or_404(id)
    form = EditOrganizationForm(obj=org)
    if form.validate_on_submit():
        org.name = form.name.data
        org.inn = form.inn.data
        org.address = form.address.data
        org.phone = form.phone.data
        org.salesman = form.salesman.data
        org.buyer = form.buyer.data
        db.session.commit()
        flash(f"Организация {org.name} успешно обновлена.", 'success')
        return redirect(url_for('main.organizations_list'))
    return render_template('edit_organization.html', form=form, org=org)


@main_bp.route('/delete-organization/<int:id>')
@login_required
def delete_organization(id):
    org = Organization.query.get_or_404(id)
    db.session.delete(org)
    db.session.commit()
    flash(f"Организация {org.name} удалена.", "success")
    return redirect(url_for('main.organizations_list'))


# --- Импорт/экспорт организаций ---
@main_bp.route('/import-organizations', methods=['GET', 'POST'])
@login_required
def import_organizations():
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash("Файл не выбран.", "warning")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("Файл не выбран.", "warning")
            return redirect(request.url)
        if file and file.filename.endswith('.json'):
            try:
                content = file.read().decode('utf-8')
                data = json.loads(content)
                if isinstance(data, dict):
                    data = data.get('organizations', [])
                elif not isinstance(data, list):
                    raise ValueError("Неверный формат JSON.")

                imported_count = 0
                for item in data:
                    inn = item.get('inn')
                    if not inn:
                        continue
                    if not Organization.query.filter_by(inn=inn).first():
                        new_org = Organization(
                            name=item.get('name', 'Не указано'),
                            inn=inn,
                            address=item.get('address', ''),
                            phone=item.get('phone', ''),
                            salesman=item.get('salesman', False),
                            buyer=item.get('buyer', True)
                        )
                        db.session.add(new_org)
                        imported_count += 1
                db.session.commit()
                flash(f"Импортировано {imported_count} новых организаций.", "success")
                return redirect(url_for('main.organizations_list'))
            except Exception as e:
                db.session.rollback()
                flash(f"Ошибка при импорте: {e}", "danger")
        else:
            flash("Только .json файлы поддерживаются.", "danger")
    return render_template('admin/import_organizations.html')


@main_bp.route('/export-organizations')
@login_required
def export_organizations():
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    buyers = Organization.query.filter_by(buyer=True).all()
    data = [
        {
            "name": org.name,
            "inn": org.inn,
            "address": org.address,
            "phone": org.phone,
            "salesman": org.salesman,
            "buyer": org.buyer
        }
        for org in buyers
    ]

    temp_dir = os.path.join("temp")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, "Заказчики.json")

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return send_file(file_path, as_attachment=True, download_name="Заказчики.json")


# --- Заказы ---
@main_bp.route('/orders', methods=['GET', 'POST'])
@login_required
def orders_list():
    filter_form = FilterOrdersForm()
    query = Order.query.join(Organization)

    if filter_form.validate_on_submit():
        search = filter_form.search_query.data.strip() if filter_form.search_query.data else None
        date_from = filter_form.date_from.data
        date_to = filter_form.date_to.data

        if search:
            query = query.filter(Order.order_number.contains(search))
        if date_from:
            query = query.filter(Order.created_at >= date_from)
        if date_to:
            query = query.filter(Order.created_at <= date_to)

    filtered_orders = query.all()
    return render_template('orders.html', orders=filtered_orders, filter_form=filter_form)


@main_bp.route('/add-order', methods=['GET', 'POST'])
@login_required
def add_order():
    form = AddOrderForm()
    if form.validate_on_submit():
        new_order = Order(
            order_number=form.order_number.data,
            organization_id=form.organization_id.data,
            total_price=float(form.total_price.data)
        )
        db.session.add(new_order)
        db.session.commit()
        flash(f"Заказ {new_order.order_number} успешно добавлен.", 'success')
        return redirect(url_for('main.orders_list'))
    return render_template('add_order.html', form=form)


@main_bp.route('/edit-order/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_order(id):
    order = Order.query.get_or_404(id)
    form = EditOrderForm(obj=order)
    if form.validate_on_submit():
        order.order_number = form.order_number.data
        order.organization_id = form.organization_id.data
        order.total_price = float(form.total_price.data)
        db.session.commit()
        flash(f"Заказ {order.order_number} успешно обновлён.", 'success')
        return redirect(url_for('main.orders_list'))
    return render_template('edit_order.html', form=form, order=order)


@main_bp.route('/delete-order/<int:id>')
@login_required
def delete_order(id):
    order = Order.query.get_or_404(id)
    db.session.delete(order)
    db.session.commit()
    flash(f"Заказ {order.order_number} удалён.", "success")
    return redirect(url_for('main.orders_list'))


# --- Отчёты ---
@main_bp.route('/reports')
@login_required
def reports_list():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('reports.html', reports=reports)


@main_bp.route('/generate-report', methods=['GET', 'POST'])
@login_required
def generate_report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start = request.form.get('start')
        end = request.form.get('end')

        query = Order.query
        if start:
            query = query.filter(Order.created_at >= datetime.fromisoformat(start))
        if end:
            query = query.filter(Order.created_at <= datetime.fromisoformat(end))

        total_orders = query.count()
        total_revenue = db.session.query(func.sum(Order.total_price)).scalar() or 0.0

        report_data = {
            "total_orders": total_orders,
            "total_revenue": float(total_revenue),
            "period_start": start,
            "period_end": end
        }

        new_report = Report(
            report_type=report_type,
            period_start=datetime.fromisoformat(start) if start else None,
            period_end=datetime.fromisoformat(end) if end else None,
            data=report_data
        )
        db.session.add(new_report)
        db.session.commit()

        flash("Отчёт успешно сгенерирован.", "success")
        return redirect(url_for('main.reports_list'))

    return render_template('generate_report.html')


# --- Настройки ---
@main_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash("Доступ запрещён.", "danger")
        return redirect(url_for('main.dashboard'))

    from utils import cleanup_temp_files
    import config

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'change_password':
            old_pass = request.form.get('old_password')
            new_pass = request.form.get('new_password')
            confirm_pass = request.form.get('confirm_password')

            if not current_user.check_password(old_pass):
                flash("Неверный текущий пароль.", "danger")
            elif new_pass != confirm_pass:
                flash("Новые пароли не совпадают.", "danger")
            elif len(new_pass) < 6:
                flash("Пароль должен быть не менее 6 символов.", "danger")
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                flash("Пароль успешно изменён.", "success")

        elif action == 'cleanup_temp':
            count = cleanup_temp_files()
            flash(f"Удалено {count} временных файлов.", "info")

    return render_template(
        'admin/settings.html',
        backup_log = read_backup_log(),
        debug=config.DevelopmentConfig.DEBUG,
        db_uri=config.Config.SQLALCHEMY_DATABASE_URI,
        version="1.0.0"
    )


# --- Товары ---
@main_bp.route('/products')
@login_required
def products_list():
    items = Product.query.all()
    return render_template('products.html', items=items)


@main_bp.route('/add-product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = AddProductForm()
    if form.validate_on_submit():
        new_product = Product(
            name=form.name.data,
            weight=float(form.weight.data),
            quantity=form.quantity.data,
            cost=float(form.cost.data)
        )
        db.session.add(new_product)
        db.session.commit()
        flash(f"Товар '{new_product.name}' успешно добавлен.", 'success')
        return redirect(url_for('main.products_list'))
    return render_template('add_product.html', form=form)


@main_bp.route('/edit-product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = EditProductForm(original_name=product.name, obj=product)
    if form.validate_on_submit():
        product.name = form.name.data
        product.weight = float(form.weight.data)
        product.quantity = form.quantity.data
        product.cost = float(form.cost.data)
        db.session.commit()
        flash(f"Товар '{product.name}' успешно обновлён.", 'success')
        return redirect(url_for('main.products_list'))
    return render_template('edit_product.html', form=form, product=product)


@main_bp.route('/delete-product/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash(f"Товар '{product.name}' удалён.", 'success')
    return redirect(url_for('main.products_list'))

# --- Отчёты: просмотр и экспорт ---
@main_bp.route('/report/<int:id>')
@login_required
def view_report(id):
    """
    Просмотр отчёта.
    """
    report = Report.query.get_or_404(id)
    return render_template('view_report.html', report=report)


@main_bp.route('/export-report/<int:id>')
@login_required
def export_report(id):
    """
    Экспорт отчёта в JSON.
    """
    report = Report.query.get_or_404(id)
    data = {
        "id": report.id,
        "type": report.report_type,
        "period_start": report.period_start.isoformat() if report.period_start else None,
        "period_end": report.period_end.isoformat() if report.period_end else None,
        "data": report.data,
        "created_at": report.created_at.isoformat()
    }
    file_path = os.path.join("temp", f"report_{report.id}.json")
    os.makedirs("temp", exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return send_file(file_path, as_attachment=True, download_name=f"Отчёт_{report.id}.json")

@main_bp.route('/backup/full', methods=['POST'])
@login_required
def backup_full():
    success, msg = full_backup()
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('main.settings'))


@main_bp.route('/backup/incremental', methods=['POST'])
@login_required
def backup_incremental():
    last_time = get_last_backup_time()
    success, msg = incremental_backup(last_backup_time=last_time)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('main.settings'))

@main_bp.route('/backup/differential', methods=['POST'])
@login_required
def backup_differential():
    last_time = get_last_full_backup_time()
    success, msg = differential_backup(last_full_backup_time=last_time)
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('main.settings'))


@main_bp.route('/restore/<int:backup_id>', methods=['POST'])
@login_required
def restore_from_backup(backup_id):
    log_entries = read_backup_log()
    if backup_id >= len(log_entries):
        flash("Неверный ID резервной копии.", "danger")
        return redirect(url_for('main.settings'))

    entry = log_entries[backup_id]
    success, msg = restore_backup(entry['path'])

    if success:
        # Сохраняем сообщение в сессии для отображения после перезапуска
        session['restore_success'] = msg
        # Возвращаем специальную страницу с JavaScript для перезапуска
        return render_template('restarting.html')
    else:
        flash(msg, 'danger')
        return redirect(url_for('main.settings'))


@main_bp.route('/restart', methods=['POST'])
def restart_app():
    time.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)
    return '', 200