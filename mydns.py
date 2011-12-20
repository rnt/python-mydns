#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: Milan Nikolic <gen2brain@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
from textwrap import dedent
from optparse import OptionParser, OptionValueError

import MySQLdb
from MySQLdb.cursors import DictCursor

MYSQL_DB = 'mydns'
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWD = 'password'

SOA_NS = 'ns1.example.com.'
SOA_MBOX = 'hostmaster.example.com.'
SOA_REFRESH = 43200
SOA_RETRY = 1800
SOA_EXPIRE = 2419200
SOA_MINIMUM = 10800
SOA_TTL = 86400
SOA_XFER = '8.8.8.8'

RR_AUX = 0
RR_TTL = 87600
RR_TYPES = ['A', 'AAAA', 'CNAME', 'HINFO', 'MX', 'NAPTR', 'NS', 'PTR', 'RP', 'SRV', 'TXT']

BUNDLE_NS = "ns1.example.com.,ns2.example.com.,ns3.example.com."

stdout = sys.stdout.write
stderr = sys.stderr.write

class MyDNS:
    """Interface to the MyDNS DB"""

    def __init__(self):
        """Connects to MySQL server"""
        try:
            self.db = MySQLdb.connect(
                    host=MYSQL_HOST, db=MYSQL_DB,
                    user=MYSQL_USER, passwd=MYSQL_PASSWD)
            self.dbc = self.db.cursor()
            self.dbd = self.db.cursor(DictCursor)
            self.origin = None
        except MySQLdb.Error, err:
            self.db = None
            stderr("Error: %s\n" % str(err))
            sys.exit(1)

    def __del__(self):
        """Closes MySQL connection"""
        if self.db:
            self.db.close()

    def get_origins(self):
        """Returns all origins"""
        self.dbc.execute("SELECT origin FROM soa ORDER BY origin")
        return self.dbc.fetchall()

    def set_origin(self, origin):
        """Sets current origin"""
        self.origin = origin

    def set_active(self, active='Y'):
        """Toggles 'active' column"""
        self.dbc.execute("UPDATE soa SET active='%s' WHERE origin = '%s'" % (
            active, self.origin))

    def get_soa(self):
        """Returns SOA record"""
        self.dbd.execute("SELECT * FROM soa WHERE origin = '%s'" % self.origin)
        return self.dbd.fetchone()

    def get_soa_id(self):
        """Returns SOA id"""
        self.dbc.execute("SELECT id FROM soa WHERE origin = '%s'" % self.origin)
        soa_id = self.dbc.fetchone()
        if soa_id:
            return soa_id[0]
        else:
            return None

    def get_next_soa_id(self):
        """Returns next SOA id"""
        self.dbc.execute("""SELECT auto_increment FROM information_schema.tables
                WHERE table_name='soa' AND table_schema='%s'""" % MYSQL_DB)
        return self.dbc.fetchone()[0]


    def create_soa(self, opts):
        """Creates new SOA record"""
        ns = (SOA_NS, opts.ns)[bool(opts.ns)]
        mbox = (SOA_MBOX, opts.mbox)[bool(opts.mbox)]
        serial = self.get_serial()
        refresh = (SOA_REFRESH, opts.refresh)[bool(opts.refresh)]
        retry = (SOA_RETRY, opts.retry)[bool(opts.retry)]
        expire = (SOA_EXPIRE, opts.expire)[bool(opts.expire)]
        minimum = (SOA_MINIMUM, opts.minimum)[bool(opts.minimum)]
        ttl = (SOA_TTL, opts.ttl)[bool(opts.ttl)]
        xfer = (SOA_XFER, opts.xfer)[bool(opts.xfer)]
        sql = """\
                INSERT INTO soa (origin,ns,mbox,serial,refresh,retry,expire,minimum,ttl,xfer,active)
                VALUES ('%s','%s','%s','%s','%s','%s','%s','%s','%s','%s','Y')""" % (
        self.origin,ns,mbox,serial,refresh,retry,expire,minimum,ttl,xfer)
        if opts.pretend:
            stdout("\n%s\n" % dedent(sql))
        else:
            try:
                self.dbc.execute(sql)
            except MySQLdb.Error, err:
                stderr("Error: %s\n" % str(err))

    def update_soa(self, opts):
        """Updates record in SOA table"""
        updates = []
        self.dbd.execute("""SELECT ns,mbox,refresh,retry,expire,minimum,ttl,xfer
                FROM soa WHERE origin = '%s'""" % self.origin)
        soa = self.dbd.fetchone()
        for key, value in soa.items():
            opt = eval("opts.%s" % key)
            if opt and str(opt) != str(value):
                updates.append((key, opt))

        if updates:
            sql = "UPDATE soa SET "
            count = len(updates)-1
            for num, update in enumerate(updates):
                key, value = update
                sql += "%s = '%s'" % (key, value)
                if num != count:
                    sql += ", "
            sql += " WHERE origin = '%s'" % self.origin
            if opts.pretend:
                stdout("%s\n" % sql)
                return False
            else:
                try:
                    self.dbc.execute(sql)
                    return True
                except MySQLdb.Error, err:
                    stderr("Error: %s\n" % str(err))
        return False

    def delete_soa(self, opts):
        zone = self.get_soa_id()
        sql = "DELETE FROM rr WHERE zone = %s" % zone
        if opts.pretend:
            stdout("\n%s\n" % sql)
        else:
            self.dbc.execute(sql)
        sql = "DELETE FROM soa WHERE origin = '%s'" % self.origin
        if opts.pretend:
            stdout("%s\n" % sql)
        else:
            try:
                self.dbc.execute(sql)
            except MySQLdb.Error, err:
                stderr("Error: %s\n" % str(err))

    def get_serial(self):
        """Returns new serial number"""
        return "%s%02d" % (time.strftime("%Y%m%d", time.localtime()), 1)

    def update_serial(self):
        """Updates serial number in SOA table"""
        self.dbc.execute("SELECT serial FROM soa WHERE origin = '%s'" % self.origin)
        date_serial = str(self.dbc.fetchone()[0])[:8]
        date_today = time.strftime("%Y%m%d", time.localtime())
        if date_serial == date_today:
            serial = 'serial + 1'
        else:
            serial = self.get_serial()
        self.dbc.execute("UPDATE soa SET serial = %s WHERE origin = '%s'" % (
            serial, self.origin))

    def get_rr(self, opts):
        """Returns data from RR table for current origin"""
        sql = """SELECT rr.zone,rr.name,rr.type,rr.data,rr.aux,rr.ttl
            FROM rr
            JOIN soa ON soa.id = rr.zone
            WHERE soa.origin = '%s' """ % self.origin
        if opts.type:
            sql += "AND rr.type in (%s) " % opts.type
        if opts.name:
            sql += "AND rr.name = '%s' " % opts.name
        if opts.data:
            sql += "AND rr.data = '%s' " % opts.data
        if opts.aux:
            sql += "AND rr.aux = '%s' " % opts.aux
        sql += "ORDER BY type, name, data"
        self.dbd.execute(sql)
        return self.dbd.fetchall()

    def create_rr(self, opts):
        """Creates new RR record"""
        zone = self.get_soa_id()
        if not zone:
            stderr("Error: origin '%s' doesn't exist.\n" % self.origin)
            return False
        name = opts.name
        if not name:
            stderr("Error: You must specify the name that describes RR (--name)\n")
            return False
        rrtype = opts.type
        if not rrtype:
            stderr("Error: You must specify DNS record type (--type)\n")
            return False
        else:
            if ',' in rrtype:
                stderr("Error: You must specify single DNS record type (--type)\n")
                return False
            else:
                rrtype = rrtype.strip("'")
        data = opts.data
        if not data:
            stderr("Error: You must specify the data associated with resource record (--data)\n")
            return False
        aux = (RR_AUX, opts.aux)[bool(opts.aux)]
        ttl = (RR_TTL, opts.rr_ttl)[bool(opts.rr_ttl)]

        sql = """\
            INSERT INTO rr (zone, name, type, data, aux, ttl)
            VALUES ('%s','%s','%s','%s','%s','%s')""" % (
            zone, name, rrtype, data, aux, ttl)
        if opts.pretend:
            stdout("\n%s\n" % dedent(sql))
        else:
            try:
                self.dbc.execute(sql)
            except MySQLdb.Error, err:
                stderr("Error: %s\n" % str(err))

    def update_rr(self, opts):
        """Updates records in RR table"""
        sql = """SELECT rr.id,rr.zone,rr.name,rr.type,rr.data,rr.aux,rr.ttl
            FROM rr
            JOIN soa ON soa.id = rr.zone
            WHERE soa.origin = '%s' """ % self.origin
        if opts.type:
            sql += "AND rr.type in (%s) " % opts.type
        if opts.name:
            sql += "AND rr.name = '%s' " % opts.name
        self.dbd.execute(sql)
        rr = self.dbd.fetchall()

        rr_ids = [r['id'] for r in rr]
        options = [("data", opts.data), ("aux", opts.aux), ("ttl", opts.rr_ttl)]
        options_set = [item for item in options if item[1]]
        count = len(options_set)-1

        if opts.data or opts.aux or opts.rr_ttl:
            for rr_id in rr_ids:
                sql = "UPDATE rr SET "
                for num, option in enumerate(options_set):
                    col, opt = option
                    if opt:
                        sql += "%s = '%s'" % (col, opt)
                        if num != count:
                            sql += ", "
                sql += " WHERE id = %d" % rr_id
                if opts.pretend:
                    stdout("\n%s\n" % sql)
                else:
                    try:
                        self.dbc.execute(sql)
                    except MySQLdb.Error, err:
                        stderr("Error: %s\n" % str(err))
            if not opts.pretend:
                return True
        return False

    def delete_rr(self, opts):
        zone = self.get_soa_id()
        sql = "DELETE FROM rr WHERE zone = %s " % zone
        if opts.type:
            sql += "AND rr.type in (%s) " % opts.type
        if opts.name:
            sql += "AND rr.name = '%s' " % opts.name

        if opts.pretend:
            stdout("\n%s\n" % sql)
            return False
        else:
            try:
                self.dbc.execute(sql)
                return True
            except MySQLdb.Error, err:
                stderr("Error: %s\n" % str(err))

    def create_bundle(self, opts):
        aux = (RR_AUX, opts.aux)[bool(opts.aux)]

        data = opts.data
        if not data:
            stderr("Error: You must specify the data associated with resource record (--data)\n")
            return False

        self.create_soa(opts)
        if not opts.pretend:
            zone = self.get_soa_id()
            if not zone:
                stderr("Error: origin '%s' doesn't exist.\n" % self.origin)
                return False
        else:
            zone = self.get_next_soa_id()

        for name in ['', '*', 'mail', 'www']:
            sql = """\
                INSERT INTO rr (zone, name, type, data, aux, ttl)
                VALUES ('%s','%s','%s','%s','%s','%s')""" % (
                zone, name, 'A', data, aux, '87600')
            if opts.pretend:
                stdout("%s\n" % dedent(sql))
            else:
                try:
                    self.dbc.execute(sql)
                except MySQLdb.Error, err:
                    stderr("Error: %s\n" % str(err))

        bundle_ns = (BUNDLE_NS, opts.bundle_ns)[bool(opts.bundle_ns)]
        nameservers = [val.strip() for val in bundle_ns.split(",") if val]
        for ns in nameservers:
            ns = trail_dot(ns)
            sql = """\
                INSERT INTO rr (zone, name, type, data, aux, ttl)
                VALUES ('%s','%s','%s','%s','%s','%s')""" % (
                zone, self.origin, 'NS', ns, aux, '87600')
            if opts.pretend:
                stdout("%s\n" % dedent(sql))
            else:
                try:
                    self.dbc.execute(sql)
                except MySQLdb.Error, err:
                    stderr("Error: %s\n" % str(err))

        for name in ['', '*']:
            sql = """\
                INSERT INTO rr (zone, name, type, data, aux, ttl)
                VALUES ('%s','%s','%s','%s','%s','%s')""" % (
                zone, name, 'MX', 'mail', aux, '604800')
            if opts.pretend:
                stdout("%s\n" % dedent(sql))
            else:
                try:
                    self.dbc.execute(sql)
                except MySQLdb.Error, err:
                    stderr("Error: %s\n" % str(err))


