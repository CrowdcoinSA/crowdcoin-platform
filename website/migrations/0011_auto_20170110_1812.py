# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-10 16:12
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0010_auto_20170110_1334'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simcard',
            name='actual_balance',
            field=models.FloatField(blank=True, default=0),
        ),
    ]
