# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-04-21 10:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('osmdata', '0007_auto_20161023_0942'),
    ]

    operations = [
        migrations.AlterField(
            model_name='action',
            name='type',
            field=models.CharField(choices=[('remove', 'remove'), ('delete', 'delete'), ('modify', 'modify'), ('create', 'create')], max_length=10),
        ),
    ]
