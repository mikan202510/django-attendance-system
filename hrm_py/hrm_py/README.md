\# HRM (Django + Streamlit) — 勤怠管理システム



ローカルで動作する Django REST API と Streamlit UI の統合プロジェクトです。

勤怠打刻・日次／週次／月次の集計を自動化し、グラフで可視化します。



---



\## 🧩 主な機能

\- 出勤／退勤／休憩打刻API

\- 日次・週次・月次集計

\- JWT認証（開発用に任意設定可）

\- Streamlitフロントエンド（ボタン打刻＋可視化）



---



\## 🚀 実行方法

```bash

python -m venv .venv

. .venv/Scripts/activate

pip install -r requirements.txt

copy .env.example .env

python manage.py migrate

python manage.py runserver 8000

streamlit run app.py

