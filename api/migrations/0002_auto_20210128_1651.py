# Generated by Django 3.1.4 on 2021-01-28 07:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='search',
            old_name='created_on',
            new_name='created_at',
        ),
    ]
