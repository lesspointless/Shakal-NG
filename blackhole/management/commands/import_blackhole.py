# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import sys
from collections import namedtuple
from datetime import datetime
from os import path

import pytz
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import connections
from django.utils.functional import cached_property

from ...models import Term
from accounts.models import User
from blackhole.models import VocabularyNodeType


#from common_utils.asciitable import NamedtupleTablePrinter


COMMENT_NODE_HIDDEN = 0
COMMENT_NODE_CLOSED = 1
COMMENT_NODE_OPEN = 2

NODE_NOT_PROMOTED = 0
NODE_PROMOTED = 1

NODE_NOT_STICKY = 0
NODE_STICKY = 1

USER_STATUS_BLOCKED = 0
USER_STATUS_ACTIVE = 1


FilterFormat = namedtuple('FilterFormat', ['format', 'name'])
NodeData = namedtuple('NodeData', ['nid', 'type', 'title', 'uid', 'status', 'created', 'changed', 'comment', 'promote', 'sticky', 'vid'])
TermData = namedtuple('TermData', ['tid', 'parent', 'vid', 'name', 'description'])
UserData = namedtuple('UserData', ['uid', 'name', 'signature', 'created', 'login', 'status', 'picture'])


FORMATS_TRANSLATION = {
	'Filtered HTML': 'html',
	'PHP code': 'html',
	'Full HTML': 'raw',
	'No HTML': 'text',
}


def timestamp_to_time(timestamp):
	return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)


def dot():
	sys.stdout.write(".")
	sys.stdout.flush()


class Command(BaseCommand):
	def __init__(self, *args, **kwargs):
		super(Command, self).__init__(*args, **kwargs)
		self.users_map = {}
		self.vocabulary_map = {}
		self.term_map = {}

	@cached_property
	def db_connection(self):
		return connections['blackhole']

	def db_cursor(self):
		return self.db_connection.cursor()

	@cached_property
	def filter_formats(self):
		cursor = self.db_cursor()
		cursor.execute('SELECT format, name FROM filter_formats')
		formats = tuple(FilterFormat(*row) for row in cursor.fetchall())
		return {f.format: FORMATS_TRANSLATION[f.name] for f in formats}

	@cached_property
	def vocabulary_format_types(self):
		cursor = self.db_cursor()
		cursor.execute('SELECT vid, type FROM vocabulary_node_types')
		return dict(cursor.fetchall())

	def nodes(self):
		cursor = self.db_cursor()
		cursor.execute('SELECT nid, type, title, uid, status, created, changed, comment, promote, sticky, vid FROM node')
		nodes = tuple(NodeData(row) for row in cursor.fetchall())
		for node in nodes:
			yield node

	def terms(self):
		cursor = self.db_cursor()
		cursor.execute('SELECT term_data.tid, term_hierarchy.parent, term_data.vid, term_data.name, description FROM term_data LEFT JOIN term_hierarchy ON term_data.tid = term_hierarchy.tid')
		return tuple(TermData(*row) for row in cursor.fetchall())

	def users(self):
		cursor = self.db_cursor()
		cursor.execute('SELECT uid, name, signature, created, login, status, picture FROM users')
		return tuple(UserData(*row) for row in cursor.fetchall())

	def create_user(self, username, user_data):
		is_active = user_data.status == 1
		avatar = None
		if user_data.picture:
			avatar_filename = path.join(settings.MEDIA_ROOT, 'blackhole', user_data.picture)
			try:
				avatar = SimpleUploadedFile(path.basename(avatar_filename), open(avatar_filename, 'rb').read())
			except IOError:
				print('File does not exist: ' + avatar_filename)
		user = User(
			username=username,
			signature=user_data.signature,
			date_joined=timestamp_to_time(user_data.created),
			last_login=timestamp_to_time(user_data.login),
			is_active=is_active,
			avatar=avatar or '',
		)
		user.save()
		return user

	def sync_users(self):
		users_map = {}
		for user in self.users():
			dot()
			username = user.name
			user_instance = User.objects.filter(username=username).first()
			if user_instance is not None and user_instance.password == '':
				users_map[user.uid] = user_instance.pk
				continue
			if user_instance is None:
				user_instance = self.create_user(username, user)
			else:
				username = 'blackhole_' + username
				user_instance = User.objects.filter(username=username).first()
				if user_instance is None:
					user_instance = self.create_user(username, user)
			users_map[user.uid] = user_instance.pk
		return users_map

	def sync_vocabulary(self):
		vocabulary_map = {}
		for vid, fmt in self.vocabulary_format_types.items():
			dot()
			instance, _ = VocabularyNodeType.objects.get_or_create(name=fmt)
			vocabulary_map[vid] = instance.pk
		return vocabulary_map

	def sync_term(self):
		term_map = {}
		terms = {}

		def import_term(term_data, parent):
			dot()
			instance = (Term.objects
				.filter(parent=parent, vocabulary_id=term_data.vid, name=term_data.name)
				.first())
			if instance is None:
				instance = Term(
					parent=parent,
					vocabulary_id=term_data.vid,
					name=term_data.name,
					description=term_data.description
				)
				instance.save()
			if parent:
				parent = Term.objects.get(pk=parent.pk)
			for subterm in terms.get(term_data.tid, []):
				import_term(subterm, instance)

		for term in self.terms():
			terms.setdefault(term.parent, [])
			terms[term.parent].append(term)
		if not 0 in terms:
			return term_map

		for term in terms[0]:
			import_term(term, None)

		return term_map

	def handle(self, *args, **options):
		print("Users")
		self.users_map = self.sync_users()
		print("")
		print("Vocabulary type")
		self.vocabulary_map = self.sync_vocabulary()
		print("")
		print("Term")
		self.term_map = self.sync_term()
		print("")