# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-21 16:47
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0058_auto_20170821_1841'),
    ]

    operations = [
        migrations.AddField(
            model_name='airtimedeposittransaction',
            name='sim_card',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='airtime_deposit_transaction_sim_card', to='website.SimCard'),
        ),
    ]
