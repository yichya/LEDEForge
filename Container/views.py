import requests

from django.http import JsonResponse, Http404
from django.shortcuts import render_to_response
from django.views import View

from Container.models import Container


class WorkerConnectView(View):
    def get(self, request, cid, path):
        container = Container.objects.filter(id=cid).first()
        result = container.connector.get(path, request.GET)
        return JsonResponse(result, safe=False)

    def post(self, request, cid, path):
        container = Container.objects.filter(id=cid).first()
        result = container.connector.post(path, request.GET, request.POST)
        return JsonResponse(result, safe=False)


class ContainerListView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerDetailView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerProcessOutputView(View):
    def get(self, request, cid, pid):
        return render_to_response("container/index.html", {'cid': cid, 'pid': pid})


class ContainerPackagesView(View):
    def get(self, request, cid):
        keyword = self.request.GET.get("keyword", "")
        return render_to_response("container/index.html", {'cid': cid, 'keyword': keyword})


class ContainerKconfigView(View):
    def get(self, request, cid):
        sequence = self.request.GET.get("sequence", "")
        return render_to_response("container/index.html", {'cid': cid, 'sequence': sequence})


