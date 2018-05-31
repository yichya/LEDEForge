from django.http import JsonResponse
from django.shortcuts import render, render_to_response
from django.views import View

from Common.Utils.queue_manager import queue_manager
from Endpoint.models import EndPoint


class QueueOutputView(View):
    def get(self, request, queue_id):
        return render_to_response("endpoint/process_output.html", {"queue_id": queue_id})


class QueueOutputFetchView(View):
    def get(self, request, queue_id):
        data = queue_manager.get_all_contents_from_queue(queue_id)
        return JsonResponse(data, safe=False)


class EndpointListView(View):
    def get(self, request):
        return render_to_response("endpoint/list.html", {'endpoints': EndPoint.objects.all()})


class EndpointDetailView(View):
    def get(self, request, eid):
        return render_to_response("endpoint/detail.html", {'endpoint': EndPoint.objects.filter(id=eid).first()})


class DockerBuildView(View):
    def post(self, request, eid):
        endpoint = EndPoint.objects.filter(id=eid).first()
        path = request.POST.get("path", ".")
        queue_id = endpoint.docker_build_in_queue(path)
        return JsonResponse({'queue_id': queue_id})


class DockerRunView(View):
    def post(self, request, eid):
        endpoint = EndPoint.objects.filter(id=eid).first()
        image_id = request.POST.get("image_id")
        port = int(request.POST.get("port"))
        result = endpoint.docker_run_daemon(image_id, port)
        return JsonResponse(result)
