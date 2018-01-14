# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-04 13:55
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmailTransaction',
        ),
        migrations.RemoveField(
            model_name='fundstransaction',
            name='network',
        ),
        migrations.RemoveField(
            model_name='fundstransaction',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='fundstransaction',
            name='transaction_type',
        ),
        migrations.RemoveField(
            model_name='marketproduct',
            name='profile',
        ),
        migrations.DeleteModel(
            name='NewsletterSubscription',
        ),
        migrations.RemoveField(
            model_name='prepaidlead',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='prepaidlead',
            name='supervisor',
        ),
        migrations.RemoveField(
            model_name='prepaidlead',
            name='transaction_type',
        ),
        migrations.RemoveField(
            model_name='referral',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='review',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='ussdsession',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='voicekeyword',
            name='profile',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='balance',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='date_of_birth',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='device_tag',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='from_quasar',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='gender',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='msisdn',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='thisisme_verified',
        ),
        migrations.DeleteModel(
            name='FundsTransaction',
        ),
        migrations.DeleteModel(
            name='MarketProduct',
        ),
        migrations.DeleteModel(
            name='PrepaidLead',
        ),
        migrations.DeleteModel(
            name='Referral',
        ),
        migrations.DeleteModel(
            name='Review',
        ),
        migrations.DeleteModel(
            name='TransactionType',
        ),
        migrations.DeleteModel(
            name='UssdSession',
        ),
        migrations.DeleteModel(
            name='VoiceKeyword',
        ),
    ]