def trail_dot(arg):
    if arg and not arg.endswith('.'):
        return arg+'.'
    return arg

def rr_type(option, opt, value, parser):
    types = []
    rr_types = [val.strip() for val in value.split(",") if val]
    for rr_type in rr_types:
        if not rr_type.upper() in RR_TYPES:
            raise OptionValueError(
                    "Invalid %s '%s'.\nMust be one of the following: %s " % (
                option, rr_type, ", ".join(RR_TYPES)))
        else:
            types.append("'%s'" % rr_type)
    parser.values.type = ",".join(types)

def pad_str(left, string, width=40):
    left, string = str(left), str(string)
    str_width = len(left)
    return string.rjust(width-str_width)

def format_soa(soa):
    return """%s%s IN SOA %s %s (
                                        %s\t; serial
                                        %s%s
                                        %s%s
                                        %s%s
                                        %s%s
                                        )
""" % (soa['origin'], pad_str(soa['origin'], soa['ttl']), soa['ns'], soa['mbox'], soa['serial'],
        soa['refresh'], '\t\t; refresh '+format_time(soa['refresh']),
        soa['retry'], '\t\t; retry '+format_time(soa['retry']),
        soa['expire'], '\t\t; expire '+format_time(soa['expire']),
        soa['minimum'], '\t\t; minimum '+format_time(soa['minimum']))

