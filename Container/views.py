import requests

from django.http import JsonResponse, Http404
from django.shortcuts import render_to_response
from django.views import View

from Container.models import Container


class WorkerConnector(object):
    def __init__(self, worker_connection_string):
        self.worker_connection_string = worker_connection_string
        self.requests_session = requests.session()

    def get(self, path, params):
        response = self.requests_session.get("".join([self.worker_connection_string, path]), params=params)
        if response.status_code == 404:
            raise Http404(path)
        return response.json()

    def post(self, path, params, body):
        response = self.requests_session.post("".join([self.worker_connection_string, path]), params=params, body=body)
        if response.status_code == 404:
            raise Http404(path)
        return response.json()


class WorkerConnectView(View):
    def get(self, request, cid, path):
        container = Container.objects.filter(id=cid).first()
        result = WorkerConnector(container.connection_string).get(path, request.GET)
        return JsonResponse(result, safe=False)

    def post(self, request, cid, path):
        container = Container.objects.filter(id=cid).first()
        result = WorkerConnector(container.connection_string).post(path, request.GET, request.POST)
        return JsonResponse(result, safe=False)


class ContainerListView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerDetailView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerProcessOutputView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerPackagesView(View):
    def get(self, request):
        return render_to_response("container/index.html")


class ContainerKconfigView(View):
    def get(self, request):
        return render_to_response("container/index.html")


