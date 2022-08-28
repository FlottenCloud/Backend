# Generated by Django 4.1 on 2022-08-28 08:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('openstack', '0004_rename_instance_ip_address_openstackinstance_ip_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='openstackinstance',
            name='instance_name',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='openstackinstance',
            name='stack_name',
            field=models.CharField(max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='openstackinstance',
            name='ip_address',
            field=models.GenericIPAddressField(null=True),
        ),
    ]
