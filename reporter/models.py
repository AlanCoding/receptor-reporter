from django.db import models


class WorkUnit(models.Model):
    unit_id = models.CharField(primary_key=True, max_length=10)

    def result_stdout(self):
        return '\n'.join([chunk.stdout for chunk in self.outputchunk_set.order_by('counter')])


class OutputChunk(models.Model):
    work_unit = models.ForeignKey(WorkUnit, on_delete=models.DO_NOTHING)
    stdout = models.TextField()
    counter = models.IntegerField()
