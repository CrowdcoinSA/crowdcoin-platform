# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-04-02 03:02
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0037_auto_20170331_1409'),
    ]

    operations = [
        migrations.CreateModel(
            name='Merchant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trading_name', models.CharField(blank=True, max_length=100, null=True)),
                ('registered_name', models.CharField(blank=True, max_length=100, null=True)),
                ('registration_number', models.CharField(blank=True, max_length=50, null=True)),
                ('telephone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('website', models.URLField(blank=True, null=True)),
                ('street_address', models.TextField(blank=True, max_length=50, null=True)),
                ('suburb', models.CharField(blank=True, max_length=50, null=True)),
                ('city', models.CharField(blank=True, max_length=50, null=True)),
                ('province', models.CharField(blank=True, max_length=50, null=True)),
                ('postal_code', models.CharField(blank=True, max_length=10, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_account_number', models.CharField(blank=True, max_length=100, null=True)),
                ('bank_branch_code', models.CharField(blank=True, max_length=100, null=True)),
                ('payout_frequency', models.IntegerField(blank=True, default=1, null=True)),
                ('callback_url', models.URLField(blank=True, null=True)),
                ('pockets', models.ManyToManyField(blank=True, related_name='merchant_pockets', to='website.Pocket')),
            ],
        ),
        migrations.AddField(
            model_name='userprofile',
            name='city',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='postal_code',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='province',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='street_address',
            field=models.TextField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='suburb',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='merchant',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='merchant_profile', to='website.UserProfile'),
        ),
        migrations.AddField(
            model_name='merchant',
            name='sub_profiles',
            field=models.ManyToManyField(blank=True, related_name='merchant_sub_profiles', to='website.UserProfile'),
        ),
    ]
