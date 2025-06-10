from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required
import requests
from app.models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_id = request.form.get('account_id', '').strip()
        api_key = request.form.get('api_key', '').strip()

        if not account_id or not api_key:
            flash('Preencha todos os campos.', 'warning')
            return redirect(url_for('auth.login'))

        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
            }

            data = {
                'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
                'apikey': api_key,
                'response_type': 'cloud_iam',
            }

            response = requests.post(
                'https://iam.cloud.ibm.com/identity/token',
                headers=headers,
                data=data,
                timeout=10
            )

            if response.status_code == 200:
                token_data = response.json()
                session.clear()
                session['access_token'] = token_data.get('access_token')
                session['account_id'] = account_id
                session.permanent = True

                user = User(account_id)
                login_user(user)

                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard.home'))
            elif response.status_code == 400:
                flash('Chave de API inválida ou expirou. Verifique os dados.', 'danger')
            else:
                flash(f'Erro ao autenticar. Código: {response.status_code}', 'danger')

        except requests.exceptions.RequestException:
            flash('Erro de conexão com o servidor da IBM Cloud.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('auth.login'))
