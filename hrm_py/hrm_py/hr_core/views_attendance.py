# hr_core/views_attendance.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone as dt_tz
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from .models_attendance import AttendancePunch, PunchType
from .serializers_attendance import AttendancePunchSerializer, PunchCreateSerializer

# ---- タイムゾーン定義（zoneinfoで厳密に） ----
JST = ZoneInfo("Asia/Tokyo")

def _to_date_local(dt: datetime) -> datetime.date:
    """打刻の暦日をJSTで判定（aware/naiveどちらでも可）"""
    if timezone.is_naive(dt):
        # サーバ時刻（UTC想定）でaware化
        dt = dt.replace(tzinfo=dt_tz.utc)
    return dt.astimezone(JST).date()

def _parse_date(param: Optional[str]) -> Optional[datetime.date]:
    if not param:
        return None
    try:
        return datetime.strptime(param, "%Y-%m-%d").date()
    except Exception:
        return None

def _calc_daily_minutes(punches: List[AttendancePunch]) -> Dict[str, int]:
    punches = sorted(punches, key=lambda x: x.punched_at)
    work_min = 0
    break_min = 0
    current_in: Optional[datetime] = None
    break_start: Optional[datetime] = None

    for p in punches:
        t = p.punched_at
        if timezone.is_naive(t):
            t = t.replace(tzinfo=dt_tz.utc)

        if p.punch_type == PunchType.IN:
            current_in = t
            break_start = None
        elif p.punch_type == PunchType.BREAK_START and current_in is not None and break_start is None:
            break_start = t
        elif p.punch_type == PunchType.BREAK_END and current_in is not None and break_start is not None:
            if t > break_start:
                break_min += int((t - break_start).total_seconds() // 60)
            break_start = None
        elif p.punch_type == PunchType.OUT and current_in is not None:
            duration = int((t - current_in).total_seconds() // 60)
            work_min += max(0, duration - break_min)
            current_in = None
            break_start = None
            break_min = 0

    overtime_min = max(0, work_min - 8 * 60)
    return {"work_minutes": work_min, "break_minutes": break_min, "overtime_minutes": overtime_min}


# ------------- API -------------
import traceback

class AttendancePunchAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            s = PunchCreateSerializer(data=request.data)
            s.is_valid(raise_exception=True)
            pt = s.validated_data["type"]
            note = s.validated_data.get("note", "")
            punched_at: Optional[datetime] = s.validated_data.get("punched_at")

            if punched_at is None:
                punched_at = timezone.now()
            # aware化（naiveならJST基準で解釈→UTCに直す）
            if timezone.is_naive(punched_at):
                punched_at = punched_at.replace(tzinfo=JST).astimezone(dt_tz.utc)

            obj = AttendancePunch.objects.create(
                user=request.user,
                punch_type=pt,
                note=note,
                punched_at=punched_at,
            )
            return Response(AttendancePunchSerializer(obj).data, status=status.HTTP_201_CREATED)
        except Exception:
            print(traceback.format_exc())
            return Response({"detail": "server_error"}, status=500)


class AttendanceMyAPI(APIView):
    """
    GET /api/attendance/my?from=YYYY-MM-DD&to=YYYY-MM-DD
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            dfrom = _parse_date(request.query_params.get("from"))
            dto   = _parse_date(request.query_params.get("to"))
            if not dfrom or not dto or dfrom > dto:
                return Response({"detail": "from/to を YYYY-MM-DD で指定してください"}, status=400)

            # JSTの一日範囲 → UTCへ
            start_dt = datetime.combine(dfrom, datetime.min.time(), tzinfo=JST).astimezone(dt_tz.utc)
            end_dt   = datetime.combine(dto + timedelta(days=1), datetime.min.time(), tzinfo=JST).astimezone(dt_tz.utc)

            qs = AttendancePunch.objects.filter(
                user=request.user,
                punched_at__gte=start_dt,
                punched_at__lt=end_dt,
            ).order_by("punched_at")

            data = AttendancePunchSerializer(qs, many=True).data
            return Response(data)
        except Exception:
            print(traceback.format_exc())
            return Response({"detail": "server_error"}, status=500)


class AttendanceSummaryAPI(APIView):
    """
    GET /api/attendance/summary?from=YYYY-MM-DD&to=YYYY-MM-DD[&user_id=...]
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            dfrom = _parse_date(request.query_params.get("from"))
            dto   = _parse_date(request.query_params.get("to"))
            if not dfrom or not dto or dfrom > dto:
                return Response({"detail": "from/to を YYYY-MM-DD で指定してください"}, status=400)

            target_user = request.user
            user_id_param = request.query_params.get("user_id")
            if user_id_param and request.user.is_staff:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                target_user = User.objects.get(pk=int(user_id_param))

            start_dt = datetime.combine(dfrom, datetime.min.time(), tzinfo=JST).astimezone(dt_tz.utc)
            end_dt   = datetime.combine(dto + timedelta(days=1), datetime.min.time(), tzinfo=JST).astimezone(dt_tz.utc)

            qs = AttendancePunch.objects.filter(
                user=target_user,
                punched_at__gte=start_dt,
                punched_at__lt=end_dt,
            )

            punches_by_day: Dict[str, List[AttendancePunch]] = {}
            for p in qs:
                key = _to_date_local(p.punched_at).isoformat()
                punches_by_day.setdefault(key, []).append(p)

            value: List[Dict[str, Any]] = []
            cur = dfrom
            while cur <= dto:
                key = cur.isoformat()
                day_punches = punches_by_day.get(key, [])
                mins = _calc_daily_minutes(day_punches) if day_punches else {
                    "work_minutes": 0, "break_minutes": 0, "overtime_minutes": 0
                }
                value.append({
                    "date": key,
                    **mins,
                    "notes": [p.note for p in day_punches if p.note],
                })
                cur += timedelta(days=1)

            return Response({"value": value})
        except Exception:
            print(traceback.format_exc())
            return Response({"detail": "server_error"}, status=500)
