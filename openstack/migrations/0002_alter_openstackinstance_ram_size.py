# Generated by Django 4.1 on 2022-08-23 07:18

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='openstackinstance',
            name='ram_size',
            field=models.FloatField(validators=[django.core.validators.MaxValueValidator(50)]),
        ),
    ]
