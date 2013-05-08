#!/usr/bin/env python

"""
 Author: Renato Covarrubias <rnt [at] rnt.cl>

 Based on Milan Nikolic <gen2brain [at] gmail.com> works.

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys
import time

import MySQLdb
from MySQLdb.cursors import DictCursor

stderr = sys.stderr.write

class mydns:
	"""Interface to the MyDNS DB"""

	def __init__(self, host, db, user, passwd):
		"""
Create a new mydns instance and connects to MySQL server.
		
import mydns        
dns = mydns.mydns(
		host='localhost',
		db='mydns',
		user='username',
		passwd='password')

NOTE:
	If passwd is None, we try to connect without password.
	Perhaps it seems idiotic, but mysql allows users without password.
		"""
		try:
			self._host = host
			self._dbname = db
			self._user = user
			if passwd is None:
				self.db = MySQLdb.connect(host=host, db=db, user=user)
			else:
				self.db = MySQLdb.connect(host=host, db=db, user=user, passwd=passwd)
			self.dbc = self.db.cursor()
			self.dbd = self.db.cursor(DictCursor)
		except MySQLdb.Error, err:
			self.db = None
			stderr("ERROR: %s\n" % str(err))
			sys.exit(1)

	def __del__(self):
		"""When this object die, closes MySQL connection"""
		if self.db:
			self.db.close()
	
	def _column_exists(self, table_name, column_name):
		"""Verify if a column exists on a table, return True|False."""
		if table_name not in ['soa', 'rr']:
			raise ValueError("Table '%s' doesn't supported'" % table_name)
		
		self.dbd.execute('SHOW columns FROM %s' % table_name)
		if len(filter(lambda x:x['Field']==column_name, self.dbd.fetchall())) == 0:
			return False
		else:
			return True

	def _set_active_soa(self, origin, active):
		"""Toggles 'active' column, if exists return True otherwise return False"""
		if self._column_exists('soa', 'active'):
			self.dbc.execute("UPDATE soa SET active='%s' WHERE origin = '%s'" % (
				active, self._trail_dot(origin) ))
			return True
		else:
			return False
	
	def _trail_dot(self, arg):
		"""Add the final dot to domains"""
		try:
			if not arg.endswith('.'):
				return arg+'.'
		except:
			pass
		return arg    

	def _filter_variables(self, table, item):
		"Function to filter arguments using on UPDATE by table"
		if item[1] is None:
		   return False
		if self._column_exists(table, item[0]):
		   return True
		else:
		   return False

	def _filter_variables_soa(self, item):
		"Function to filter soa arguments using on UPDATE"
		return self._filter_variables('soa', item)
	
	def _filter_variables_rr(self, item):
		"Function to filter rr arguments using on UPDATE"
		return self._filter_variables('rr', item)
	
	def _is_valid_type(self, rrtype):
		"""Return True if the RR type is valid, otherwise return False"""
		if rrtype.upper() in ['A', 'AAAA', 'CNAME', 'HINFO', 'MX', 'NAPTR', 'NS', 'PTR', 'RP', 'SRV', 'TXT']:
			return True
		else:
			return False
	
	
	def enable_soa(self, origin):
		"""
Enable SOA, see self._set_active_soa()
		
import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.enable_soa('test.domain.com.')
		"""
		return self._set_active_soa(origin, 'Y')
	
	def disable_soa(self, origin):
		"""
Disable SOA, see self._set_active_soa()
		
import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.disable_soa('test.domain.com.')
		"""
		return self._set_active_soa(origin, 'N')

	def get_origins(self):
		"""
Returns all origins

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
origins = dns.get_origins()
"""
		try:
			self.dbc.execute("SELECT origin FROM soa ORDER BY origin")
			return [x[0] for x in self.dbc.fetchall()]
		except MySQLdb.Error, err:
			stderr("ERROR in get_origins: %s\n" % str(err))

	def get_soa(self, id_origin):
		"""
