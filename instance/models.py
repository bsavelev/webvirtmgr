from django.db import models
from servers.models import Compute
from vrtManager.instance import wvmInstance


class Instance(models.Model):
    compute = models.ForeignKey(Compute)
    name = models.CharField(max_length=255)
    uuid = models.CharField(max_length=36)
    # display_name = models.CharField(max_length=50)
    # display_description = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('compute', 'name')

    def get_conn(self):
        if not hasattr(self, '_conn'):
            conn = wvmInstance(
                self.compute.hostname,
                self.compute.login,
                self.compute.password,
                self.compute.type,
                self.name)
            setattr(self, '_conn', conn)
        return self._conn

    def start(self):
        conn = self.get_conn()
        conn.start()
