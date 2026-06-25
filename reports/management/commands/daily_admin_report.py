from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from reports.models import UserActivityLog, DailyReport


class Command(BaseCommand):
    help = "Generate daily admin activity report"

    def handle(self, *args, **options):
        today = timezone.localdate()

        self.stdout.write("=" * 80)
        self.stdout.write(f"RD_SYSTEM DAILY ADMIN REPORT - {today}")
        self.stdout.write("=" * 80)

        users = User.objects.filter(is_active=True).order_by("username")

        for user in users:
            logins = UserActivityLog.objects.filter(
                user=user,
                action="login",
                created_at__date=today,
            ).order_by("created_at")

            reports = DailyReport.objects.filter(
                created_by=user,
                reference_date=today,
            ).order_by("created_at")

            self.stdout.write("")
            self.stdout.write(f"USER: {user.username}")

            if logins.exists():
                self.stdout.write(f"  Logged in: YES")
                for login in logins:
                    self.stdout.write(
                        f"    - {login.created_at} | IP: {login.ip_address}"
                    )
            else:
                self.stdout.write("  Logged in: NO")

            if reports.exists():
                self.stdout.write("  Daily Reports:")
                for report in reports:
                    self.stdout.write(
                        f"    - Report #{report.id} | "
                        f"Project: {report.project} | "
                        f"Status: {report.status} | "
                        f"Created: {report.created_at} | "
                        f"Submitted: {report.submitted_at}"
                    )
            else:
                self.stdout.write("  Daily Reports: NONE")

            if logins.exists() and not reports.exists():
                self.stdout.write("  WARNING: Logged in but no report saved today.")

        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("END OF REPORT")
        self.stdout.write("=" * 80)