Returns SOA record

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
origin = dns.get_soa(dns.get_soa_id('test.domain.com.'))
origin = dns.get_soa(1)
"""
		try:
			self.dbd.execute("SELECT * FROM soa WHERE id = '%s'" % id_origin )
			return self.dbd.fetchone()
		except MySQLdb.Error, err:
			stderr("ERROR in get_soa: %s\n" % str(err))

	def get_soa_id(self, origin):
		"""
Returns SOA id

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
soa_id = dns.get_soa_id('test.domain.com.')
"""
		try:
			self.dbc.execute("SELECT id FROM soa WHERE origin = '%s'" % self._trail_dot(origin))
			soa_id = self.dbc.fetchone()
			return int(soa_id[0])
		except Exception, err:
			stderr("ERROR in get_soa_id: %s\n" % str(err))
			return None

	def get_next_soa_id(self):
		"""
Returns next SOA id

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
next_soa_id = dns.get_next_soa_id()
"""
		try:
			self.dbc.execute("""SELECT auto_increment FROM information_schema.tables
				WHERE table_name='soa' AND table_schema='%s'""" % self._dbname)
			return self.dbc.fetchone()[0]
		except MySQLdb.Error, err:
			stderr("ERROR in get_next_soa_id: %s\n" % str(err))

	def origin_exists(self, origin):
		"""
Returns True if origin already exists

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
if dns.origin_exists('test.domain.com.'):
	print "test.domain.com exists :)"
else:
	print "test.domain.com not exists :('"

"""
		return bool(self.get_soa_id(origin))

	def create_soa(self, origin, ns, mbox, serial=1, refresh=900, retry=600, expire=86400, minimum=300, ttl=3600, xfer=None, active='Y'):
		"""
Creates new SOA record

import mydns
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.create_soa('test1.domain.com.', 'ns1.domain.com.', 'dns-admin.domain.com.')

NOTE: 'xfer' and 'active' arguments are only used if the columns exists.
		"""
		if origin is None or origin.strip()=='':
			raise ValueError("origin is not defined")
		
		if self.origin_exists(origin):
			raise ValueError("origin already exists")
			
		variables = locals()
		del variables['self']
		
		filter_variables = filter(self._filter_variables_soa, variables.items())
		
		sql = "INSERT INTO soa (%s) VALUES (%s)" % (
			','.join(["%s" % i[0] for i in filter_variables]),
			', '.join(["%r" % self._trail_dot(i[1]) for i in filter_variables]),
		)
					
		try:
			self.dbc.execute(sql)
			return True
		except MySQLdb.Error, err:
			stderr("ERROR in create_soa: %s\n" % str(err))
			return False

	def update_soa(self, id_origin, origin=None, ns=None, mbox=None, serial=None, refresh=None, retry=None, expire=None, minimum=None, force_increment=False, force_date_increment=False, ttl=None, xfer=None, active='Y'):
		"""
Updates record in SOA table

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.update_soa(dns.get_soa_id('test.domain.com.'), origin='foobar.domain.com.')

NOTE: 'xfer' and 'active' arguments are only used if the columns exists.
"""
		variables = locals()
		for i in ['self', 'id_origin', 'force_increment']:
			del variables[i]
		
		if serial is None or serial < self.get_serial(id_origin):
			variables['serial'] = self.get_new_serial(id_origin, force_increment, force_date_increment)
		
		filter_variables = filter(self._filter_variables_soa, variables.items())
		if len(filter_variables) == 1:
		   return False
		
		sql = "UPDATE soa SET %s WHERE id=%r" % (
			','.join(["%s=%r" % i for i in filter_variables]),
			id_origin)
	
		try:
			self.dbc.execute(sql)
			return True
		except MySQLdb.Error, err:
			stderr("ERROR in update_soa: %s\n" % str(err))
			return False

	def delete_soa(self, id_origin):
		"""
