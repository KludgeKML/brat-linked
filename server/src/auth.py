#!/usr/bin/env python
# -*- Mode: Python; tab-width: 4; indent-tabs-mode: nil; coding: utf-8; -*-
# vim:set ft=python ts=4 sw=4 sts=4 autoindent:

'''
Authentication and authorization mechanisms.

Author:     Pontus Stenetorp    <pontus is s u-tokyo ac jp>
            Illes Solt          <solt tmit bme hu>
Version:    2011-04-21
'''

from hashlib import sha256
from uuid import uuid1
from os.path import dirname, join as path_join, isdir, isfile
from sqlite3 import connect
import string
import random

try:
    from os.path import relpath
except ImportError:
    # relpath new to python 2.6; use our implementation if not found
    from common import relpath
from common import ProtocolError
from config import USER_PASSWORD, DATA_DIR, USER_DB
from message import Messager
from session import get_session, invalidate_session
from projectconfig import ProjectConfiguration


# To raise if the authority to carry out an operation is lacking
class NotAuthorisedError(ProtocolError):
    def __init__(self, attempted_action):
        self.attempted_action = attempted_action

    def __str__(self):
        return 'Login required to perform "%s"' % self.attempted_action

    def json(self, json_dic):
        json_dic['exception'] = 'notAuthorised'
        return json_dic


# File/data access denial
class AccessDeniedError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Access Denied'

    def json(self, json_dic):
        json_dic['exception'] = 'accessDenied'
        # TODO: Client should be responsible here
        Messager.error('Access Denied')
        return json_dic


class InvalidAuthError(ProtocolError):
    def __init__(self):
        pass

    def __str__(self):
        return 'Incorrect login and/or password'

    def json(self, json_dic):
        json_dic['exception'] = 'invalidAuth'
        return json_dic


def _is_authenticated(user, password):
	if not user_db_exists(USER_DB):
		# Uh oh. The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return False

	# Our database file exists, so grab the the hashed password for this user.
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("SELECT password_hash FROM users WHERE user_name=?", [user])
		user_data = curs.fetchone()
		conn.close()
	
		if user_data == None:
			# Oops. No such user. Obviously not authenticated, so return false.
			return False
		else:
			hashed_password = _password_hash(password)
			# Compare the input password with the stored one--user_data[0] is the stored sha256-hashed password.
			# If they match, we've got ourselves an authenticated user. 
			if(user_data[0] == hashed_password):
				return True
			else:
				return False

	except Error as e:
		# The database file exists, but something went wrong. Show the error, then go back. 
		# NB: Yes, catching a generic Error isn't ideal, but SQLite's exception hierarchy isn't terribly 
		# well-documented. 
		Messager.error("Database error--contact your administrator")
		return False


# Tiny function to see if the user database file exists. This is here 
# because SQLite is...not great at handling missing database files. It'll
# happily--and silently!--create a new database with the same name if the file
# we're trying to connect to is missing.  
def user_db_exists(user_db):
	if isfile(user_db):
		return True
	else:
		return False

		
def _password_hash(password):
    return sha256(password).hexdigest()

def login(user, password):
    if not _is_authenticated(user, password):
        raise InvalidAuthError

    get_session()['user'] = user
    Messager.info('Hello!')
    return {}

def logout():
    try:
        del get_session()['user']
    except KeyError:
        # Already deleted, let it slide
        pass
    # TODO: Really send this message?
    Messager.info('Bye!')
    return {}

def add_user(user_name,is_admin):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None

	# Generate a unique ID and a new random password for this user. We'll be returning the random password 
	# to the admin user (who should be the only person calling this function) later.
	# NB: Do we really need this unique ID? SQLite will generate ID integers if you configure a column as
	# INTEGER PRIMARY KEY. Can we use that, or is there a danger of reuse if/when users get deleted? 
	# probably not, but check. 
	# NB: Just setting it to an arbitrary length of 15 right now. We can also add punctuation into the mix later if 
	# this doesn't feel secure enough. 
	user_id = uuid1().hex
	password = ''.join(random.choice(string.ascii_uppercase + string.ascii.lowercase + string.digits) for _ in range(15))
	hashed_password = _password_hash(password)
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("INSERT INTO users VALUES (?,?,?,?)", (user_id,user_name,hashed_password,is_admin))
		conn.commit()
		conn.close()
		# All done. Hand back the password so the admin user can pass it on to the new user.
		return password
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")
		return None

	
