
# app.py

import os
import io
from datetime import date, datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List
from dateutil.relativedelta import relativedelta
import calendar
import requests
import pandas as pd
import streamlit as st
import altair as alt

# 祝日
try:
    import jpholiday  # type: ignore
except Exception:
    jpholiday = None

# ========= 基本設定 =========
DEFAULT_API_BASE = "http://127.0.0.1:8000"
st.set_page_config(page_title="勤怠フロント", page_icon="🕒", layout="centered")
st.title("🕒 勤怠フロント（Streamlit）")

# ========= セッション初期化 =========
if "access" not in st.session_state:
    st.session_state["access"] = None  # type: Optional[str]
if "API_BASE" not in st.session_state:
    st.session_state["API_BASE"] = DEFAULT_API_BASE
if "headers" not in st.session_state:
    st.session_state["headers"] = {}

# ========= 小ヘルパー =========
def to_iso(d: date) -> str:
    return d.isoformat()

def today_local() -> date:
    return datetime.now().date()

def get_week_range(d: date) -> Tuple[date, date]:
    start = d - timedelta(days=d.weekday())  # 月曜始まり
    end = start + timedelta(days=6)
    return start, end

def get_month_range(d: date) -> Tuple[date, date]:
    first = d.replace(day=1)
    last = (first + relativedelta(months=1)) - timedelta(days=1)
    return first, last

def safe_get(dct: Any, *keys: Any, **kwargs: Any) -> Any:
    default = kwargs.get("default", None)
    cur = dct
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default

def is_jp_holiday(d: date) -> Tuple[bool, Optional[str]]:
    if jpholiday is None:
        return (False, None)
    try:
        name = jpholiday.is_holiday_name(d)  # type: ignore
        return (name is not None), name  # type: ignore
    except Exception:
        return (False, None)

def is_manager_user(me: Dict[str, Any]) -> bool:
    # /api/hr/me の is_manager を使用（無ければ False）
    return bool(me.get("is_manager"))

# ========= 接続チェック（🟢/🔴 バッジ用） =========
def ping_api(base_url: str) -> bool:
    # /api/health が無い環境でも /api/ でOKとする
    for path in ("/api/health", "/api/"):
        try:
            r = requests.get(base_url.rstrip("/") + path, timeout=3)
            if r.ok or r.status_code in (200, 401, 404):
                return True
        except requests.exceptions.RequestException:
            pass
    return False

# ========= API呼び出し =========
def api_login(base_url: str, username: str, password: str) -> Dict[str, Any]:
    """
    SimpleJWT のトークン取得エンドポイントで access/refresh を取得
    POST /api/auth/token/  {username, password}
    """
    url = base_url.rstrip("/") + "/api/auth/token/"
    resp = requests.post(url, json={"username": username, "password": password}, timeout=10)
    resp.raise_for_status()
    return resp.json()  # {"access": "...", "refresh": "..."}