Deletes soa record

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.delete_soa(dns.get_soa_id('test.domain.com.'))
dns.delete_soa(1)
"""
		sql = "DELETE FROM rr WHERE zone = %d" % id_origin

		try:
			self.dbc.execute(sql)
		except MySQLdb.Error, err:
			stderr("ERROR in delete_soa, deleting rr: %s\n" % str(err))
			return False
			
		sql = "DELETE FROM soa WHERE origin = '%s'" % id_origin
		try:
			self.dbc.execute(sql)
			return True
		except MySQLdb.Error, err:
			stderr("ERROR in delete_soa, deleting soa: %s\n" % str(err))
			return False

	def get_serial(self, id_origin):
		"""
Get the origin serial        

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
serial = dns.get_serial(1)
serial = dns.get_serial(dns.get_soa_id('test.domain.com.'))
"""
		try:
			self.dbc.execute("SELECT serial FROM soa WHERE id=%r" % id_origin)
			return self.dbc.fetchone()[0]
		except MySQLdb.Error, err:
			stderr("ERROR in get_serial: %s\n" % str(err))
			return None

	def get_new_serial(self, id_origin, force_increment=False, force_date_increment=False):
		"""
Returns new serial number

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
new_serial = dns.get_new_serial(1)
new_serial = dns.get_new_serial(dns.get_soa_id('test.domain.com.'), force_increment=True)

NOTE 1: If the serial started in 1, after upgrade 1,970,010,100 may want to continue using increments of 1. That's what the argument force_increment exists. :P crazy ah?
NOTE 2: If you want to pass from serial < 1,970,010,100 to using serial from date, set force_date_increment=True ;)
"""
		if force_increment and force_date_increment:
			raise ValueError("force_increment and force_date_increment are mutually exclusive")
		
		old_serial = self.get_serial(id_origin)
		if not force_date_increment and (force_increment or old_serial < 1970010101 or old_serial/100 >= int(time.strftime("%Y%m%d"))):
			return int(old_serial+1)
		else:
			return int(time.strftime("%Y%m%d01"))

	def update_serial(self, id_origin, force_increment=False, force_date_increment=False):
		"""
Updates serial number in SOA table

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')
dns.update_serial(1)
dns.update_serial(1, force_increment=True, force_date_increment=False)

NOTE: For an explanation of the attribute force_increment or force_date_increment, please see self.get_new_serial()
"""
		try:
			self.dbc.execute("UPDATE soa SET serial = %r WHERE id = %r" % (
				self.get_new_serial(id_origin, force_increment, force_date_increment), id_origin))
			return True
		except Exception, err:
			stderr("ERROR in update_serial: %s\n", str(err))
			return False     

	def get_rr(self, rrid=None, zone=None, name=None, data=None, aux=None, ttl=None, rrtype=None):
		"""
Returns data from RR table

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')

# Search all register from domain test.domain.com
dns.get_rr(zone=dns.get_soa_id('test.domain.com.'))

# Search register with name start with 'dns'
dns.get_rr(name='dns%')

# Search register with type 'A' or 'AAAA'.
dns.get_rr(rrtype=['A', 'AAAA'])

# Search regiter from zone=1 and type 'A'
dns.get_rr(zone=1, rrtype='A')
"""
		
		variables = locals()
		# id and type are reserved words
		variables['id'] = variables['rrid']
		variables['type'] = variables['rrtype']
		del variables['self']
		del variables['rrid']
		del variables['rrtype']
		
		sql = "SELECT id,zone,name,type,data,aux,ttl FROM rr WHERE %s ORDER BY type, name, data"
			
		filter_variables = filter(self._filter_variables_rr, variables.items())
		if len(filter_variables) == 0:
		   return False
		
		sql = sql % ' AND '.join(
			["%s%s%r" % (
					i[0],
					" IN " if type(i[1]) is list else "=" if str(i[1]).find('%') == -1 else " LIKE ",
					i[1] if type(i[1]) is not list else tuple(i[1]))
				for i in filter_variables])

		try:
			self.dbd.execute(sql)
			return self.dbd.fetchall()
		except MySQLdb.Error, err:
			stderr("ERROR in get_rr: %s\n" % str(err))
			return None

	def create_rr(self, zone, name, data, aux=0, ttl=3600, rrtype='A'):
		"""
