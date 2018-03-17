from git import repo


class GitRepositoryAccess(object):
    def __init__(self, path):
        self.path = path
        self.repository = repo.Repo(self.path)

    @property
    def commit(self):
        return self.repository.heads.master.commit

