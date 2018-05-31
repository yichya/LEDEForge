from django.contrib import admin
from Container.models import Container, Registry
from Endpoint.models import EndPoint

# Register your models here.

admin.site.register(EndPoint)
admin.site.register(Container)
admin.site.register(Registry)