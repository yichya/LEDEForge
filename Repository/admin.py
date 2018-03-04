from django.contrib import admin
from Repository.models import RepositoryRegistration


# Register your models here.
class RepositoryRegistrationAdmin(admin.ModelAdmin):
    list_display = ['path']


admin.site.register(RepositoryRegistration, RepositoryRegistrationAdmin)
