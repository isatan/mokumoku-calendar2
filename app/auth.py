import json
from flask import Blueprint, redirect, url_for, flash, session, request, current_app, render_template
from flask_login import login_user, logout_user, login_required, current_user
from oauthlib.oauth2 import WebApplicationClient
import requests
from .models import User
from . import db

bp = Blueprint('auth', __name__, url_prefix='/auth')

def get_google_provider_cfg():
    try:
        return requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Failed to get Google provider config: {e}")
        return None

@bp.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        flash("Google認証サーバーに接続できませんでした。しばらくしてから再度お試しください。", "danger")
        return redirect(url_for('main.index')) # Or a dedicated error page

    authorization_endpoint = google_provider_cfg["authorization_endpoint"]
    client = WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])

    redirect_uri = url_for('auth.callback', _external=True)
    if current_app.config['OAUTHLIB_INSECURE_TRANSPORT']:
         # For local development with HTTP
        if not redirect_uri.startswith('http://'):
            redirect_uri = redirect_uri.replace('https://', 'http://', 1)


    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=redirect_uri,
        scope=["openid", "email", "profile", current_app.config['GOOGLE_CALENDAR_API_SCOPES'][0]], # Add calendar scope
        access_type='offline', # Request refresh token
        prompt='consent' # Ensure refresh token is sent every time for development/testing
    )
    return redirect(request_uri)

@bp.route('/callback')
def callback():
    client = WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])
    google_provider_cfg = get_google_provider_cfg()
    if not google_provider_cfg:
        flash("Google認証サーバーに接続できませんでした。しばらくしてから再度お試しください。", "danger")
        return redirect(url_for('main.index'))

    token_endpoint = google_provider_cfg["token_endpoint"]
    code = request.args.get("code")

    redirect_uri = url_for('auth.callback', _external=True)
    if current_app.config['OAUTHLIB_INSECURE_TRANSPORT']:
        if not redirect_uri.startswith('http://'):
            redirect_uri = redirect_uri.replace('https://', 'http://', 1)


    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=redirect_uri,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(current_app.config['GOOGLE_CLIENT_ID'], current_app.config['GOOGLE_CLIENT_SECRET']),
    )

    if not token_response.ok:
        flash(f"トークンの取得に失敗しました: {token_response.text}", "danger")
        return redirect(url_for('main.index'))

    client.parse_request_body_response(json.dumps(token_response.json()))

    # Store the tokens in the session for API calls
    session['google_oauth_token'] = token_response.json()


    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        unique_id = userinfo_response.json()["sub"]
        users_email = userinfo_response.json()["email"]
        picture = userinfo_response.json()["picture"]
        users_name = userinfo_response.json()["name"]
    else:
        flash("ユーザーのメールアドレスが確認されていません。", "danger")
        return redirect(url_for('main.index'))

    user = User.query.filter_by(google_id=unique_id).first()
    if not user:
        user = User(google_id=unique_id, name=users_name, email=users_email, profile_pic=picture)
        db.session.add(user)
        db.session.commit()
        flash("新しいアカウントが作成されました。", "success")
    else:
        # Update user info if changed
        user.name = users_name
        user.email = users_email
        user.profile_pic = picture
        db.session.commit()


    login_user(user)
    flash(f"{user.name}さん、ようこそ！", "success")
    return redirect(url_for('main.index'))


@bp.route('/logout')
@login_required
def logout():
    session.pop('google_oauth_token', None) # Clear OAuth token from session
    logout_user()
    flash("ログアウトしました。", "info")
    return redirect(url_for('main.index'))

# Dummy login page for login_manager.login_view if direct access to /auth/login is preferred.
# Or, you might want a page that explains "Login with Google"
@bp.route('/login_page') # This could be the target for login_view if you want a page first
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    return render_template('login.html')
