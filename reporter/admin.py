from django.contrib import admin

from reporter.models import WorkUnit, OutputChunk


class WorkUnitAdmin(admin.ModelAdmin):
    readonly_fields = ['result_stdout']


admin.site.register(WorkUnit, WorkUnitAdmin)
admin.site.register(OutputChunk)
