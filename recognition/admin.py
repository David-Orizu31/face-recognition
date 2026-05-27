# recognition/admin.py
from django.contrib import admin
from .models import Person, FaceRecord

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')

@admin.register(FaceRecord)
class FaceRecordAdmin(admin.ModelAdmin):
    list_display = ('person', 'model_used', 'created_at')