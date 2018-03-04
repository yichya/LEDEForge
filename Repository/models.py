import os
from django.db import models
from git import Repo


class RepositoryRegistration(models.Model):
    path = models.CharField(max_length=255)

    @property
    def repository(self):
        return Repository(os.path.join(os.path.dirname(__file__), "../../", self.path))


# Create your models here.
class Repository(object):
    def __init__(self, path):
        self.path = path
        self.repository = Repo(self.path)

    @property
    def commit(self):
        return self.repository.heads.master.commit
