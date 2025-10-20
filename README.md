## 内容

| 打刻画面（メインUI） | 日次・月次集計グラフ |
|----------------|------------------|
| ![punch](https://github.com/mikan202510/django-attendance-system/assets/00000000a2746209bc3ce3b39da5e8f8) | ![summary](https://github.com/mikan202510/django-attendance-system/assets/000000000a8c61fb8814231736b9b8ea) |

| 月次データ一覧 | チーム集計（管理者向け） |
|----------------|----------------|
| ![monthly](https://github.com/mikan202510/django-attendance-system/assets/0000000068006209a7c37a7864b216b5) | ![team](https://github.com/mikan202510/django-attendance-system/assets/0000000076746209b6ceafb6201f03e8) |

| 残業・休暇申請画面 |
|----------------|
| ![request](https://github.com/mikan202510/django-attendance-system/assets/00000000a724620998f8cd1404bc8aae) |

# Django × Streamlit 勤怠管理システム ― 打刻と集計の可視化アプリ
- Django REST Framework と Streamlit を組み合わせた、勤怠打刻と勤務時間集計を自動化・可視化するWebアプリです
- 出勤・退勤・休憩の打刻API、日次／週次／月次の勤怠集計、グラフ表示を実装
- ローカル開発環境で実行可能なポートフォリオ・学習用プロジェクトです

---

## 開発の目的 
 
- 「勤怠データの記録・集計・可視化」を一連の仕組みとして自作し、フロントとバックエンドの連携設計・API構築・データ可視化の理解を深めることを目的としました
- バックエンド（Django）とフロントエンド（Streamlit）の統合構成を実践的に学習

---

## 使用技術 

- Backend：Django / Django REST Framework / SimpleJWT / CORS Headers
- Frontend：Streamlit / Altair / Pandas / Requests  
- その他：python-dotenv / jpholiday / SQLite3
- 開発環境：Windows 10 / Python 3.11

---

## 機能 

- 出勤／退勤／休憩の打刻API（POST）
- 日次・週次・月次の勤怠集計API（GET）
- Streamlit UI（ボタン打刻・集計結果の可視化） 
- 社員別の勤務時間・残業時間・休暇日数の可視化
- JWT認証によるユーザー管理（開発モード対応）

---

## 工夫した点 

- Django REST Framework を用いてシンプルかつ拡張性のあるAPI設計を構築 
- Streamlit と Altair によるリアルタイム集計グラフ表示
- 祝日ライブラリ（jpholiday）で自動的に休日を判定  
- フロントとAPI通信を .env 設定で切り替え可能にし、開発・デモ両対応
- コードとUIを極力シンプルに保ち、学習用途にも理解しやすい構成に設計

---

## 実行方法 

- 依存パッケージをインストール
pip install -r requirements.txt
- .env ファイルを作成（.env.example をコピー）
copy .env.example .env
- Django（バックエンド）を起動
python manage.py migrate
python manage.py runserver 8000
- Streamlit（フロント）を起動
streamlit run app.py
- ブラウザで「http://localhost:8501」を開くと勤怠ダッシュボードが表示されます
---

## 想定利用シーン

- チームや個人の勤務時間を簡単に記録・可視化
- 小規模事業所の勤怠・残業・休暇の記録に利用
- エンジニア学習者が「API × フロント」構成を学ぶ教材として活用
- ポートフォリオ作品としてWebアプリ開発スキルを提示

---

## 今後の展望 

- /api/hr/me の社員情報APIを実装し、Streamlitに表示
- 月次KPIグラフの拡張（平均残業時間・稼働率）
- Streamlit Cloud へのデモ公開

---

## 制作メモ

- 開発期間：約2日
- 開発環境：Windows 10 / Python 3.11 / Django 4.2 / Streamlit 1.36
