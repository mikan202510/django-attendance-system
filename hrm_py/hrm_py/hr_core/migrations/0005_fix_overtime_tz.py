# hr_core/migrations/0005_fix_overtime_tz.py
from django.db import migrations
from django.utils import timezone

def forwards(apps, schema_editor):
    OvertimeRequest = apps.get_model("hr_core", "OvertimeRequest")
    tz = timezone.get_default_timezone()
    for o in OvertimeRequest.objects.all():
        changed = False
        if o.start_datetime and timezone.is_naive(o.start_datetime):
            o.start_datetime = timezone.make_aware(o.start_datetime, tz)
            changed = True
        if o.end_datetime and timezone.is_naive(o.end_datetime):
            o.end_datetime = timezone.make_aware(o.end_datetime, tz)
            changed = True
        if changed:
            o.save(update_fields=["start_datetime", "end_datetime"])

def backwards(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [("hr_core", "0004_alter_department_options_alter_leaverequest_options_and_more")]
    operations = [migrations.RunPython(forwards, backwards)]
