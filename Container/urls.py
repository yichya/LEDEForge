from django.conf.urls import url
from Container.views import WorkerConnectView

container_urlpatterns = [
    url(r'^(?P<cid>[0-9]+)/(?P<path>.*)$', WorkerConnectView.as_view())
]
