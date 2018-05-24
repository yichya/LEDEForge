import os
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render_to_response


def default_context():
    return {
        "os": os.name
    }


class IndexView(View):
    def get(self, request):
        return render_to_response("frame.html", default_context())


class QueueOutputView(View):
    def get(self, request, queue_id):
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class QueueOutputFetchView(View):
    def get(self, request, queue_id):
        data = {}
        return JsonResponse(data, safe=False)