def delete_user(user_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None
		
	# TODO: Delete annotations. If we're keeping database records of which documents
	# the user's touched, be sure to delete those too. 
	#
	# The process: Find user's annotations-> rewrite annotation files without those annotations ->
	# delete user records from "who touched what" table, then finally delete user account.
	# It'll be a lot neater if/when annotations are moved into the database instead of residing in text files. 
	#
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("DELETE FROM users WHERE user_name=?", [user_name])
		# Need to delete any of the user's group memberships as well. 
		curs.execute("DELETE FROM group_memberships WHERE user_name=?", [user_name])
		conn.commit()
		conn.close()
		# TODO: Pass back a return code here so the caller knows it worked?
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")

def change_password(user_name, new_password):
	# TODO: Check for authentication on the front end or back in here? 
	# Need to make sure the right person is calling this. 
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return 

	hashed_password = _password_hash(new_password)
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("UPDATE users SET password_hash = ? WHERE user_name = ?", (hashed_password, user_name))
		conn.commit()
		conn.close()
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")		

# TODO: Add "change group name" function for convenience later? It would save having to remove/re-add the group
# and repopulate it. 
def add_group(group_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None

	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("INSERT INTO groups(group_name) VALUES (?)", (group_name))
		conn.commit()
		conn.close()
		# All done. Hand back the password so the admin user can pass it on to the new user.
		return password
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error (group may already exist)--contact your administrator")
		return None

def delete_group(group_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None
		
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("DELETE FROM groups WHERE group_name=?", [group_name])
		# Need to delete any of the associated group memberships and permissions.
		curs.execute("DELETE FROM group_memberships WHERE group_name=?", [group_name])
		curs.execute("DELETE FROM doc_permissions WHERE group_name=?", [group_name])
		conn.commit()
		conn.close()
		# TODO: Pass back a return code here so the caller knows it worked?
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")
		
def add_user_to_group(user_name,group_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("INSERT INTO group_memberships(user_name, group_name) VALUES (?,?)", (user_name,group_name))
		conn.commit()
		conn.close()
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error (user may already be in group)--contact your administrator")
		return None

def delete_user_from_group(user_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None		
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("DELETE FROM group_memberships WHERE user_name=?", [user_name])
		conn.commit()
		conn.close()
		# TODO: Pass back a return code here so the caller knows it worked?
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")

def add_doc_permission(doc_path, group_name, can_write):
	# Bit of a difficulty here with can_write. First, an implementation detail...Python understands 
	# boolean types, obviously, but SQLite doesn't--to it, false is 0 and true is 1. There'd have to be
	# some mapping between types before we could store/retrieve the value. 
	#
	# Secondly, BRAT seems to expect everything that can be seen to be writeable. So, 
	# TODO: Determine if that can be made more granular. 
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("INSERT INTO doc_permissions(doc_path, group_name, can_write) VALUES (?,?)", (user_name,group_name,can_write))
		conn.commit()
		conn.close()
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error (permission may already be set)--contact your administrator")
		return None

#TODO: Add a second revocation method to revoke permissions for an entire document at once? 		
def revoke_doc_permission(group_name):
	if not user_db_exists(USER_DB):
		# The database file is missing, or USER_DB isn't set properly. Throw up an error message and go back. 
		Messager.error("User database not found--contact your administrator")
		return None		
	try:
		conn = connect(USER_DB)
		curs = conn.cursor()
		curs.execute("DELETE FROM doc_permissions WHERE group_name=?", [group_name])
		conn.commit()
		conn.close()
		# TODO: Pass back a return code here so the caller knows it worked?
	except Error as e:
		# See note in _is_authenticated about catching a generic Error.
		Messager.error("Database error--contact your administrator")
		
def whoami():
    json_dic = {}
    try:
        json_dic['user'] = get_session().get('user')
    except KeyError:
        # TODO: Really send this message?
        Messager.error('Not logged in!', duration=3)
    return json_dic

def allowed_to_read(real_path):
    data_path = path_join('/', relpath(real_path, DATA_DIR))
    # add trailing slash to directories, required to comply to robots.txt
    if isdir(real_path):
        data_path = '%s/' % ( data_path )
        
	#TODO: Replace this with database lookup, most likely in the doc_permissions table,
	# to see if the user has permissions. Comment out this bit, then skip down to 
	# after getting the username from the session info.
	#
    real_dir = dirname(real_path)	
    robotparser = ProjectConfiguration(real_dir).get_access_control()
    if robotparser is None:
        return True # default allow

	#TODO: NB to myself...here's where we grab the username. Should probably return False if the 
	# system falls back to "guest", as it seems to do before a user logs in. 
    try:
        user = get_session().get('user')
    except KeyError:
        user = None

    if user is None:
        user = 'guest'

    
	return robotparser.can_fetch(user, data_path)

# TODO: Unittesting
