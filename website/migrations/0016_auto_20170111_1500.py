# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-11 13:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0015_auto_20170111_1444'),
    ]

    operations = [
        migrations.AddField(
            model_name='bankdepositlead',
            name='transactions',
            field=models.ManyToManyField(blank=True, related_name='bank_deposit_lead_transactions', to='website.Transaction'),
        ),
        migrations.AddField(
            model_name='bankpaymentlead',
            name='transactions',
            field=models.ManyToManyField(blank=True, related_name='bank_payment_lead_transactions', to='website.Transaction'),
        ),
        migrations.AddField(
            model_name='crowdcoinpaymentlead',
            name='transactions',
            field=models.ManyToManyField(blank=True, related_name='crowdcoin_payment_lead_transactions', to='website.Transaction'),
        ),
    ]
