# Generated by Django 2.0.2 on 2018-05-23 16:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Container', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='container',
            old_name='date',
            new_name='data',
        ),
        migrations.AddField(
            model_name='container',
            name='connection_string',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]