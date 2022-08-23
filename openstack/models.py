from django.db import models
from django.core.validators import MaxValueValidator

# Create your models here.
class OpenstackInstance(models.Model):
    flavor_id = models.CharField(max_length = 50)
    ram_size = models.FloatField(validators=[MaxValueValidator(50)])
    volume_size = models.IntegerField(validators = [MaxValueValidator(50)])