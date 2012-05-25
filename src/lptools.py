"""
Liquid Planner tools
"""

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


class LPAPI(object):
    """
    LiquidPlanner API class
    """
    def __init__(self, username, password, workspace):
        self.uri = 'https://app.liquidplanner.com/api/workspaces/%s/' \
            % workspace

        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password(realm='Application',
                                  uri=self.uri,
                                  user=username,
                                  passwd=password)

        opener = urllib2.build_opener(auth_handler)
        urllib2.install_opener(opener)

    def members(self):
        r = urllib2.urlopen(self.uri + 'members')
        memb = json.loads(r.read())
        return dict([(rec['id'], rec) for rec in memb])

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


def lptools():
    """
    show all tasks not updated since a given date
    """
    config = ConfigParser.ConfigParser()
    config.read([os.path.expanduser('~/.lptools')])

    try:
        username = config.get('lptools', 'username')
        password = config.get('lptools', 'password')
        workspace = config.get('lptools', 'workspace')
    except ConfigParser.Error:
        print >>sys.stderr, """\
Please create ~/.lptools with the following info:

[lptools]
username = <your LP username>
password = <your LP password>
workspace = <your workspace>
"""
        sys.exit(1)

    parser = create_arg_parser("Show tasks in LiquidPlanner according to "
                               "various criteria")
    parser.add_argument('-d', '--days', type=int,
                        help="The number of days since task was updated",
                        required=True)
    parser.add_argument('-w', '--workspace', type=int,
                        help="Liquidplanner Workspace")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-u', '--updated', action='store_true',
                       help="Show tasks that were updated in the last N days")
    group.add_argument('-n', '--notupdated', action='store_true',
                       help="Show tasks that were NOT updated in the last N days")
    args = parser.parse_args()
    since = datetime.now() - timedelta(days=args.days)

    lp = LPAPI(username=username,
               password=password,
               workspace=workspace)

    members = lp.members()
    tasks = lp.tasks()
    if args.updated:
        tasks = [t for t in tasks if t['updated_at'] >= since]
    if args.notupdated:
        tasks = [t for t in tasks if t['updated_at'] < since]

    for t in tasks:
        if t['owner_id'] in members:
            name = members[t['owner_id']]['user_name'].encode('utf-8')
        else:
            name = "Unknown"
        print "%20s   %20s   %s" % \
            (name, t['updated_at'], t['name'].encode('utf-8'))
