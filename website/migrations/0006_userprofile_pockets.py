# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-04 21:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0005_pocket_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='pockets',
            field=models.ManyToManyField(to='website.Pocket'),
        ),
    ]