Creates new RR record

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')

dns.create_rr(dns.get_soa_id('test.domain.com.'), 'foobar', '127.0.0.1')
dns.create_rr(dns.get_soa_id('test.domain.com.'), 'lala', ['127.0.0.1', '127.0.0.2'])
"""
		if not self._is_valid_type(rrtype):
			raise ValueError("%s isn't a valid type" % rrtype)

		if type(data) is not list:
			data = [data]
	
		sql = "INSERT INTO rr (zone, name, type, data, aux, ttl) VALUES (%r,%r,%r,%r,%r,%r)"
	
		for d in data:
			try:
				self.dbc.execute(sql % (zone, name, rrtype.upper(), d, aux, ttl))
			except MySQLdb.Error, err:
				stderr("ERROR in create_rr: %s\n" % str(err))
				return False
		return True

	def update_rr(self, rrid, zone=None, name=None, data=None, aux=None, ttl=None, rrtype=None):
		"""
Updates records in RR table

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')

In [1]: dns.get_rr(4)[0]['id']
Out[1]: 4L

In [2]: dns.update_rr(4, data='10.80.12.50')
Out[2]: True
"""
		
		variables = locals()
		# type is a reserved word
		variables['type'] = variables['rrtype']
		del variables['self']
		del variables['rrtype']
		del variables['rrid']
		
		filter_variables = filter(self._filter_variables_rr, variables.items())
		if len(filter_variables) == 0:
		   return False
		
		sql = "UPDATE rr SET %s WHERE id=%r" % (
			','.join(["%s=%r" % i for i in filter_variables]),
			rrid)
	
		try:
			self.dbc.execute(sql)
			return True
		except MySQLdb.Error, err:
			stderr("ERROR in update_rr: %s\n" % str(err))
			return False

	def delete_rr(self, rrid=None, zone=None, name=None, data=None, aux=None, ttl=None, rrtype=None):
		"""
Deletes rr records

import mydns        
dns = mydns.mydns(host='localhost', db='mydns', user='username', passwd='password')

# Delete all register from domain test.domain.com
dns.delete_rr(zone=dns.get_soa_id('test.domain.com.'))

# Delete register with name start with 'dns'
dns.delete_rr(name='dns%')

# Delete all register with type 'A' or 'AAAA'.
dns.delete_rr(rrtype=['A', 'AAAA'])

# Delete register from zone=1 and type 'A'
dns.delete_rr(zone=1, rrtype='A')

# Delete register with id 42
dns.delete_rr(rrid=42)
"""
		variables = locals()
		# type is a reserved word
		variables['id'] = variables['rrid']
		variables['type'] = variables['rrtype']
		del variables['self']
		del variables['rrtype']
		del variables['rrid']
		
		filter_variables = filter(self._filter_variables_rr, variables.items())
		if len(filter_variables) == 0:
		   return False
		
		sql = "DELETE FROM rr WHERE %s" % (
			' AND '.join(
			["%s%s%r" % (
					i[0],
					" IN " if type(i[1]) is list else "=" if str(i[1]).find('%') == -1 else " LIKE ",
					i[1] if type(i[1]) is not list else tuple(i[1]))
				for i in filter_variables]))
		
		try:
			self.dbc.execute(sql)
			return True
		except MySQLdb.Error, err:
			stderr("ERROR in delete_rr: %s\n" % str(err))
			return False

# -*- coding: utf-8 -*-
