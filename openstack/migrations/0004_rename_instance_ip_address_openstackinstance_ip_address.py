# Generated by Django 4.1 on 2022-08-28 07:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0003_rename_instance_image_name_openstackinstance_image_name_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='openstackinstance',
            old_name='instance_ip_address',
            new_name='ip_address',
        ),
    ]