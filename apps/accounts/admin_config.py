from django.contrib.admin.apps import AdminConfig


class MfaAdminConfig(AdminConfig):
    default_site = "apps.accounts.admin_site.MfaAdminSite"
