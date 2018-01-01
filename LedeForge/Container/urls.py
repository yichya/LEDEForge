from django.conf.urls import url

from LedeForge.Container.views import ContainerView, ContainerStatusView, ContainerExecView

container_urlpatterns = [
    url(r'^(?P<container_name>[a-f0-9]+)/status/$', ContainerStatusView.as_view(), name='container_status'),
    url(r'^(?P<container_name>[a-f0-9]+)/exec/$', ContainerExecView.as_view(), name='container_exec'),
    url(r'^$', ContainerView.as_view(), name='container'),
]
