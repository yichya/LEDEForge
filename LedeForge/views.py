import os
from django.views import View
from django.shortcuts import render_to_response


def default_context():
    return {
        "os": os.name
    }


class IndexView(View):
    def get(self, request):
        return render_to_response("frame.html", default_context())

