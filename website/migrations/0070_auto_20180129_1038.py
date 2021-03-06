# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2018-01-29 08:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0069_auto_20180125_1919'),
    ]

    operations = [
        migrations.AddField(
            model_name='pocket',
            name='payout_hold_days',
            field=models.IntegerField(default=7),
        ),
        migrations.AddField(
            model_name='pocket',
            name='payout_monthly_limit',
            field=models.DecimalField(decimal_places=2, default=10000, max_digits=20),
        ),
    ]
