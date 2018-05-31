from django.shortcuts import render, render_to_response
from django.views import View

from Endpoint.models import EndPoint


class EndpointListView(View):
    def get(self, request):
        return render_to_response("endpoint/list.html", {'endpoints': EndPoint.objects.all()})


