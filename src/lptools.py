"""
Liquid Planner tools
"""
from __future__ import print_function

import json
import sys
from datetime import datetime, timedelta
import argparse
import urllib2
from urllib import urlencode
import ConfigParser
import os.path

def create_arg_parser(description):
    """
    create arguments parser
    """
    parser = argparse.ArgumentParser(description=description)
    return parser


class VerboseHandler(urllib2.BaseHandler):
    """
    """
    def default_open(self, req):
        print("Fetching URL {}".format(req.get_full_url()), file=sys.stderr)


class LPAPI(object):
    """
    LiquidPlanner API class
    """
    def __init__(self, username, password, workspace, ignore_users=None,
                 verbose=False):
        self.uri = 'https://app.liquidplanner.com/api/workspaces/%s/' \
            % workspace
        self.verbose = verbose
        self.ignore_users = ignore_users or []
        self.ignore_users.extend([u'unassigned', u'everyone'])

        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='Application',
                                  uri=self.uri,
                                  user=username,
                                  passwd=password)
        handlers = [auth_handler]
        if verbose:
            handlers.append(VerboseHandler())
        opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(opener)

    def members(self):
        r = urllib2.urlopen(self.uri + 'members')
        memb = json.loads(r.read())
        return dict([(rec['id'], rec) for rec in memb
                     if rec['user_name'] not in self.ignore_users and
                        rec['email'] not in self.ignore_users])

    def tasks(self, include_done=False):
        uri = self.uri + 'tasks'
        if not include_done:
            uri += '?' + urlencode({'filter[]' : 'is_done is false'})
        r = urllib2.urlopen(uri)
        tasks = json.loads(r.read())
        for t in tasks:
            ts = t['updated_at']
            i = ts.rindex(u'+00:00')
            if i:
                ts = t['updated_at'][:i]
            t['updated_at'] = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%S')
        return tasks


def _get_members_tasks(args):
    lp = LPAPI(username=args.username,
               password=args.password,
               workspace=args.workspace,
               ignore_users=args.ignore_users,
               verbose=args.verbose)
    return lp.members(), lp.tasks()


def tasks(args):
    """
    'lptools tasks' subcommand
    """
    members, tasks = _get_members_tasks(args)
    since = datetime.now() - timedelta(days=args.days)
    if args.updated:
        tasks = [t for t in tasks if t['updated_at'] >= since]
    if args.notupdated:
        tasks = [t for t in tasks if t['updated_at'] < since]

    for t in tasks:
        if t['owner_id'] in members:
            name = members[t['owner_id']]['user_name'].encode('utf-8')
        else:
            name = "Unknown"
        print("{0:20}   {1:%d/%m/%Y %H:%M:%S}  {2:20}".format(
                  name, t['updated_at'], t['name'].encode('utf-8')))
    

def members(args):
    """
    'lptools members' subcommand
    """
    members, tasks = _get_members_tasks(args)
    since = datetime.now() - timedelta(days=args.days)
    
    if args.notupdating or args.updating:
        out_memb = set()
        
        for t in tasks:
            if t['updated_at'] >= since:
                out_memb.add(t['updated_by'])

        if args.notupdating:
            out_memb = set(members.keys()).difference(out_memb)
    else:
        out_memb = members.keys()

    for m_id in out_memb:
        print("{0[email]:>40}\t{0[user_name]:<30}".format(members[m_id]))


def lptools():
    """
    show all tasks not updated since a given date
    """
    parser = create_arg_parser("Show tasks in LiquidPlanner according to "
                               "various criteria")
    parser.add_argument('-w', '--workspace', type=int,
                        help="Liquidplanner Workspace")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Verbose")
    subparsers = parser.add_subparsers(help='subcommand help')
    parser_tasks = subparsers.add_parser('tasks', help='LiquidPlanner Tasks')
    parser_members = subparsers.add_parser('members',
                                           help='LiquidPlanner Members')
    parser_tasks.add_argument('-d', '--days', type=int,
                        help="The number of days since task was updated",
                        required=True)
    group = parser_tasks.add_mutually_exclusive_group()
    group.add_argument('-u', '--updated', action='store_true',
                       help="Show tasks that were updated in the last N days")
    group.add_argument('-n', '--notupdated', action='store_true',
                       help="Show tasks that were NOT updated in the last N days")
    parser_tasks.set_defaults(func=tasks)
    
    parser_members.add_argument('-d', '--days', type=int,
                                help='The number of days since task was updated',
                                required=True)
    group = parser_members.add_mutually_exclusive_group()
    group.add_argument('-u', '--updating', action='store_true',
                       help="Show members who have updated something")
    group.add_argument('-n', '--notupdating', action='store_true',
                       help="Show members who have not updated anything")
    parser_members.set_defaults(func=members)

    args = parser.parse_args()

    # after parsing arguments, parse the configuration file
    config = ConfigParser.ConfigParser(defaults=dict(ignore_users=None))
    config.read([os.path.expanduser('~/.lptools')])

    try:
        args.username = config.get('lptools', 'username')
        args.password = config.get('lptools', 'password')
        if not args.workspace:
            args.workspace = config.get('lptools', 'workspace')
        ignore_users = config.get('lptools', 'ignore_users')
        if ignore_users:
            args.ignore_users = [unicode(u) for u in ignore_users.split()]
        else:
            args.ignore_users = None
            
    except ConfigParser.Error:
        print("""\
Please create ~/.lptools with the following info:

[lptools]
username = <your LP username>
password = <your LP password>
workspace = <your workspace>
ignore_users = <list of ignored users>
""", file=sys.stderr)
        sys.exit(1)

    # call the subcommand
    return args.func(args)
