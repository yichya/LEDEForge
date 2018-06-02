import json

from django.http import JsonResponse
from django.shortcuts import render_to_response
from django.template.defaultfilters import register
from django.utils.safestring import mark_safe
from django.views import View

from Container.models import Container


@register.filter(name='json')
def json_dumps(data):
    return mark_safe(json.dumps(data))


class ContainerAccessMixin(object):
    def container(self, cid):
        return Container.objects.filter(id=cid).first()

    def container_get(self, cid, path, params):
        container = self.container(cid)
        return container.connector.get(path, params)

    def container_post(self, cid, path, params, body):
        container = self.container(cid)
        return container.connector.post(path, params, body)


class WorkerConnectView(ContainerAccessMixin, View):
    def get(self, request, cid, path):
        return JsonResponse(self.container_get(cid, path, request.GET), safe=False)

    def post(self, request, cid, path):
        return JsonResponse(self.container_post(cid, path, request.GET, request.POST), safe=False)


class ContainerListView(View):
    def get(self, request):
        return render_to_response("container/list.html", {'containers': Container.objects.all()})

    def post(self, request):
        name = request.POST.get("name")
        endpoint_id = int(request.POST.get("endpoint_id"))
        container_id = request.POST.get("container_id")
        connection_string = request.POST.get("connection_string")
        if connection_string[-1] != '/':
            connection_string += "/"
        new_container = Container()
        new_container.name = name
        new_container.endpoint_id = endpoint_id
        new_container.container_id = container_id
        new_container.connection_string = connection_string
        new_container.data = new_container.connector.get("", {})
        new_container.save()
        return JsonResponse({"id": new_container.id})


class ContainerDetailView(ContainerAccessMixin, View):
    def get(self, request, cid):
        container = self.container(cid)
        container.refresh_data()
        detail = self.container_get(cid, "", {})
        return render_to_response("container/detail.html", {'cid': cid, 'detail': detail, 'container': container})


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


