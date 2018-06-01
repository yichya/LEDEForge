from django.conf.urls import url
from Endpoint.views import EndpointListView, EndpointDetailView, QueueOutputFetchView, QueueOutputView, DockerBuildView, DockerRunView, DockerPullView, DockerPushView, DockerContainerOpView

endpoint_urlpatterns = [
    url(r"^list/$", EndpointListView.as_view(), name="endpoint_list"),
    url(r'^(?P<eid>[0-9]+)/$', EndpointDetailView.as_view(), name="endpoint_detail"),
    url(r'^(?P<eid>[0-9]+)/build/$', DockerBuildView.as_view(), name="endpoint_docker_build"),
    url(r'^(?P<eid>[0-9]+)/run/$', DockerRunView.as_view(), name="endpoint_docker_run"),
    url(r'^(?P<eid>[0-9]+)/pull/$', DockerPullView.as_view(), name="endpoint_docker_pull"),
    url(r'^(?P<eid>[0-9]+)/push/$', DockerPushView.as_view(), name="endpoint_docker_push"),
    url(r'^(?P<eid>[0-9]+)/container_op/$', DockerContainerOpView.as_view(), name="endpoint_docker_container_op"),
    url(r'^queue_fetch/(?P<queue_id>[a-f0-9]+)/$', QueueOutputFetchView.as_view(), name='queue_output_fetch'),
    url(r'^console/(?P<queue_id>[a-f0-9]+)/$', QueueOutputView.as_view(), name='queue_output'),
]
