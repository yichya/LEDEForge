import docker
from django.db import models


# Create your models here.
class EndPoint(models.Model):
    name = models.CharField(max_length=128)
    connection_string = models.CharField(max_length=255)

    @property
    def connector(self):
        return docker.APIClient(self.connection_string)