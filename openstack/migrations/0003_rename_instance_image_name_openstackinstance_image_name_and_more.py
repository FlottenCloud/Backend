# Generated by Django 4.1 on 2022-08-28 07:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0002_remove_openstackinstance_volume_size_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='openstackinstance',
            old_name='instance_image_name',
            new_name='image_name',
        ),
        migrations.RenameField(
            model_name='openstackinstance',
            old_name='instance_status',
            new_name='status',
        ),
    ]
