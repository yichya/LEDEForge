from django.conf.urls import url
from Endpoint.views import EndpointListView, EndpointDetailView, QueueOutputFetchView, QueueOutputView, DockerBuildView, DockerRunView

endpoint_urlpatterns = [
    url(r"^list/$", EndpointListView.as_view(), name="endpoint_list"),
    url(r'^(?P<eid>[0-9]+)/$', EndpointDetailView.as_view(), name="endpoint_detail"),
    url(r'^(?P<eid>[0-9]+)/build/$', DockerBuildView.as_view(), name="endpoint_docker_build"),
    url(r'^(?P<eid>[0-9]+)/run/$', DockerRunView.as_view(), name="endpoint_docker_run"),
    url(r'^queue_fetch/(?P<queue_id>[a-f0-9]+)/$', QueueOutputFetchView.as_view(), name='queue_output_fetch'),
    url(r'^console/(?P<queue_id>[a-f0-9]+)/$', QueueOutputView.as_view(), name='queue_output'),
]