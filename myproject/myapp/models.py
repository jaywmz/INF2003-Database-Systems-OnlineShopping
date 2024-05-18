from django.db import models

class YourModel(models.Model):
    char_field_name = models.CharField(max_length=200)
    int_field_name = models.IntegerField()