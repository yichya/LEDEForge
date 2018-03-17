import os
from django.db import models

from Common.Utils.git import GitRepositoryAccess
from Common.Utils.docker import DockerContainerAccess
from Common.const import RepositoryType


class Repository(object):
    def __init__(self):
        pass

    @property
    def branch(self):
        raise NotImplementedError

    @property
    def tag(self):
        raise NotImplementedError

    @property
    def head_commit_id(self):
        raise NotImplementedError

    @property
    def lede_version(self):
        return {}

    @property
    def lede_kernel_version(self):
        raise NotImplementedError

    def lede_packages(self, keyword=None):
        raise NotImplementedError

    def serialize(self):
        return {
            'branch': self.branch,
            'tag': self.tag,
            'head_commit_id': self.head_commit_id,
        }

    def serialize_detail(self):
        serialize = self.serialize()
        serialize.update({
            'lede_kernel_version': self.lede_kernel_version,
        })
        return serialize


class RepositoryRegistration(models.Model):
    name = models.CharField(max_length=255, default='')
    repository_type = models.IntegerField(default=1)
    container_id = models.CharField(max_length=255, default='')
    path = models.CharField(max_length=255, default='')
    command_prefix = models.CharField(max_length=255, default='')

    @property
    def repository(self) -> Repository:
        if self.repository_type == RepositoryType.local.value:
            return LocalRepository(os.path.join(os.path.dirname(__file__), "../../", self.path))
        if self.repository_type == RepositoryType.docker.value:
            return DockerRepository(self.container_id, self.path, self.command_prefix)
        raise ValueError("%d is not a valid repository type" % self.repository_type)

    @classmethod
    def query(cls, id=None):
        query = cls.objects

        if id is not None:
            query = query.filter(id=id)

        return query

    @classmethod
    def query_all(cls):
        return cls.query().all()

    @classmethod
    def query_first_by_id(cls, id=None):
        return cls.query(id=id).first()

    def serialize(self):
        result = {
            'name': self.name,
            'path': self.path,
        }
        result.update(self.repository.serialize())
        return result

    def serialize_detail(self):
        result = {
            'name': self.name,
            'path': self.path,
            'lede_version': self.repository.lede_version,
        }
        result.update(self.repository.serialize_detail())
        return result


class LocalRepository(Repository):
    def __init__(self, path):
        super(LocalRepository, self).__init__()
        self.path = path
        self.repository = GitRepositoryAccess(self.path)

    @property
    def branch(self):
        pass

    @property
    def tag(self):
        pass

    @property
    def head_commit_id(self):
        return self.repository.commit

    @property
    def lede_version(self):
        return {}

    @property
    def lede_kernel_version(self):
        return {}

    def lede_packages(self, keyword=None):
        pass


class DockerRepository(Repository):
    def __init__(self, container_id, path, command_prefix):
        super(DockerRepository, self).__init__()
        self.container_id = container_id
        self.path = path
        self.command_prefix = command_prefix
        self.container_access = DockerContainerAccess(self.container_id, self.path, self.command_prefix)

    @property
    def branch(self):
        result = self.container_access.exec_command('git rev-parse --abbrev-ref HEAD')
        return str(result.output.decode()).split('\n')[0]

    @property
    def tag(self):
        result = self.container_access.exec_command('git describe --tags')
        return str(result.output.decode()).split('\n')[0]

    @property
    def head_commit_id(self):
        result = self.container_access.exec_command('git rev-parse HEAD')
        return str(result.output.decode()).split('\n')[0]

    @property
    def lede_version(self):
        result = self.container_access.exec_command('./scripts/getver.sh')
        return str(result.output.decode()).split('\n')[0]

    @property
    def lede_kernel_version(self):
        result = self.container_access.exec_command('cat include/kernel-version.mk | grep LINUX_KERNEL_HASH- | grep .')
        version_lines = str(result.output.decode())
        print(version_lines)
        versions = {}
        for version_line in version_lines.split('\n'):
            try:
                version = version_line.split('LINUX_KERNEL_HASH-')[1].split('=')
                versions[version[0].strip()] = version[1].strip()
            except:
                pass
        return versions

    def lede_packages(self, keyword=None):
        if keyword:
            command = './scripts/feeds search %s' % keyword
        else:
            command = './scripts/feeds list'
        result = self.container_access.exec_command(command)
        package_lines = str(result.output.decode())
        packages = {}
        for package_line in package_lines.split('\n'):
            try:
                package_detail = package_line.split('\t', maxsplit=1)
                packages[package_detail[0].strip()] = package_detail[1].strip()
            except:
                pass
        return packages

