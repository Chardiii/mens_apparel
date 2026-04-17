from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, UserRole
from extensions import limiter
from datetime import datetime, timedelta
import os, uuid, re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

ALLOWED_DOC_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'webp'}

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_doc(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

def save_doc(file, subfolder='docs'):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return os.path.join(subfolder, filename).replace('\\', '/')

def password_strong(pw):
    """Returns (ok, error_message)."""
    if len(pw) < 8:
        return False, 'Password must be at least 8 characters.'
    if not re.search(r'[A-Z]', pw):
        return False, 'Password must contain at least one uppercase letter.'
    if not re.search(r'[0-9]', pw):
        return False, 'Password must contain at least one number.'
    if not re.search(r'[^A-Za-z0-9]', pw):
        return False, 'Password must contain at least one special character.'
    return True, ''

def send_email(to, subject, html_body):
    """Send email via Flask-Mail. Silently fails in dev if mail not configured."""
    try:
        from flask_mail import Message
        from app import mail
        msg = Message(subject, recipients=[to], html=html_body)
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f'Email send failed: {e}')


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username   = request.form.get('username', '').strip()
        email      = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '')
        confirm    = request.form.get('confirm_password', '')
        role       = request.form.get('role', UserRole.BUYER.value)
        first_name = request.form.get('first_name', '').strip()
        last_name  = request.form.get('last_name', '').strip()
        phone      = request.form.get('phone', '').strip()

        if not username or not email or not password:
            flash('Username, email, and password are required.', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))

        ok, err = password_strong(password)
        if not ok:
            flash(err, 'danger')
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

        # Document validation
        valid_id_file        = request.files.get('valid_id')
        business_permit_file = request.files.get('business_permit')
        drivers_license_file = request.files.get('drivers_license')

        if not valid_id_file or not valid_id_file.filename:
            flash('A valid ID is required.', 'danger')
            return redirect(url_for('auth.register'))
        if not allowed_doc(valid_id_file.filename):
            flash('Valid ID must be JPG, PNG, WEBP, or PDF.', 'danger')
            return redirect(url_for('auth.register'))

        if role == UserRole.SELLER.value:
            if not request.form.get('shop_name', '').strip():
                flash('Store name is required for sellers.', 'danger')
                return redirect(url_for('auth.register'))
            if not business_permit_file or not business_permit_file.filename:
                flash('Business permit is required for sellers.', 'danger')
                return redirect(url_for('auth.register'))
            if not allowed_doc(business_permit_file.filename):
                flash('Business permit must be JPG, PNG, WEBP, or PDF.', 'danger')
                return redirect(url_for('auth.register'))

        if role == UserRole.RIDER.value:
            if not request.form.get('plate_number', '').strip():
                flash('Plate number is required for riders.', 'danger')
                return redirect(url_for('auth.register'))
            if not drivers_license_file or not drivers_license_file.filename:
                flash("Driver's license is required for riders.", 'danger')
                return redirect(url_for('auth.register'))
            if not allowed_doc(drivers_license_file.filename):
                flash("Driver's license must be JPG, PNG, WEBP, or PDF.", 'danger')
                return redirect(url_for('auth.register'))

        # Save documents
        valid_id_path        = save_doc(valid_id_file)
        business_permit_path = save_doc(business_permit_file) if role == UserRole.SELLER.value else None
        drivers_license_path = save_doc(drivers_license_file) if role == UserRole.RIDER.value else None

        # Generate email verification token
        verify_token = uuid.uuid4().hex

        user = User(
            username=username, email=email, role=role,
            first_name=first_name, last_name=last_name, phone=phone,
            valid_id=valid_id_path,
            is_active=False, is_verified=False,
            email_verified=False,
            email_verify_token=verify_token,
            street       = request.form.get('street', '').strip(),
            barangay     = request.form.get('barangay', '').strip(),
            municipality = request.form.get('municipality', '').strip(),
            province     = request.form.get('province', '').strip(),
            region       = request.form.get('region', '').strip(),
            zip_code     = request.form.get('zip_code', '').strip(),
        )
        user.set_password(password)

        if role == UserRole.SELLER.value:
            user.shop_name        = request.form.get('shop_name', '').strip()
            user.shop_description = request.form.get('shop_description', '').strip()
            user.business_permit  = business_permit_path

        if role == UserRole.RIDER.value:
            user.vehicle_type    = request.form.get('vehicle_type', '').strip()
            user.plate_number    = request.form.get('plate_number', '').strip()
            user.drivers_license = drivers_license_path

        db.session.add(user)
        db.session.commit()

        # Send verification email
        verify_url = url_for('auth.verify_email', token=verify_token, _external=True)
        send_email(
            to=email,
            subject='Mode S7vn — Verify Your Email',
            html_body=render_template('email/verify_email.html',
                                      username=username, verify_url=verify_url)
        )

        flash('Registration submitted! Please check your email to verify your address, then wait for admin approval.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


# ── Email verification ────────────────────────────────────────────────────────

@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verify_token=token).first()
    if not user:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('auth.login'))

    user.email_verified    = True
    user.email_verify_token = None
    db.session.commit()
    flash('Email verified! Your account is now pending admin approval.', 'success')
    return redirect(url_for('auth.login'))


# ── Forgot password ───────────────────────────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per minute; 10 per hour', methods=['POST'],
               error_message='Too many password reset requests. Please wait before trying again.')
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email).first()

        # Always show the same message to prevent email enumeration
        flash('If that email is registered, a reset link has been sent.', 'info')

        if user:
            token  = uuid.uuid4().hex
            expiry = datetime.utcnow() + timedelta(hours=1)
            user.reset_token        = token
            user.reset_token_expiry = expiry
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            send_email(
                to=email,
                subject='Mode S7vn — Password Reset',
                html_body=render_template('email/reset_password.html',
                                          username=user.username, reset_url=reset_url)
            )

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


# ── Reset password ────────────────────────────────────────────────────────────

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.utcnow():
        flash('This reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        ok, err = password_strong(password)
        if not ok:
            flash(err, 'danger')
            return redirect(url_for('auth.reset_password', token=token))

        user.set_password(password)
        user.reset_token        = None
        user.reset_token_expiry = None
        db.session.commit()

        flash('Password reset successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute; 30 per hour', methods=['POST'],
               error_message='Too many login attempts. Please wait before trying again.')
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
            if user.is_banned:
                flash('Your account has been permanently banned. Contact support if you believe this is an error.', 'danger')
                return redirect(url_for('auth.login'))
            if not user.email_verified:
                flash('Please verify your email address first. Check your inbox.', 'warning')
                return redirect(url_for('auth.login'))
            if not user.is_active:
                flash('Your account is pending admin approval. Please wait for verification.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(user, remember=True)
            # Merge any guest session cart into the DB cart
            from routes.orders import merge_session_cart_to_db
            merge_session_cart_to_db(user.id)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))

        flash('Invalid username or password.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# ── Profile ───────────────────────────────────────────────────────────────────

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.first_name   = request.form.get('first_name',   current_user.first_name)
        current_user.last_name    = request.form.get('last_name',    current_user.last_name)
        current_user.phone        = request.form.get('phone',        current_user.phone)
        current_user.street       = request.form.get('street',       current_user.street)
        current_user.barangay     = request.form.get('barangay',     current_user.barangay)
        current_user.municipality = request.form.get('municipality', current_user.municipality)
        current_user.province     = request.form.get('province',     current_user.province)
        current_user.region       = request.form.get('region',       current_user.region)
        current_user.zip_code     = request.form.get('zip_code',     current_user.zip_code)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('edit_profile.html', user=current_user)
