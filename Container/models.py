import json
import requests
from django.db import models
from django.http import Http404

from Endpoint.models import EndPoint


class WorkerConnector(object):
    def __init__(self, worker_connection_string):
        self.worker_connection_string = worker_connection_string
        self.requests_session = requests.session()

    def get(self, path, params):
        response = self.requests_session.get("".join([self.worker_connection_string, path]), params=params)
        if response.status_code == 404:
            raise Http404(path)
        return response.json()

    def post(self, path, params, body):
        response = self.requests_session.post("".join([self.worker_connection_string, path]), params=params, data=body)
        if response.status_code == 404:
            raise Http404(path)
        return response.json()


class Registry(models.Model):
    name = models.CharField(max_length=128)
    connection_string = models.CharField(max_length=255)


class Container(models.Model):
    name = models.CharField(max_length=128)
    endpoint_id = models.IntegerField()
    container_id = models.CharField(max_length=255)
    connection_string = models.CharField(max_length=255)
    data = models.TextField()

    def refresh_data(self):
        self.data = requests.get(self.connection_string).text
        self.save()

    @property
    def endpoint_name(self):
        if self.endpoint_id == 0:
            return ""
        endpoint = EndPoint.objects.filter(id=self.endpoint_id).first()
        if endpoint is None:
            return ""
        return endpoint.name

    @property
    def data_dict(self):
        return json.loads(self.data)

    @property
    def connector(self):
        return WorkerConnector(self.connection_string)
