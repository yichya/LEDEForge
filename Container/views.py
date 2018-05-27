from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.views import View

from Container.models import Container


class ContainerAccessMixin(object):
    def container_get(self, cid, path, params):
        container = Container.objects.filter(id=cid).first()
        return container.connector.get(path, params)

    def container_post(self, cid, path, params, body):
        container = Container.objects.filter(id=cid).first()
        return container.connector.post(path, params, body)


class WorkerConnectView(ContainerAccessMixin, View):
    def get(self, request, cid, path):
        return JsonResponse(self.container_get(cid, path, request.GET), safe=False)

    def post(self, request, cid, path):
        return JsonResponse(self.container_post(cid, path, request.GET, request.POST), safe=False)


class ContainerListView(View):
    def get(self, request):
        return render_to_response("container/list.html")


class ContainerDetailView(ContainerAccessMixin, View):
    def get(self, request, cid):
        detail = self.container_get(cid, "", {})
        return render_to_response("container/detail.html", {'cid': cid, 'detail': detail})


class ContainerProcessOutputView(ContainerAccessMixin, View):
    def get(self, request, cid, pid):
        return render_to_response("container/process_output.html", {'cid': cid, 'pid': pid})


class ContainerMakeView(ContainerAccessMixin, View):
    def get(self, request, cid):
        detail = self.container_get(cid, "", {})
        return render_to_response("container/make.html", {'cid': cid, 'detail': detail})


class ContainerPackagesView(ContainerAccessMixin, View):
    def get(self, request, cid):
        keyword = request.GET.get("keyword", "")
        packages = self.container_get(cid, "package/", {'keyword': keyword})
        return render_to_response("container/packages.html", {'cid': cid, 'keyword': keyword, 'packages': packages})


class ContainerKconfigView(ContainerAccessMixin, View):
    def get(self, request, cid):
        sequence = request.GET.get("sequence", "")
        kconfig = self.container_get(cid, "kconfig/", {'sequence': sequence})
        return render_to_response("container/kconfig.html", {'cid': cid, 'sequence': sequence, 'kconfig': kconfig})