def format_rr(origin, rrs):
    out = ""
    for rr in rrs:
        if rr['type'] == 'TXT': rr['data'] = '"%s"' % rr['data']
        if rr['type'] == 'MX': rr['data'] = "%s %s" % (rr['aux'], format_name(origin, rr['data']))
        name = format_name(origin, rr['name'])
        out += "%s%s IN %s %s\n" % (
        name, pad_str(name, rr['ttl']), rr['type'], rr['data'])
    return out

def format_name(origin, name):
    if origin in name:
        return name
    else:
        if name:
            return "%s.%s" % (name, origin)
        else:
            return origin

def format_time(seconds, add_s=False):
    time = []
    parts = [(' years', 60 * 60 * 24 * 7 * 52),
		     (' weeks', 60 * 60 * 24 * 7),
		     (' days', 60 * 60 * 24),
		     (' hours', 60 * 60),
		     (' minutes', 60),
		     (' seconds', 1)]
    for suffix, length in parts:
        value = seconds / length
        if value > 0:
			seconds = seconds % length
			time.append('%s%s' % (str(value),
					       (suffix, (suffix, suffix + 's')[value > 1])[add_s]))
        if seconds < 1:
			break
    return '(%s)' % ' '.join(time)

def parse_args():
    usage = "Usage: %prog <options> <args>\n"
    examples = """
Examples:
mydns.py --aux 10 --type A --name www example.com list_of_domains.txt --update
mydns.py --type A,MX example.com --delete-rr --pretend
mydns.py --list | grep "^exa" | mydns.py --deactivate
mydns.py --create-bundle --data 192.168.1.100 --bundle-ns "ns1.example.com,ns2.examplecom" list_of_domains.txt"""
    parser = OptionParser(usage=usage+examples)
    parser.add_option('--ns', action='store', dest='ns', type='string',
            help='the name of the name server. (default %s)' % SOA_NS)
    parser.add_option('--mbox', action='store', dest='mbox', type='string',
            help='mailbox of the person responsible for this zone. (default %s)' % SOA_MBOX)
    parser.add_option('--refresh', action='store', dest='refresh', type='string',
            help='''the number of seconds after which slave nameservers should check
to see if this zone has been changed. (default %s)''' % SOA_REFRESH)
    parser.add_option('--retry', action='store', dest='retry', type='string',
            help='''the number of seconds a slave nameserver should wait before retrying
if it attempts to transfer this zone but fails. (default %s)''' % SOA_RETRY)
    parser.add_option('--expire', action='store', dest='expire', type='string',
            help='''if for expire seconds the primary server cannot be reached, all information
about the zone is invalidated on the secondary servers. (default %s)''' % SOA_EXPIRE)
    parser.add_option('--minimum', action='store', dest='minimum', type='string',
            help='''the minimum TTL field that should be exported with
any RR from this zone. (default %s)''' % SOA_MINIMUM)
    parser.add_option('--ttl', action='store', dest='ttl', type='string',
            help='''the number of seconds that this zone may be cached before the
source of the information should again be consulted. (default %s)''' % SOA_TTL)
    parser.add_option('--xfer', action='store', dest='xfer', type='string',
            help='''IP addresses separated by commas that will be allowed
to transfer the zone. (default %s)''' % SOA_XFER)
    parser.add_option('--name', action='store', dest='name', type='string',
            help='the name that describes RR. (ex: www)')
    parser.add_option('--type', action='callback', dest='type', callback=rr_type, type='string',
            help='DNS record types, separated by commas. (%s)' % ",".join(RR_TYPES))
    parser.add_option('--data', action='store', dest='data', type='string',
            help='the data associated with resource record.')
    parser.add_option('--aux', action='store', dest='aux', type='string',
            help='''An auxillary numeric value in addition to data.
For `MX' records, this field specifies the preference.
For `SRV' records, this field specifies the priority.''')
    parser.add_option('--rr-ttl', action='store', dest='rr_ttl', type='string',
            help='''the number of seconds that resource record may be cached before the
source of the information should again be consulted. (default %s)''' % RR_TTL)
    parser.add_option('--activate', action='store_true', dest='activate',
            help='activate soa record')
    parser.add_option('--deactivate', action='store_true', dest='deactivate',
            help='deactivate soa record')
    parser.add_option('--list', action='store_true', dest='list',
            help='list all origins')
    parser.add_option('--pretend', action='store_true', dest='pretend',
            help='perform a dry run with no changes made (used with create/update/delete)')
    parser.add_option('--update', action='store_true', dest='update',
            help='update soa and rr records')
    parser.add_option('--create', action='store_true', dest='create',
            help='create soa record')
    parser.add_option('--create-rr', action='store_true', dest='create_rr',
            help='create rr records')
    parser.add_option('--delete', action='store_true', dest='delete',
            help='delete soa and all associated rr records')
    parser.add_option('--delete-rr', action='store_true', dest='delete_rr',
            help='delete rr records')
    parser.add_option('--create-bundle', action='store_true', dest='create_bundle',
            help='creates bundle (creates *,mail,www A records and also NS and MX records)')
    parser.add_option('--bundle-ns', action='store', dest='bundle_ns', type='string',
            help='bundle name servers, separated by commas.')
    opts, args = parser.parse_args()

    if not args and sys.stdin.isatty() and (
        not opts.list):
        parser.print_help()
        sys.exit(1)

    if not sys.stdin.isatty():
        args = []
        for arg in sys.stdin.readlines():
            args.append(arg.strip())

    for arg in args:
        if os.path.isfile(arg) and os.access(arg, os.R_OK):
            args.remove(arg)
            fd = open(arg, 'r')
            for line in fd.readlines():
                args.append(line.strip())
            fd.close()

    return opts, args

