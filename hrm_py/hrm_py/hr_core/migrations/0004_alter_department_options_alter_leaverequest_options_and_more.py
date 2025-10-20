# hr_core/migrations/0004_safe_evolution.py  ← 実際は既存 0004_xxx.py に上書き
from django.db import migrations, models
from django.utils import timezone
import datetime


def forwards_fill_overtime_datetimes(apps, schema_editor):
    OvertimeRequest = apps.get_model("hr_core", "OvertimeRequest")

    # 旧カラム(date, start_time, end_time) から新カラムへコピー
    # 旧カラムがNULLの行は仮で now / +1h を入れる（必要なら業務仕様に合わせて修正）
    for obj in OvertimeRequest.objects.all():
        date = getattr(obj, "date", None)
        st   = getattr(obj, "start_time", None)
        et   = getattr(obj, "end_time", None)

        if date and st:
            obj.start_datetime = datetime.datetime.combine(date, st)
        else:
            obj.start_datetime = timezone.now()

        if date and et:
            obj.end_datetime = datetime.datetime.combine(date, et)
        else:
            obj.end_datetime = obj.start_datetime + datetime.timedelta(hours=1)

        obj.save(update_fields=["start_datetime", "end_datetime"])


def backwards_fill_overtime_datetimes(apps, schema_editor):
    # 必要なら逆変換を実装。不要ならpassでOK
    pass


class Migration(migrations.Migration):

    dependencies = [
                ("hr_core", "0003_attendancepunch"),
    ]

    operations = [
        # --- Metaの変更やテーブル名変更（Leave/Overtime）は、そのまま活かしてOK ---
        migrations.AlterModelOptions(
            name="department",
            options={"ordering": ("id",), "verbose_name": "部署", "verbose_name_plural": "部署"},
        ),
        migrations.AlterModelOptions(
            name="leaverequest",
            options={"ordering": ("-created_at",), "verbose_name": "休暇申請", "verbose_name_plural": "休暇申請"},
        ),
        migrations.AlterModelOptions(
            name="overtimerequest",
            options={"ordering": ("-created_at",), "verbose_name": "残業申請", "verbose_name_plural": "残業申請"},
        ),
        migrations.AlterModelOptions(
            name="position",
            options={"ordering": ("id",), "verbose_name": "役職", "verbose_name_plural": "役職"},
        ),

        # --- LeaveRequest のフィールド名リネーム（データ保持） ---
        migrations.RenameField(
            model_name="leaverequest",
            old_name="end_date",
            new_name="date_from",
        ),
        migrations.RenameField(
            model_name="leaverequest",
            old_name="start_date",
            new_name="date_to",
        ),

        # --- Department/Position の不要カラム削除（スキップ可：仕様通りなら削除） ---
        migrations.RemoveField(model_name="department", name="code"),
        migrations.RemoveField(model_name="department", name="is_active"),
        migrations.RemoveField(model_name="department", name="parent"),
        migrations.RemoveField(model_name="position", name="is_active"),
        migrations.RemoveField(model_name="position", name="rank"),

        # --- LeaveRequest の不要カラム削除（days/decided_at） ---
        migrations.RemoveField(model_name="leaverequest", name="days"),
        migrations.RemoveField(model_name="leaverequest", name="decided_at"),

        # --- LeaveRequest の updated_at 追加 ---
        migrations.AddField(
            model_name="leaverequest",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),

        # --- OvertimeRequest: 新カラム追加（まずは null=True で追加→データ移行→ null=False へ） ---
        migrations.AddField(
            model_name="overtimerequest",
            name="start_datetime",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="overtimerequest",
            name="end_datetime",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="overtimerequest",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),

        # --- OvertimeRequest: データ移行（旧→新） ---
        migrations.RunPython(forwards_fill_overtime_datetimes, backwards_fill_overtime_datetimes),

        # --- OvertimeRequest: 旧カラム削除（移行後に削除するのが重要） ---
        migrations.RemoveField(model_name="overtimerequest", name="date"),
        migrations.RemoveField(model_name="overtimerequest", name="decided_at"),
        migrations.RemoveField(model_name="overtimerequest", name="start_time"),
        migrations.RemoveField(model_name="overtimerequest", name="end_time"),
        migrations.RemoveField(model_name="overtimerequest", name="minutes"),

        # --- OvertimeRequest: 新カラムを NOT NULL に引き締め ---
        migrations.AlterField(
            model_name="overtimerequest",
            name="start_datetime",
            field=models.DateTimeField(null=False, blank=False),
        ),
        migrations.AlterField(
            model_name="overtimerequest",
            name="end_datetime",
            field=models.DateTimeField(null=False, blank=False),
        ),

        # --- ForeignKey/choices の変更（そのまま活かす） ---
        migrations.AlterField(
            model_name="leaverequest",
            name="approver",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="leave_approvals", to="auth.user"),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="leave_type",
            field=models.CharField(choices=[("ANNUAL", "年休"), ("SICK", "病欠"), ("OTHER", "その他")], default="ANNUAL", max_length=20),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="reason",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="leaverequest",
            name="status",
            field=models.CharField(choices=[("PENDING", "申請中"), ("APPROVED", "承認"), ("REJECTED", "却下"), ("CANCELED", "取消")], default="PENDING", max_length=20),
        ),
        migrations.AlterField(
            model_name="overtimerequest",
            name="approver",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="overtime_approvals", to="auth.user"),
        ),
        migrations.AlterField(
            model_name="overtimerequest",
            name="reason",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="overtimerequest",
            name="status",
            field=models.CharField(choices=[("PENDING", "申請中"), ("APPROVED", "承認"), ("REJECTED", "却下"), ("CANCELED", "取消")], default="PENDING", max_length=20),
        ),

        # --- テーブル名のリネーム（0004 に入っていた変更を踏襲） ---
        migrations.AlterModelTable(
            name="leaverequest",
            table="hr_core_leave_request",
        ),
        migrations.AlterModelTable(
            name="overtimerequest",
            table="hr_core_overtime_request",
        ),

        # --- Employee → EmployeeProfile を削除/作成ではなくリネームで保持 ---
        migrations.RenameModel(
            old_name="Employee",
            new_name="EmployeeProfile",
        ),

        # もし EmployeeProfile の Meta.db_table を “新しい名前” にしていたら、
        # 既存データのテーブル名を保ちたい場合は下行を有効化（旧テーブル名が hr_core_employee だと仮定）
        # migrations.AlterModelTable(
        #     name="employeeprofile",
        #     table="hr_core_employee",
        # ),
    ]
