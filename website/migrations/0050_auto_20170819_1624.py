# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-19 14:24
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0049_onetimepin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='crowdcoinpaymentlead',
            name='pocket_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='crowdcoin_payment_lead_pocket_from', to='website.Pocket'),
        ),
    ]
