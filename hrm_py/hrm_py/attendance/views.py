# attendance/views.py
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import Iterable, List, Dict, Tuple

from django.db.models import QuerySet, Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .models import Attendance as AttendancePunch

# Employee 情報（残業判定の所定労働時間参照用：存在しなければ無視）
try:
    from hr_core.models import Employee
except Exception:  # hr_core が未導入でも動くように
    Employee = None  # type: ignore


# ==== 共通ユーティリティ ====

PUNCH_IN = "IN"
PUNCH_OUT = "OUT"
BREAK_START = "BREAK_START"
BREAK_END = "BREAK_END"
ALLOWED_TYPES = {PUNCH_IN, PUNCH_OUT, BREAK_START, BREAK_END}


def is_hr_admin(user) -> bool:
    """HR管理者判定：is_staff または HR_ADMIN グループ所属"""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False):
        return True
    try:
        return user.groups.filter(name="HR_ADMIN").exists()
    except Exception:
        return False


def local_today() -> date:
    return timezone.localdate()


def to_iso_date(d: date) -> str:
    return d.isoformat()


def to_iso_dt(dt: datetime) -> str:
    # JSONにISO8601で返却（tzつき）
    return dt.astimezone(timezone.get_current_timezone()).isoformat()


def parse_range(request) -> Tuple[date, date]:
    """?from=YYYY-MM-DD&to=YYYY-MM-DD を date にパース。無効なら本日～本日。"""
    s = request.query_params.get("from")
    e = request.query_params.get("to")
    start = parse_date(s) if s else None
    end = parse_date(e) if e else None
    if not start:
        start = local_today()
    if not end:
        end = start
    if end < start:
        start, end = end, start
    return start, end


