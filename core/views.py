from django.views.generic import TemplateView

class UserManualView(TemplateView):
    template_name = 'core/user_manual.html'