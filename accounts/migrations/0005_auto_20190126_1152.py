# Generated by Django 2.1 on 2019-01-26 10:52

from django.db import migrations


class Migration(migrations.Migration):

	dependencies = [
		('accounts', '0004_auto_20190113_1027'),
	]

	operations = [
		migrations.AlterModelOptions(
			name='userrating',
			options={'verbose_name': 'hodnotenie používateľa', 'verbose_name_plural': 'hodnotenia používateľov'},
		),
	]
