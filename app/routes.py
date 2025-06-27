from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import login_required, current_user
from .models import AttendancePost
from . import db
# For Google Calendar API
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime

bp = Blueprint('main', __name__)

def get_calendar_service():
    if 'google_oauth_token' not in session:
        flash('Googleアカウントで認証されていません。再度ログインしてください。', 'warning')
        return None

    token_info = session['google_oauth_token']
    credentials = Credentials(
        token=token_info['access_token'],
        refresh_token=token_info.get('refresh_token'), # May not be present if not requested or already used
        token_uri='https://oauth2.googleapis.com/token',
        client_id=current_app.config['GOOGLE_CLIENT_ID'],
        client_secret=current_app.config['GOOGLE_CLIENT_SECRET'],
        scopes=current_app.config['GOOGLE_CALENDAR_API_SCOPES']
    )

    # Handle token refresh if necessary
    if credentials.expired and credentials.refresh_token:
        try:
            import google.auth.transport.requests
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)
            session['google_oauth_token']['access_token'] = credentials.token # Update session token
        except Exception as e:
            current_app.logger.error(f"Error refreshing token: {e}")
            flash('セッションの有効期限が切れました。再度ログインしてください。', 'danger')
            session.pop('google_oauth_token', None) # Clear potentially bad token
            return None # Indicate failure to get service

    try:
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except HttpError as error:
        current_app.logger.error(f'An API error occurred: {error}')
        flash(f'Google Calendar APIへの接続に失敗しました: {error.resp.status}', 'danger')
        return None


@bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10 # Number of events per page

    calendar_service = get_calendar_service()
    if not calendar_service:
        return redirect(url_for('auth.login')) # Redirect to login if service cannot be obtained

    now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time

    try:
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=per_page * page, # Fetch enough for current and previous pages to get the correct slice
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        all_events = events_result.get('items', [])

        # Simple pagination: slice the events for the current page
        # For more robust pagination, you'd use the nextPageToken from the API
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        events_on_page = all_events[start_index:end_index]

        # Fetch post counts for each event on the current page
        for event in events_on_page:
            event_id = event['id']
            event['posts_count'] = AttendancePost.query.filter_by(event_id=event_id).count()
            event['attending_count'] = AttendancePost.query.filter_by(event_id=event_id, status='出席').count()
            event['tentative_count'] = AttendancePost.query.filter_by(event_id=event_id, status='未定').count()
            # Note: 'declined_count' is not explicitly requested for the event list summary

        # Basic next/prev page logic for demonstration
        # A more complete solution would use nextPageToken from Google API for true pagination
        has_next_page = len(all_events) > end_index
        has_prev_page = page > 1

    except HttpError as error:
        flash(f'カレンダーの予定取得中にエラーが発生しました: {error.resp.status}', 'danger')
        current_app.logger.error(f"Calendar API error: {error}")
        events_on_page = []
        has_next_page = False
        has_prev_page = False
    except Exception as e:
        flash(f'予期せぬエラーが発生しました: {str(e)}', 'danger')
        current_app.logger.error(f"Unexpected error: {str(e)}")
        events_on_page = []
        has_next_page = False
        has_prev_page = False


    return render_template('index.html',
                           events=events_on_page,
                           page=page,
                           has_next_page=has_next_page,
                           has_prev_page=has_prev_page)


@bp.route('/event/<event_id>')
@login_required
def event_details(event_id):
    calendar_service = get_calendar_service()
    event_summary = "イベント詳細" # Default summary
    if calendar_service:
        try:
            event = calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
            event_summary = event.get('summary', event_id)
        except HttpError as error:
            flash(f'イベント詳細の取得中にエラー: {error.resp.status}', 'warning')
            current_app.logger.warning(f"Could not fetch event {event_id} details: {error}")


    posts = AttendancePost.query.filter_by(event_id=event_id).order_by(AttendancePost.timestamp.desc()).all()
    return render_template('event_details.html', event_id=event_id, posts=posts, event_summary=event_summary)

@bp.route('/event/<event_id>/post', methods=['GET', 'POST'])
@login_required
def post_attendance(event_id):
    calendar_service = get_calendar_service()
    event_summary = event_id # Default summary
    if calendar_service:
        try:
            event = calendar_service.events().get(calendarId='primary', eventId=event_id).execute()
            event_summary = event.get('summary', event_id)
        except HttpError as error:
            flash(f'イベント詳細の取得中にエラー: {error.resp.status}', 'warning')
            current_app.logger.warning(f"Could not fetch event {event_id} details for post form: {error}")

    if request.method == 'POST':
        status = request.form.get('status')
        comment = request.form.get('comment')

        if not status:
            flash('出欠状況を選択してください。', 'danger')
        else:
            # Check if user already posted for this event, if so, update it
            existing_post = AttendancePost.query.filter_by(event_id=event_id, user_id=current_user.id).first()
            if existing_post:
                existing_post.status = status
                existing_post.comment = comment
                flash('投稿を更新しました。', 'success')
            else:
                new_post = AttendancePost(
                    event_id=event_id,
                    user_id=current_user.id,
                    user_name=current_user.name,
                    status=status,
                    comment=comment
                )
                db.session.add(new_post)
                flash('投稿しました。', 'success')

            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(f'データベースエラー: {str(e)}', 'danger')
                current_app.logger.error(f"DB error on post: {e}")

            return redirect(url_for('main.event_details', event_id=event_id))

    # For GET request, or if POST had an error and we re-render
    existing_post = AttendancePost.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    return render_template('post_form.html', event_id=event_id, event_summary=event_summary, existing_post=existing_post)
