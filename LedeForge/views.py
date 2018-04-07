import os

from django.http import JsonResponse
from django.views import View
from django.shortcuts import render_to_response

from Common.Utils.queue_manager import queue_manager


def default_context():
    return {
        "os": os.name
    }


class IndexView(View):
    def get(self, request):
        return render_to_response("frame.html", default_context())


class TerminalView(View):
    def get(self, request, terminal_type, terminal_name):
        return render_to_response("terminal.html", {
            'terminal_type': terminal_type,
            'terminal_name': terminal_name
        })


class QueueOutputView(View):
    def get(self, request, queue_id):
        return render_to_response("queue.html", {
            "queue_id": queue_id
        })


class QueueOutputFetchView(View):
    def get(self, request, queue_id):
        data = queue_manager.get_all_contents_from_queue(queue_id)
        return JsonResponse(data, safe=False)
