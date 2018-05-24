from django.contrib import admin
from Container.models import EndPoint, Container, Registry
# Register your models here.

admin.site.register(EndPoint)
admin.site.register(Container)
admin.site.register(Registry)