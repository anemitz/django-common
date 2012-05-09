from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

class NewUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined', 'action']
    list_filter = UserAdmin.list_filter + ('groups__name',)

    def action(self, obj):
        return '<a href="%s">Switch user</a>' % (reverse('common.views.su', args=[obj.id]))
    action.allow_tags = True
    action.short_description = 'Actions'

admin.site.unregister(User)
admin.site.register(User, NewUserAdmin)


