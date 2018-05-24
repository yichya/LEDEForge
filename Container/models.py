from django.db import models
import requests
# Create your models here.


class Registry(models.Model):
    name = models.CharField(max_length=128)
    connection_string = models.CharField(max_length=255)


class EndPoint(models.Model):
    name = models.CharField(max_length=128)
    connection_string = models.CharField(max_length=255)


class Container(models.Model):
    name = models.CharField(max_length=128)
    endpoint_id = models.IntegerField()
    container_id = models.CharField(max_length=255)
    connection_string = models.CharField(max_length=255)
    data = models.TextField()

    def refresh_data(self):
        self.data = requests.get(self.connection_string).json()

