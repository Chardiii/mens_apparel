from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, UserRole
import os
import uuid

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_DOC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'webp'}

def allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

def save_doc(file, subfolder='docs'):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return os.path.join(subfolder, filename).replace('\\', '/')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username    = request.form.get('username', '').strip()
        email       = request.form.get('email', '').strip()
        password    = request.form.get('password', '')
        confirm     = request.form.get('confirm_password', '')
        role        = request.form.get('role', UserRole.BUYER.value)
        first_name  = request.form.get('first_name', '').strip()
        last_name   = request.form.get('last_name', '').strip()
        phone       = request.form.get('phone', '').strip()

        # Basic validation
        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        if role not in [UserRole.BUYER.value, UserRole.SELLER.value, UserRole.RIDER.value]:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('auth.register'))

        # ── Document validation per role ──────────────────────────
        valid_id_file      = request.files.get('valid_id')
        business_permit_file = request.files.get('business_permit')
        drivers_license_file = request.files.get('drivers_license')

        if not valid_id_file or not valid_id_file.filename:
            flash('A valid ID is required for all registrations.', 'danger')
            return redirect(url_for('auth.register'))

        if not allowed_doc(valid_id_file.filename):
            flash('Valid ID must be an image (JPG, PNG, WEBP) or PDF.', 'danger')
            return redirect(url_for('auth.register'))

        if role == UserRole.SELLER.value:
            shop_name = request.form.get('shop_name', '').strip()
            if not shop_name:
                flash('Store name is required for sellers.', 'danger')
                return redirect(url_for('auth.register'))
            if not business_permit_file or not business_permit_file.filename:
                flash('Business permit is required for sellers.', 'danger')
                return redirect(url_for('auth.register'))
            if not allowed_doc(business_permit_file.filename):
                flash('Business permit must be an image or PDF.', 'danger')
                return redirect(url_for('auth.register'))

        if role == UserRole.RIDER.value:
            plate_number = request.form.get('plate_number', '').strip()
            if not plate_number:
                flash('Plate number is required for riders.', 'danger')
                return redirect(url_for('auth.register'))
            if not drivers_license_file or not drivers_license_file.filename:
                flash("Driver's license is required for riders.", 'danger')
                return redirect(url_for('auth.register'))
            if not allowed_doc(drivers_license_file.filename):
                flash("Driver's license must be an image or PDF.", 'danger')
                return redirect(url_for('auth.register'))

        # ── Save documents ────────────────────────────────────────
        valid_id_path = save_doc(valid_id_file)

        business_permit_path = None
        drivers_license_path = None

        if role == UserRole.SELLER.value and business_permit_file and business_permit_file.filename:
            business_permit_path = save_doc(business_permit_file)

        if role == UserRole.RIDER.value and drivers_license_file and drivers_license_file.filename:
            drivers_license_path = save_doc(drivers_license_file)

        # ── Create user ───────────────────────────────────────────
        user = User(
            username=username,
            email=email,
            role=role,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            valid_id=valid_id_path,
            is_active=False,    # pending admin approval
            is_verified=False
        )
        user.set_password(password)

        if role == UserRole.SELLER.value:
            user.shop_name = request.form.get('shop_name', '').strip()
            user.shop_description = request.form.get('shop_description', '').strip()
            user.business_permit = business_permit_path

        if role == UserRole.RIDER.value:
            user.vehicle_type = request.form.get('vehicle_type', '').strip()
            user.plate_number = request.form.get('plate_number', '').strip()
            user.drivers_license = drivers_license_path

        db.session.add(user)
        db.session.commit()

        flash('Registration submitted! Your account is pending admin approval. You will be notified once approved.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is pending approval. Please wait for admin verification.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(user, remember=True)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name  = request.form.get('last_name', current_user.last_name)
        current_user.phone      = request.form.get('phone', current_user.phone)
        current_user.address    = request.form.get('address', current_user.address)
        current_user.city       = request.form.get('city', current_user.city)
        current_user.zip_code   = request.form.get('zip_code', current_user.zip_code)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('edit_profile.html', user=current_user)
