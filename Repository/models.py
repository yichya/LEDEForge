import os
from django.db import models
from git import Repo


class RepositoryRegistration(models.Model):
    path = models.CharField(max_length=255)

    @property
    def repository(self):
        return LocalRepository(os.path.join(os.path.dirname(__file__), "../../", self.path))


class Repository(object):
    def __init__(self):
        pass


# Create your models here.
class LocalRepository(Repository):
    def __init__(self, path):
        super(LocalRepository, self).__init__()
        self.path = path
        self.repository = Repo(self.path)

    @property
    def commit(self):
        return self.repository.heads.master.commit


class DockerRepository(Repository):
    def __init__(self, container_id, path):
        super(DockerRepository, self).__init__()
        self.container_id = container_id
        self.path = path
