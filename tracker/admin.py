from django.contrib import admin
from .models import Tracker, Entry, Note

# Register your models here.
admin.site.register(Tracker)
admin.site.register(Entry)
admin.site.register(Note)
