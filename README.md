# Google Calendar Event Poll

Google Calendarの予定に対して、参加可否の情報を投稿するWebアプリケーションです。

## 機能

- Googleアカウント連携による認証
- ログイン後の初期表示はGoogle Calendarの予定一覧（ページネーションあり）
  - 各予定には、現在の投稿数、出席数、未定数を表示
- 予定を選択すると、その予定への参加可否投稿一覧画面へ遷移
  - 投稿者名、出欠状況（出席、欠席、未定）、コメントを表示
- 投稿一覧画面から投稿フォーム画面へ遷移し、参加可否とコメントを投稿・編集可能

## 技術スタック

- Python
- Flask
  - Flask-SQLAlchemy (データベースORM)
  - Flask-Migrate (データベースマイグレーション)
  - Flask-Login (ユーザーセッション管理)
- Google API Client Library for Python
  - Google Calendar API (予定取得)
  - Google OAuth 2.0 (認証)
- Bootstrap 5 (フロントエンドフレームワーク)
- SQLite (開発用データベース)

## セットアップと実行方法

### 1. 前提条件

- Python 3.8以上
- pip

### 2. Google Cloud Platformでの設定

1.  [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成または選択します。
2.  **APIとサービス > ライブラリ** で "Google Calendar API" を検索し、有効にします。 (OAuth同意画面でユーザー情報を取得するために必要な "Google People API" なども内部的に有効になることがあります)
3.  **APIとサービス > OAuth同意画面** を設定します。
    - **ユーザータイプ**: 「外部」を選択します。(テスト中は、ご自身のGoogleアカウントをテストユーザーとして追加できます)
    - **アプリ情報**:
        - アプリケーション名 (例: `Calendar Event Poll App`)
        - ユーザーサポートメール (ご自身のメールアドレス)
        - アプリのロゴ (任意)
        - アプリケーションのホームページ、プライバシーポリシー、利用規約のリンク (任意ですが、本番公開時は推奨)
    - **デベロッパーの連絡先情報**: メールアドレスを入力します。
    - **スコープ**: 「スコープを追加または削除」ボタンをクリックし、手動で以下のスコープを追加します (フィルタで検索すると見つけやすいです):
        - `../auth/calendar.readonly` (Google Calendar API - See and download any calendar you can access using your Google Calendar)
        - `../auth/userinfo.email` (See your primary Google Account email address)
        - `../auth/userinfo.profile` (See your personal info, including any personal info you've made publicly available)
        - `openid` (Associate you with your personal info on Google)
    - **テストユーザー**: テスト段階では、ご自身のGoogleアカウントのメールアドレスを追加します。これにより、アプリが「テスト中」の状態でもそのアカウントでログインしてテストできます。
    - 設定を保存します。
4.  **APIとサービス > 認証情報** を開きます。
5.  画面上部の **＋認証情報を作成** をクリックし、「OAuthクライアントID」を選択します。
6.  **アプリケーションの種類**: 「ウェブアプリケーション」を選択します。
7.  **名前**: 任意の名前を入力します (例: "Calendar Event Poll Web Client")。
8.  **承認済みのリダイレクトURI**: 「＋URIを追加」をクリックし、以下を追加します（ローカル開発用）:
    - `http://127.0.0.1:5000/auth/callback`
    - `http://localhost:5000/auth/callback`
9.  「作成」ボタンをクリックします。作成後、「クライアントID」と「クライアントシークレット」が表示されるので、これらを安全な場所に控えておきます。

### 3. ローカル環境でのセットアップ

1.  リポジトリをクローンします (まだの場合):
    ```bash
    # git clone <repository-url>
    # cd <repository-directory>
    ```
2.  Python仮想環境を作成して有効化します (推奨):
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS の場合
    # venv\Scripts\activate    # Windows の場合
    ```
3.  必要なライブラリをインストールします:
    ```bash
    pip install -r requirements.txt
    ```
4.  プロジェクトのルートディレクトリに`.env`ファイルを作成します。以下の内容をコピーし、必要な情報を追記・編集してください:
    ```env
    # Flask App
    SECRET_KEY='your_very_secret_key_please_change_this_for_production' # 強力な秘密鍵に変更してください
    FLASK_APP=run.py # Flask CLIがアプリケーションを見つけるために必要
    # FLASK_DEBUG=1 # 開発中にデバッグモードを有効にする場合 (本番では0または未設定)

    # Database
    DATABASE_URL='sqlite:///app.db' # ローカルSQLiteデータベース

    # Google OAuth Credentials
    GOOGLE_CLIENT_ID='YOUR_GOOGLE_CLIENT_ID' # 手順2で取得したクライアントID
    GOOGLE_CLIENT_SECRET='YOUR_GOOGLE_CLIENT_SECRET' # 手順2で取得したクライアントシークレット

    # ローカルHTTPでのOAuthコールバックを許可する場合 (開発時のみ '1' に設定)
    OAUTHLIB_INSECURE_TRANSPORT='1'
    ```
    - `YOUR_GOOGLE_CLIENT_ID` と `YOUR_GOOGLE_CLIENT_SECRET` を、手順2で取得したものに置き換えてください。
    - `SECRET_KEY` は、Flaskのセッション管理などに使われる重要なキーです。ランダムで複雑な文字列に変更してください（例: `openssl rand -hex 32` で生成）。

### 4. データベースの初期化とマイグレーション

アプリケーションのルートディレクトリで以下のコマンドを実行します。

1.  **Flask-Migrateの初期化** (まだ`migrations`フォルダがない場合のみ):
    ```bash
    flask db init
    ```
2.  **マイグレーションファイルの生成**:
    モデル（`app/models.py`）に変更があった場合（初回含む）に実行します。
    ```bash
    flask db migrate -m "Initial migration with User and AttendancePost tables"
    ```
    (コメントは適宜変更してください)
3.  **マイグレーションの適用**:
    生成されたマイグレーションをデータベースに適用します。
    ```bash
    flask db upgrade
    ```

### 5. アプリケーションの実行

```bash
flask run
```
成功すれば、ターミナルに `Running on http://127.0.0.1:5000/` (または同様のURL) が表示されます。
ブラウザでこのURLを開いてください。

## 注意事項

- このアプリケーションは開発・デモンストレーション目的で作成されています。本番環境で利用する際は、セキュリティ対策（`SECRET_KEY`の厳重な管理、HTTPS化、エラーハンドリングの強化、依存ライブラリの脆弱性チェックなど）やパフォーマンスチューニングを十分に行ってください。
- Google CloudプロジェクトのOAuth同意画面で、公開ステータスが「テスト中」の場合、テストユーザーとして登録されたGoogleアカウント以外はログインできません。より多くのユーザーに利用させる場合は、同意画面の設定を審査に提出し、「本番環境」に切り替える必要があります。
- `.env` ファイルには機密情報が含まれるため、Gitなどのバージョン管理システムにはコミットしないでください。`.gitignore`ファイルに`.env`を追加することを推奨します。

## 今後の改善点 (例)

- より詳細なエラーハンドリングとユーザーへのフィードバック
- ページネーションの改善 (Google Calendar APIの`nextPageToken`を活用した、より正確なページング)
- カレンダーイベントのフィルタリング機能 (例: 表示する日付範囲の指定)
- UI/UXのさらなる向上 (カスタムCSSの追加、JavaScriptによるインタラクティブ性の向上など)
- 多言語対応
- 本番環境用の設定分離 (例: `config.py` で開発用・本番用設定を分ける)
- より堅牢なデータベースへの移行検討 (PostgreSQL, MySQLなど)
- 非同期処理の導入によるパフォーマンス改善 (例: API呼び出し部分)
```