def main():
    mydns = MyDNS()
    opts, args = parse_args()

    if opts.list:
        for origin in mydns.get_origins():
            stdout("%s\n" % origin)
        sys.exit(0)

    for arg in args:
        origin = trail_dot(arg)
        opts.ns = trail_dot(opts.ns)
        opts.mbox = trail_dot(opts.mbox)
        mydns.set_origin(origin)

        if opts.create_bundle:
            mydns.create_bundle(opts)
            continue

        if opts.activate:
            mydns.set_active('Y')
            continue
        elif opts.deactivate:
            mydns.set_active('N')
            continue
        elif opts.create:
            mydns.create_soa(opts)
            continue
        elif opts.create_rr:
            mydns.create_rr(opts)
            continue
        elif opts.update:
            soa_upd = mydns.update_soa(opts)
            rr_upd = mydns.update_rr(opts)
            if soa_upd or rr_upd:
                mydns.update_serial()
            continue
        elif opts.delete:
            mydns.delete_soa(opts)
            continue
        elif opts.delete_rr:
            mydns.delete_rr(opts)
            continue

        soa = mydns.get_soa()
        if soa:
            stdout(format_soa(soa))
        rr = mydns.get_rr(opts)
        if rr:
            stdout(format_rr(origin, rr)+"\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
