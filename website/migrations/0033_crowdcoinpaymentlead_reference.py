# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-18 15:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0032_auto_20170118_1631'),
    ]

    operations = [
        migrations.AddField(
            model_name='crowdcoinpaymentlead',
            name='reference',
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
    ]
