from django.contrib import admin
from .models import Tag, Search, Profile

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext as _
from .models import Tag, Search, Profile, User, Benchmark, Pricing, Hashtag


class UserAdmin(BaseUserAdmin):
    ordering = ['id']
    list_display = ['email']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ()}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                )
            }
        ),
        (_('Important dates'), {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')
        }),
    )


admin.site.register(User, UserAdmin)
admin.site.register(Benchmark)
admin.site.register(Profile)
admin.site.register(Tag)
admin.site.register(Search)
admin.site.register(Pricing)
admin.site.register(Hashtag)
