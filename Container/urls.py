from django.conf.urls import url
from Container.views import (
    WorkerConnectView,
    ContainerDetailView,
    ContainerKconfigView,
    ContainerMakeView,
    ContainerProcessOutputView,
    ContainerPackagesView
)


container_api_urlpatterns = [
    url(r'^(?P<cid>[0-9]+)/worker/(?P<path>.*)$', WorkerConnectView.as_view(), name="container_worker_connector"),
]


container_view_urlpatterns = [
    url(r'^(?P<cid>[0-9]+)/detail/$', ContainerDetailView.as_view(), name="container_detail"),
    url(r'^(?P<cid>[0-9]+)/kconfig/$', ContainerKconfigView.as_view(), name="container_kconfig"),
    url(r'^(?P<cid>[0-9]+)/packages/$', ContainerPackagesView.as_view(), name="container_packages"),
    url(r'^(?P<cid>[0-9]+)/make/$', ContainerMakeView.as_view(), name="container_make"),
    url(r'^(?P<cid>[0-9]+)/process_output/(?P<pid>[0-9]+)/$', ContainerProcessOutputView.as_view(),
        name="container_process_output"),
]