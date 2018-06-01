from django.contrib import admin

from Endpoint.models import EndPoint, Registry


admin.site.register(Registry)
admin.site.register(EndPoint)
