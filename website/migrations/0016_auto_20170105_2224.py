# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-05 20:24
from __future__ import unicode_literals

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0015_auto_20170105_1321'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='default_pocket',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_profile_default_pocket', to='website.Pocket'),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='datetime',
            field=models.DateTimeField(auto_created=True, default=datetime.datetime(2017, 1, 5, 22, 24, 59, 450035)),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='pockets',
            field=models.ManyToManyField(related_name='user_profile_pocket', to='website.Pocket'),
        ),
    ]