def daterange(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


# ==== 打刻API ====

class PunchAPIView(APIView):
    """
    POST /api/attendance/punch
    Body: {"type": "IN"|"OUT"|"BREAK_START"|"BREAK_END", "note": "任意"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ptype = (request.data or {}).get("type")
        note = (request.data or {}).get("note", "") or ""

        if ptype not in ALLOWED_TYPES:
            return Response(
                {"detail": f"Invalid type. allowed={sorted(ALLOWED_TYPES)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        work_date = timezone.localdate(now)

        punch = AttendancePunch.objects.create(
            user=request.user,
            punch_type=ptype,
            punched_at=now,
            work_date=work_date,
            note=note,
        )

        return Response(
            {
                "id": punch.id,
                "punch_type": punch.punch_type,
                "punched_at": to_iso_dt(punch.punched_at),
                "work_date": to_iso_date(punch.work_date),
                "note": punch.note or "",
            },
            status=status.HTTP_201_CREATED,
        )


# ==== 自分の打刻一覧 ====

class MyAttendanceAPIView(APIView):
    """
    GET /api/attendance/my?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        start, end = parse_range(request)

        qs: QuerySet[AttendancePunch] = (
            AttendancePunch.objects
            .filter(user=request.user, work_date__gte=start, work_date__lte=end)
            .order_by("punched_at", "id")
        )

        data = [
            {
                "id": p.id,
                "punch_type": p.punch_type,
                "punched_at": to_iso_dt(p.punched_at),
                "work_date": to_iso_date(p.work_date),
                "note": p.note or "",
            }
            for p in qs
        ]
        return Response(data)


# ==== 日次集計 ====

@dataclass
class DayCalcResult:
    work_minutes: int = 0
    break_minutes: int = 0

    @property
    def overtime_minutes(self) -> int:
        # 実際の所定労働時間は呼び出し元で差し引く（ここはダミー）
        return 0


def _pair_intervals(events: List[AttendancePunch], start_type: str, end_type: str) -> List[Tuple[datetime, datetime]]:
    """
    指定した開始/終了タイプをペアリングして区間リストを返す。
    不完全ペアは末尾は無視（安全側）。
    """
    start_at: datetime | None = None
    intervals: List[Tuple[datetime, datetime]] = []
    for ev in events:
        if ev.punch_type == start_type and start_at is None:
            start_at = ev.punched_at
        elif ev.punch_type == end_type and start_at is not None:
            end_at = ev.punched_at
            if end_at > start_at:
                intervals.append((start_at, end_at))
            start_at = None
    return intervals


def _minutes_total(intervals: List[Tuple[datetime, datetime]]) -> int:
    total = 0
    for s, e in intervals:
        total += int((e - s).total_seconds() // 60)
    return max(total, 0)


def compute_day(punches: List[AttendancePunch]) -> DayCalcResult:
    """
    1日の打刻（ソート済み）から 勤務分／休憩分 を算出。
    - 勤務区間: IN→OUT のペア
    - 休憩区間: BREAK_START→BREAK_END のペア
    - 休憩は勤務時間から重複控除しない（IN/OUT が勤務の外側、BREAK が内側に入る設計を想定）
    """
    if not punches:
        return DayCalcResult()

    # 時系列に並べる
    punches = sorted(punches, key=lambda x: (x.punched_at, x.id))

    work_intervals = _pair_intervals(punches, PUNCH_IN, PUNCH_OUT)
    break_intervals = _pair_intervals(punches, BREAK_START, BREAK_END)

    work_min = _minutes_total(work_intervals)
    break_min = _minutes_total(break_intervals)

    return DayCalcResult(work_minutes=work_min, break_minutes=break_min)


def _base_hours_for_user(user) -> float:
    """所定労働時間（時間）。Employee があれば参照、なければ 8h。"""
    try:
        if Employee is not None:
            emp = Employee.objects.select_related(None).filter(user_id=user.id).first()
            if emp and getattr(emp, "base_hours_per_day", None) is not None:
                return float(emp.base_hours_per_day)
    except Exception:
        pass
    return 8.0


class SummaryAPIView(APIView):
    """
    GET /api/attendance/summary?from=YYYY-MM-DD&to=YYYY-MM-DD
      追加（任意）: &department=1&position=1&employee_code=E0001&user_id=123
    レスポンス:
    {
      "value": [
        {"date":"2025-10-18","work_minutes":0,"work_hours":0.0,"break_minutes":0,"overtime_minutes":0,"notes":[]},
        ...
      ]
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        start, end = parse_range(request)

        # ベースクエリ（期間）
        qs: QuerySet[AttendancePunch] = AttendancePunch.objects.filter(
            work_date__gte=start,
            work_date__lte=end,
        )

        # 権限：一般ユーザーは自分のみ
        if not is_hr_admin(user):
            qs = qs.filter(user=user)
        else:
            # HR管理者のみ使える拡張フィルタ
            dept_id = request.query_params.get("department")
            pos_id = request.query_params.get("position")
            ecode = request.query_params.get("employee_code")
            uid = request.query_params.get("user_id")

            # Employee を辿るフィルタは hr_core がある場合のみ
            if dept_id and Employee is not None:
                qs = qs.filter(user__employee__department_id=dept_id)
            if pos_id and Employee is not None:
                qs = qs.filter(user__employee__position_id=pos_id)
            if ecode and Employee is not None:
                qs = qs.filter(user__employee__employee_code=ecode)
            if uid:
                qs = qs.filter(user_id=uid)

        qs = qs.select_related("user").order_by("work_date", "punched_at", "id")

        # ユーザー×日付のバケット
        bucket: Dict[Tuple[int, date], List[AttendancePunch]] = defaultdict(list)
        for p in qs:
            bucket[(p.user_id, p.work_date)].append(p)

        # 日付ごとの集計（複数ユーザーが混在する場合は合算）
        results_by_date: Dict[date, Dict[str, int]] = {d: {"work": 0, "break": 0, "ot": 0} for d in daterange(start, end)}
        notes_by_date: Dict[date, List[str]] = {d: [] for d in daterange(start, end)}

        # 事前にユーザーごとの所定労働時間（h）をキャッシュ
        base_hours_cache: Dict[int, float] = {}

        for (uid, d), punches in bucket.items():
            # ユーザー別の所定労働時間（時間）
            if uid not in base_hours_cache:
                if Employee is not None:
                    try:
                        emp = Employee.objects.filter(user_id=uid).only("base_hours_per_day").first()
                        base_hours_cache[uid] = float(emp.base_hours_per_day) if emp and emp.base_hours_per_day is not None else 8.0
                    except Exception:
                        base_hours_cache[uid] = 8.0
                else:
                    base_hours_cache[uid] = 8.0

            calc = compute_day(punches)
            base_min = int(base_hours_cache[uid] * 60)

            work_min = int(calc.work_minutes)
            break_min = int(calc.break_minutes)
            ot_min = max(work_min - base_min, 0)

            results_by_date[d]["work"] += work_min
            results_by_date[d]["break"] += break_min
            results_by_date[d]["ot"] += ot_min

            # 備考（note）をメモ（重複排除）
            for p in punches:
                if p.note:
                    if p.note not in notes_by_date[d]:
                        notes_by_date[d].append(p.note)

        # レスポンス整形
        value = []
        for d in daterange(start, end):
            wm = results_by_date[d]["work"]
            bm = results_by_date[d]["break"]
            om = results_by_date[d]["ot"]
            value.append(
                {
                    "date": to_iso_date(d),
                    "work_minutes": wm,
                    "work_hours": round(wm / 60.0, 2),
                    "break_minutes": bm,
                    "overtime_minutes": om,
                    "notes": notes_by_date[d],
                }
            )

        return Response({"value": value, "Count": len(value)})