def api_get(base_url: str, token: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    url = base_url.rstrip("/") + path
    headers = {"Authorization": "Bearer " + token}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {}

def api_post(base_url: str, token: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = base_url.rstrip("/") + path
    headers = {"Authorization": "Bearer " + token}
    r = requests.post(url, headers=headers, json=(payload or {}), timeout=20)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {}

def get_me(base_url: str, token: str) -> Dict[str, Any]:
    res = api_get(base_url, token, "/api/hr/me")
    return res if isinstance(res, dict) else {}

def punch(base_url: str, token: str, ptype: str, note: str = "") -> Dict[str, Any]:
    return api_post(base_url, token, "/api/attendance/punch", {"type": ptype, "note": note})

def get_my(base_url: str, token: str, dfrom: date, dto: date) -> Any:
    params = {"from": to_iso(dfrom), "to": to_iso(dto)}
    return api_get(base_url, token, "/api/attendance/my", params=params)

def get_summary(base_url: str, token: str, dfrom: date, dto: date, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {"from": to_iso(dfrom), "to": to_iso(dto)}
    if extra:
        for k, v in extra.items():
            if v not in (None, "", []):
                params[k] = v
    res = api_get(base_url, token, "/api/attendance/summary", params=params)
    # 必ず dict で返す
    if isinstance(res, dict):
        return res
    if isinstance(res, list):
        return {"value": res}
    return {"value": []}

# ========= 整形 =========
def summary_to_df(summary_json: Any, start: date, end: date) -> pd.DataFrame:
    vals: List[Dict[str, Any]] = []
    if isinstance(summary_json, dict):
        vals = summary_json.get("value", []) or []
    elif isinstance(summary_json, list):
        vals = summary_json
    recmap: Dict[date, Dict[str, Any]] = {}
    for v in vals:
        dt = v.get("date")
        try:
            dt2 = pd.to_datetime(dt).date()  # type: ignore
            recmap[dt2] = v
        except Exception:
            pass

    rows: List[Dict[str, Any]] = []
    cur = start
    while cur <= end:
        v = recmap.get(cur, {})
        wm = safe_get(v, "work_minutes", default=0)
        bm = safe_get(v, "break_minutes", default=0)
        om = safe_get(v, "overtime_minutes", default=0)
        notes = safe_get(v, "notes", default=[])
        is_hol, hol_name = is_jp_holiday(cur)
        rows.append({
            "date": cur,
            "work_minutes": int(wm or 0),
            "work_hours": round((wm or 0) / 60.0, 2),
            "break_minutes": int(bm or 0),
            "overtime_minutes": int(om or 0),
            "is_holiday": bool(is_hol or (cur.weekday() >= 5)),
            "holiday_name": hol_name if is_hol else ("土日" if cur.weekday() >= 5 else ""),
            "notes": notes,
        })
        cur += timedelta(days=1)
    return pd.DataFrame(rows)

def punches_to_df(punches: Any) -> pd.DataFrame:
    if not isinstance(punches, list) or not punches:
        return pd.DataFrame(columns=["punched_at", "punch_type", "note"])
    df = pd.DataFrame(punches)
    if "punched_at" in df.columns:
        df["punched_at"] = pd.to_datetime(df["punched_at"], errors="coerce")  # type: ignore
        df = df.sort_values("punched_at")
    keep = [c for c in ["punched_at", "punch_type", "note"] if c in df.columns]
    return df[keep] if keep else df

# ========= グラフ =========
def bar_chart(df: pd.DataFrame, unit: str, overtime_hours: Optional[float]):
    if df.empty:
        return alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_bar()

    plot_df = df.copy()
    if unit == "minutes":
        plot_df = plot_df.assign(y=plot_df["work_minutes"])
        y_title = "勤務（分）"
    else:
        plot_df = plot_df.assign(y=plot_df["work_hours"])
        y_title = "勤務（時間）"

    base = alt.Chart(plot_df).encode(
        x=alt.X("yearmonthdate(date):T", title="日付"),
        tooltip=[
            alt.Tooltip("yearmonthdate(date):T", title="日付"),
            alt.Tooltip("work_hours:Q", title="勤務h"),
            alt.Tooltip("work_minutes:Q", title="勤務min"),
            alt.Tooltip("overtime_minutes:Q", title="残業min"),
            alt.Tooltip("holiday_name:N", title="祝日/備考"),
        ],
    )

    bars = base.mark_bar().encode(
        y=alt.Y("y:Q", title=y_title),
        color=alt.Color("is_holiday:N", title="休日", scale=alt.Scale(range=["#4C78A8", "#F58518"])),
    )
    chart = bars

    if (overtime_hours is not None) and (unit == "hours"):
        line_df = pd.DataFrame({"y": [overtime_hours]})
        line = alt.Chart(line_df).mark_rule(strokeDash=[4, 4]).encode(y="y:Q")
        chart = chart + line

    return chart.properties(height=300).interactive()

# ========= /api/hr/me ヘッダー描画 =========
EMPLOYMENT_LABELS: Dict[str, str] = {
    "REGULAR": "正社員",
    "CONTRACT": "契約社員",
    "PARTTIME": "パート/アルバイト",
    "DISPATCH": "派遣",
    "INTERN": "インターン",
}

def render_me_header(emp: Dict[str, Any]) -> None:
    import html
    user = emp.get("user") or {}
    first = (user.get("first_name") or "").strip()
    last = (user.get("last_name") or "").strip()
    uname = (user.get("username") or "").strip()
    display_name = (first + " " + last).strip() or uname or "-"

    code = emp.get("employee_code") or "-"
    dept = safe_get(emp, "department", "name", default="-")
    pos  = safe_get(emp, "position", "name", default="-")
    et   = EMPLOYMENT_LABELS.get(emp.get("employment_type", ""), emp.get("employment_type") or "-")
    base = emp.get("base_hours_per_day", 8.0)
    status = emp.get("status") or "-"
    is_mgr = bool(emp.get("is_manager"))

    display_name = html.escape(str(display_name))
    code = html.escape(str(code))
    dept = html.escape(str(dept))
    pos = html.escape(str(pos))
    et = html.escape(str(et))
    status = html.escape(str(status))

    c1, c2 = st.columns([1.1, 1.9])
    with c1:
        st.markdown(
            """
            <div style="border:1px solid #eee;border-radius:10px;padding:12px;">
              <div style="font-size:1.05rem;">👤 <b>%s</b></div>
              <div style="color:#666;">社員コード: <b>%s</b></div>
              <div style="margin-top:6px;">
                %s
              </div>
            </div>
            """ % (
                display_name,
                code,
                "<span style='background:#ffe8a3;padding:2px 6px;border-radius:8px;'>管理職</span>" if is_mgr else ""
            ),
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            """
            <div style="border:1px solid #eee;border-radius:10px;padding:12px;">
              <div>🏢 部署: <b>%s</b>　🎖 役職: <b>%s</b></div>
              <div style="margin-top:4px;">💼 雇用区分: <b>%s</b>　🕘 所定: <b>%s h/日</b></div>
              <div style="margin-top:4px;">📌 ステータス: <b>%s</b></div>
            </div>
            """ % (dept, pos, et, base, status),
            unsafe_allow_html=True,
        )

# ========= サイドバー：接続 & ログイン =========
with st.sidebar:
    st.subheader("API接続")
    base_url = st.text_input("APIベースURL", value=st.session_state["API_BASE"], help="例: http://127.0.0.1:8000")
    connected = ping_api(base_url)
    st.markdown("**接続状態**: " + ("🟢 接続OK" if connected else "🔴 未接続"))

    st.subheader("ログイン")
    default_user = os.environ.get("HRM_USER", "admin")
    default_pass = os.environ.get("HRM_PASS", "kintai2025")
    username = st.text_input("ユーザー名", value=default_user, key="login_user")
    password = st.text_input("パスワード", value=default_pass, type="password", key="login_pass")
    if st.button("🔐 ログイン / トークン取得", use_container_width=True):
        try:
            data = api_login(base_url, username, password)
            access_token = data.get("access")
            if access_token:
                st.session_state["access"] = access_token
                st.session_state["API_BASE"] = base_url
                st.session_state["headers"] = {"Authorization": f"Bearer {access_token}"}
                st.success("ログイン成功（トークン取得）")
            else:
                st.error("トークン(access)が取得できませんでした")
        except Exception as e:
            st.error(f"ログイン失敗: {e}")

# ログイン必須
access: Optional[str] = st.session_state.get("access")
base_url: str = st.session_state.get("API_BASE", DEFAULT_API_BASE)
if not access:
    st.warning("左のサイドバーからログインしてください。")
    st.stop()

# ========= /api/hr/me（プロフィール表示） =========
me: Dict[str, Any] = {}
try:
    me = get_me(base_url, access)
    if isinstance(me, dict) and me:
        render_me_header(me)
    else:
        st.warning("社員情報（/api/hr/me）が空でした。HR登録未作成の可能性があります。")
except Exception:
    st.warning("社員情報（/api/hr/me）を取得できませんでした。HR登録未作成の可能性があります。")

# ========= KPIピル（当月サマリ） =========
today_d = today_local()
first_day, last_day = get_month_range(today_d)

try:
    summ_m_for_kpi = get_summary(base_url, access, first_day, last_day)
    dff = summary_to_df(summ_m_for_kpi, first_day, last_day)

    work_min_total = int(dff["work_minutes"].sum()) if not dff.empty else 0
    overtime_min_total = int(dff["overtime_minutes"].sum()) if not dff.empty else 0
    working_days = int((dff["work_minutes"] > 0).sum()) if not dff.empty else 0

    work_hours_total = round(work_min_total / 60.0, 2)
    overtime_hours_total = round(overtime_min_total / 60.0, 2)

    st.markdown(
        f"""
        <style>
          .kpi-header {{
            position: sticky; top: 0; z-index: 999;
            background: rgba(255,255,255,0.85); backdrop-filter: blur(6px);
            padding: 0.5rem 0.75rem 0.35rem; border-bottom: 1px solid #eee;
            margin-top: -0.5rem;
          }}
          .kpi-pill {{
            border: 1px solid #e5e7eb; border-radius: 9999px;
            padding: 0.45rem 0.9rem; display: inline-block;
            margin-right: 0.5rem; margin-bottom: 0.25rem;
            font-weight: 600; font-size: 0.95rem;
          }}
          .kpi-label {{ color: #6b7280; margin-right: 0.35rem; }}
          .kpi-value {{ color: #111827; }}
        </style>
        <div class="kpi-header">
          <span class="kpi-pill"><span class="kpi-label">今月の勤務時間</span><span class="kpi-value">{work_hours_total} h</span></span>
          <span class="kpi-pill"><span class="kpi-label">残業時間</span><span class="kpi-value">{overtime_hours_total} h</span></span>
          <span class="kpi-pill"><span class="kpi-label">出勤日数</span><span class="kpi-value">{working_days} 日</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )
except Exception as e:
    st.error(f"KPIピル用データ取得エラー: {e}")

st.markdown("---")

# ========= 当日の打刻 & 集計 =========
today = today_d

st.markdown("### 本日の打刻")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    if st.button("🟢 出勤", use_container_width=True):
        try:
            punch(base_url, access, "IN", "出勤")
            st.toast("出勤完了", icon="✅")
        except Exception as e:
            st.error(f"出勤失敗: {e}")

with col2:
    if st.button("🔴 退勤", use_container_width=True):
        try:
            punch(base_url, access, "OUT", "退勤")
            st.toast("退勤完了", icon="✅")
        except Exception as e:
            st.error(f"退勤失敗: {e}")

with col3:
    if st.button("☕ 休憩開始", use_container_width=True):
        try:
            punch(base_url, access, "BREAK_START", "休憩開始")
            st.toast("休憩開始完了", icon="✅")
        except Exception as e:
            st.error(f"休憩開始失敗: {e}")

with col4:
    if st.button("🍱 休憩終了", use_container_width=True):
        try:
            punch(base_url, access, "BREAK_END", "休憩終了")
            st.toast("休憩終了完了", icon="✅")
        except Exception as e:
            st.error(f"休憩終了失敗: {e}")

try:
    punches = get_my(base_url, access, today, today)
    dfp = punches_to_df(punches)
    st.subheader("当日の打刻一覧")
    if dfp.empty:
        st.write("打刻なし")
    else:
        st.dataframe(dfp, use_container_width=True)

    summ = get_summary(base_url, access, today, today)
    dfd = summary_to_df(summ, today, today)
    st.subheader("当日集計")
    if not dfd.empty:
        wm = int(dfd.loc[0, "work_minutes"])
        bm = int(dfd.loc[0, "break_minutes"])
        om = int(dfd.loc[0, "overtime_minutes"])
        m1, m2, m3 = st.columns(3)
        m1.metric("勤務", f"{wm} 分（{wm/60.0:.2f} h）")
        m2.metric("休憩", f"{bm} 分")
        m3.metric("残業", f"{om} 分")
    else:
        st.write("集計なし")
except Exception as e:
    st.error(f"当日データ取得エラー: {e}")

st.markdown("---")

# ========= 週/月タブ =========
tab_week, tab_month = st.tabs(["📅 週", "🗓️ 月"])

with tab_week:
    wk_start, wk_end = get_week_range(today)
    st.write(f"対象週: **{wk_start} ~ {wk_end}**")

    unit = st.radio("表示単位", ["hours", "minutes"], index=0, horizontal=True)
    ov = st.number_input("残業ライン(時間)", min_value=0.0, max_value=24.0, value=8.0, step=0.5)

    try:
        summ_w = get_summary(base_url, access, wk_start, wk_end)
        dfw = summary_to_df(summ_w, wk_start, wk_end)
        st.altair_chart(bar_chart(dfw, unit, ov), use_container_width=True)
        st.caption("※ オレンジは休日/祝日。点線は残業ライン（時間表示時のみ）。")
        st.dataframe(dfw, use_container_width=True)
    except Exception as e:
        st.error(f"週次データ取得エラー: {e}")

with tab_month:
    first, last = get_month_range(today)
    st.write(f"対象月: **{first} ~ {last}**")

    unit_m = st.radio("表示単位（⽉）", ["hours", "minutes"], index=0, horizontal=True, key="unit_m")
    ov_m = st.number_input("残業ライン(時間: ⽉)", min_value=0.0, max_value=24.0, value=8.0, step=0.5, key="ov_m")

    try:
        summ_m = get_summary(base_url, access, first, last)
        dfm = summary_to_df(summ_m, first, last)
        st.altair_chart(bar_chart(dfm, unit_m, ov_m), use_container_width=True)
        st.caption("※ オレンジは休日/祝日。点線は残業ライン（時間表示時のみ）。")
        st.dataframe(dfm, use_container_width=True)

        buf = io.StringIO()
        dfm.to_csv(buf, index=False, encoding="utf-8")
        st.download_button(
            "⬇ 月次CSVをダウンロード",
            data=buf.getvalue(),
            file_name=f"attendance_summary_{first.strftime('%Y%m')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"月次データ取得エラー: {e}")

# ========= チーム集計（管理者向け） =========
try:
    if me and is_manager_user(me):
        st.markdown("---")
        st.subheader("👥 チーム集計（管理者向け）")

        colf1, colf2, colf3, colf4 = st.columns([1.2, 1.2, 1.2, 1])
        with colf1:
            team_from = st.date_input("From", value=get_month_range(today)[0], format="YYYY-MM-DD")
        with colf2:
            team_to = st.date_input("To", value=get_month_range(today)[1], format="YYYY-MM-DD")
        with colf3:
            dept_id = st.text_input("部署ID（任意）", value="")
        with colf4:
            pos_id = st.text_input("役職ID（任意）", value="")

        colf5, colf6 = st.columns([1.2, 1.2])
        with colf5:
            ecode = st.text_input("社員コード（任意）", value="")
        with colf6:
            uid = st.text_input("ユーザーID（任意）", value="")

        unit_t = st.radio("表示単位（チーム）", ["hours", "minutes"], index=0, horizontal=True, key="unit_team")
        ov_t = st.number_input("残業ライン(時間: チーム)", min_value=0.0, max_value=24.0, value=8.0, step=0.5, key="ov_team")

        params: Dict[str, Any] = {}
        if dept_id.strip(): params["department"] = dept_id.strip()
        if pos_id.strip():  params["position"] = pos_id.strip()
        if ecode.strip():   params["employee_code"] = ecode.strip()
        if uid.strip():     params["user_id"] = uid.strip()

        try:
            team_summ = get_summary(base_url, access, team_from, team_to, extra=params)
            dft = summary_to_df(team_summ, team_from, team_to)
            st.altair_chart(bar_chart(dft, unit_t, ov_t), use_container_width=True)

            agg = dft.agg({"work_minutes":"sum","break_minutes":"sum","overtime_minutes":"sum"})
            c1, c2, c3 = st.columns(3)
            c1.metric("合計勤務", f"{int(agg.work_minutes)} 分（{agg.work_minutes/60.0:.2f} h）")
            c2.metric("合計休憩", f"{int(agg.break_minutes)} 分")
            c3.metric("合計残業", f"{int(agg.overtime_minutes)} 分")

            st.dataframe(dft, use_container_width=True)

            buf_team = io.StringIO()
            dft.to_csv(buf_team, index=False, encoding="utf-8")
            st.download_button(
                "⬇ チームCSVをダウンロード",
                data=buf_team.getvalue(),
                file_name=f"team_summary_{team_from.strftime('%Y%m%d')}_{team_to.strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"チーム集計エラー: {e}")
except Exception:
    # /api/hr/me 失敗などは無視
    pass

st.markdown("---")
st.caption("Powered by Django REST API + Streamlit")

# ========= 申請タブ（残業／休暇） =========

def post_json_full(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {access}"}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def get_json_full(path: str) -> Any:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {access}"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

with st.expander("📝 申請（残業・休暇）", expanded=True):
    sub = st.tabs(["⏱ 残業申請", "🏖 休暇申請", "📋 申請一覧", "🛠 承認（管理者）"])

    # --- 残業申請 ---
    with sub[0]:
        st.subheader("残業申請を作成")
        col1, col2 = st.columns(2)
        with col1:
            ov_date = st.date_input("対象日", value=date.today())
            start_t = st.time_input("開始", value=datetime.now().replace(hour=18, minute=0, second=0, microsecond=0).time())
        with col2:
            end_t = st.time_input("終了", value=datetime.now().replace(hour=19, minute=0, second=0, microsecond=0).time())
            reason = st.text_input("理由（任意）", value="", key="overtime_reason")

        if st.button("残業を申請する", type="primary"):
            try:
                payload = {
                    "date": ov_date.isoformat(),
                    "start_time": start_t.strftime("%H:%M"),
                    "end_time": end_t.strftime("%H:%M"),
                    "reason": reason
                }
                data = post_json_full("/api/requests/overtime/", payload)
                st.success(f"送信しました（{data.get('minutes',0)}分）")
            except Exception as e:
                st.error(f"申請に失敗しました：{e}")

    # --- 休暇申請 ---
    with sub[1]:
        st.subheader("休暇申請を作成")
        leave_type = st.selectbox(
            "休暇区分",
            ["PAID", "SICK", "ABSENCE", "SPECIAL"],
            index=0,
            format_func=lambda x: {"PAID":"有給","SICK":"病休","ABSENCE":"欠勤","SPECIAL":"特別休暇"}[x],
        )
        c1, c2 = st.columns(2)
        with c1:
            lv_start = st.date_input("開始日", value=date.today())
        with c2:
            lv_end = st.date_input("終了日", value=date.today())
            lv_reason = st.text_input("理由（任意）", value="", key="leave_reason")

        if st.button("休暇を申請する", type="primary"):
            try:
                payload = {
                    "leave_type": leave_type,
                    "start_date": lv_start.isoformat(),
                    "end_date": lv_end.isoformat(),
                    "reason": lv_reason
                }
                data = post_json_full("/api/requests/leave/", payload)
                st.success(f"送信しました（{data.get('days','?')}日）")
            except Exception as e:
                st.error(f"申請に失敗しました：{e}")

    # --- 申請一覧（自分） ---
    with sub[2]:
        st.subheader("自分の申請一覧")
        try:
            ov = get_json_full("/api/requests/overtime/?me=1")
            lv = get_json_full("/api/requests/leave/?me=1")

            st.write("**残業申請**")
            ov_list = ov["results"] if isinstance(ov, dict) and "results" in ov else ov
            st.dataframe([{
                "ID": x.get("id"), "日付": x.get("date"), "開始": x.get("start_time"), "終了": x.get("end_time"),
                "分": x.get("minutes"), "理由": x.get("reason",""), "状態": x.get("status")
            } for x in (ov_list or [])], use_container_width=True)

            st.write("**休暇申請**")
            lv_list = lv["results"] if isinstance(lv, dict) and "results" in lv else lv
            st.dataframe([{
                "ID": x.get("id"), "区分": x.get("leave_type"), "開始": x.get("start_date"), "終了": x.get("end_date"),
                "日数": x.get("days"), "理由": x.get("reason",""), "状態": x.get("status")
            } for x in (lv_list or [])], use_container_width=True)

            st.caption("行を選んで取消したいIDを下に入力してください。")
            cancel_id = st.text_input("取消ID", "", key="cancel_id_input")
            colc1, colc2 = st.columns(2)
            with colc1:
                if st.button("残業申請を取消"):
                    try:
                        post_json_full(f"/api/requests/overtime/{cancel_id}/cancel/", {})
                        st.success("取消しました")
                    except Exception as e:
                        st.error(f"取消に失敗：{e}")
            with colc2:
                if st.button("休暇申請を取消"):
                    try:
                        post_json_full(f"/api/requests/leave/{cancel_id}/cancel/", {})
                        st.success("取消しました")
                    except Exception as e:
                        st.error(f"取消に失敗：{e}")

        except Exception as e:
            st.error(f"一覧取得に失敗：{e}")

    # --- 承認（管理者） ---
    with sub[3]:
        st.subheader("承認・却下（管理者用）")
        st.caption("※ `is_staff=True` のユーザーでアクセスすると承認APIが使えます。")
        try:
            # 申請中だけを表示
            ov_p = get_json_full("/api/requests/overtime/?status=PENDING")
            lv_p = get_json_full("/api/requests/leave/?status=PENDING")
            ov_list = ov_p["results"] if isinstance(ov_p, dict) and "results" in ov_p else ov_p
            lv_list = lv_p["results"] if isinstance(lv_p, dict) and "results" in lv_p else lv_p

            st.write("**残業（申請中）**")
            st.dataframe([{
                "ID": x.get("id"), "社員": x.get("user"), "日付": x.get("date"), "開始": x.get("start_time"),
                "終了": x.get("end_time"), "分": x.get("minutes"), "理由": x.get("reason","")
            } for x in (ov_list or [])], use_container_width=True)

            st.write("**休暇（申請中）**")
            st.dataframe([{
                "ID": x.get("id"), "社員": x.get("user"), "区分": x.get("leave_type"),
                "開始": x.get("start_date"), "終了": x.get("end_date"), "日数": x.get("days"), "理由": x.get("reason","")
            } for x in (lv_list or [])], use_container_width=True)

            act_id = st.text_input("承認／却下するIDを入力", "", key="approve_id_input")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if st.button("残業を承認"):
                    try:
                        post_json_full(f"/api/requests/overtime/{act_id}/approve/", {})
                        st.success("承認しました")
                    except Exception as e:
                        st.error(f"失敗：{e}")
            with c2:
                if st.button("残業を却下"):
                    try:
                        post_json_full(f"/api/requests/overtime/{act_id}/reject/", {})
                        st.success("却下しました")
                    except Exception as e:
                        st.error(f"失敗：{e}")
            with c3:
                if st.button("休暇を承認"):
                    try:
                        post_json_full(f"/api/requests/leave/{act_id}/approve/", {})
                        st.success("承認しました")
                    except Exception as e:
                        st.error(f"失敗：{e}")
            with c4:
                if st.button("休暇を却下"):
                    try:
                        post_json_full(f"/api/requests/leave/{act_id}/reject/", {})
                        st.success("却下しました")
                    except Exception as e:
                        st.error(f"失敗：{e}")

        except Exception as e:
            st.error(f"承認一覧の取得に失敗：{e}")
