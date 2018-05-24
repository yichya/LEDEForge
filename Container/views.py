import requests

from django.http import JsonResponse, Http404
from django.views import View

from Container.models import Container


class WorkerConnectView(View):
    def get(self, request, cid, path):
        container = Container.objects.filter(id=cid).first()
        uri = "".join([container.connection_string, path])
        response = requests.get(uri, params=request.GET)
        if response.status_code == 404:
            raise Http404(path)
        return JsonResponse(response.json(), safe=False)

    def post(self, container_id, path):
        pass
