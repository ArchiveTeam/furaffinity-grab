from distutils.version import StrictVersion
import datetime
import hashlib
import os
import random
import re
import socket
import shutil
import time
import sys

import seesaw
from seesaw.config import realize, NumberConfigValue
from seesaw.externalprocess import WgetDownload, ExternalProcess
from seesaw.item import ItemInterpolation, ItemValue
from seesaw.pipeline import Pipeline
from seesaw.project import Project
from seesaw.task import SimpleTask, SetItemKey, LimitConcurrent
from seesaw.tracker import PrepareStatsForTracker, GetItemFromTracker, \
    UploadWithTracker, SendDoneToTracker
from seesaw.util import find_executable


# check the seesaw version
if StrictVersion(seesaw.__version__) < StrictVersion("0.8.3"):
    raise Exception("This pipeline needs seesaw version 0.8.3 or higher.")


###########################################################################
# Find a useful Wpull executable.
#
# WPULL_EXE will be set to the first path that
# 1. does not crash with --version, and
# 2. prints the required version string
WPULL_EXE = find_executable(
    "Wpull",
    re.compile(r"\b1\.0\b"),
    [
        "./wpull",
        os.path.expanduser("~/.local/share/wpull-1.0/wpull"),
        os.path.expanduser("~/.local/bin/wpull"),
        "./wpull_bootstrap",
        "wpull",
    ]
)

if not WPULL_EXE:
    raise Exception("No usable Wpull found.")


###########################################################################
# The version number of this pipeline definition.
#
# Update this each time you make a non-cosmetic change.
# It will be added to the WARC files and reported to the tracker.
VERSION = "20150000.01"
# USER_AGENT = 'ArchiveTeam'
TRACKER_ID = 'furaffinity'
TRACKER_HOST = 'localhost:9080'
DISCO_TRACKER_URL = 'http://localhost:8058'

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/600.3.18 (KHTML, like Gecko) Version/8.0.3 Safari/600.3.18',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:36.0) Gecko/20100101 Firefox/36.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/40.0.2214.115 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.89 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.3; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.76 Safari/537.36',
    ]


def make_user_agent(seed):
    rand = random.Random(seed)

    user_agent = rand.choice(USER_AGENTS)
    user_agent += ' ArchiveTeam (compatible)'

    return user_agent

user_agent = make_user_agent(realize(downloader))


###########################################################################
# This section defines project-specific tasks.
#
# Simple tasks (tasks that do not need any concurrency) are based on the
# SimpleTask class and have a process(item) method that is called for
# each item.


class CheckIP(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "CheckIP")
        self._counter = 0

    def process(self, item):
        if self._counter <= 0:
            item.log_output('Checking IP address.')
            ip_set = set()

            ip_set.add(socket.gethostbyname('twitter.com'))
            ip_set.add(socket.gethostbyname('facebook.com'))
            ip_set.add(socket.gethostbyname('youtube.com'))
            ip_set.add(socket.gethostbyname('microsoft.com'))
            ip_set.add(socket.gethostbyname('icanhas.cheezburger.com'))
            ip_set.add(socket.gethostbyname('archiveteam.org'))

            if len(ip_set) != 6:
                item.log_output('Got IP addresses: {0}'.format(ip_set))
                item.log_output(
                    'You are behind a firewall or proxy. That is a big no-no!')
                raise Exception(
                    'You are behind a firewall or proxy. That is a big no-no!')

        # Check only occasionally
        if self._counter <= 0:
            self._counter = 10
        else:
            self._counter -= 1


class PrepareDirectories(SimpleTask):
    def __init__(self, warc_prefix):
        SimpleTask.__init__(self, "PrepareDirectories")
        self.warc_prefix = warc_prefix

    def process(self, item):
        item_name = item["item_name"]
        # escaped_item_name = item_name.replace(':', '_').replace('/', '_')
        escaped_item_name = hashlib.sha1(item_name.encode('ascii')).hexdigest()
        item['escaped_item_name'] = escaped_item_name

        dirname = "/".join((item["data_dir"], escaped_item_name))

        if os.path.isdir(dirname):
            shutil.rmtree(dirname)

        os.makedirs(dirname)

        item["item_dir"] = dirname
        item["warc_file_base"] = "%s-%s-%s" % (
            self.warc_prefix, escaped_item_name,
            time.strftime("%Y%m%d-%H%M%S")
        )

        open("%(item_dir)s/%(warc_file_base)s.warc.gz" % item, "w").close()


class MoveFiles(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "MoveFiles")

    def process(self, item):
        # Check if wget was compiled with zlib support
        if os.path.exists("%(item_dir)s/%(warc_file_base)s.warc" % item):
            raise Exception('Please compile wget with zlib support!')

        os.rename("%(item_dir)s/%(warc_file_base)s.warc.gz" % item,
                  "%(data_dir)s/%(warc_file_base)s.warc.gz" % item)

        shutil.rmtree("%(item_dir)s" % item)


def get_hash(filename):
    with open(filename, 'rb') as in_file:
        return hashlib.sha1(in_file.read()).hexdigest()


CWD = os.getcwd()
PIPELINE_SHA1 = get_hash(os.path.join(CWD, 'pipeline.py'))
SCRIPT_SHA1 = get_hash(os.path.join(CWD, 'furaffinity.py'))
HELPER_SHA1 = get_hash(os.path.join(CWD, 'helper.py'))


def stats_id_function(item):
    # For accountability and stats.
    d = {
        'pipeline_hash': PIPELINE_SHA1,
        'script_hash': SCRIPT_SHA1,
        'helper_hash': HELPER_SHA1,
        'python_version': sys.version,
    }

    return d


class WgetArgs(object):
    def realize(self, item):
        wget_args = [
            WPULL_EXE,
            "-nv",
            "-4",
            "--user-agent", user_agent,
            "--python-script", "furaffinity.py",
            "-o", ItemInterpolation("%(item_dir)s/wpull.log"),
            "--no-check-certificate",
            "--database", ItemInterpolation("%(item_dir)s/wpull.db"),
            "--delete-after",
            "--no-robots",
            "--load-cookies", ItemInterpolation("%(item_dir)s/cookies.txt"),
            "--rotate-dns",
            "--recursive", "--level=inf",
            "--no-parent",
            "--page-requisites",
            "--span-hosts-allow", "page-requisites",
            "--timeout", "60",
            "--tries", "inf",
            "--wait", "1",
            "--random-wait",
            "--waitretry", "30",
            # "--domains", "furaffinity.net,facdn.net",
            "--warc-file", ItemInterpolation("%(item_dir)s/%(warc_file_base)s"),
            "--warc-header", "operator: Archive Team",
            "--warc-header", "furaffinity-dld-script-version: " + VERSION,
            "--warc-header", ItemInterpolation("furaffinity-user: %(item_name)s"),
        ]

        item_type, item_value = item['item_name'].split(':', 1)

        if item_type == 'profile':
            username = item_value
            assert ',' not in username, 'multi user not supported {0}'.format(item_value)

            wget_args.extend([
                'https://www.furaffinity.net/user/{}/'.format(username),
                'https://www.furaffinity.net/commissions/{}/'.format(username),
                'https://www.furaffinity.net/journals/{}/'.format(username),
                'https://www.furaffinity.net/gallery/{}/'.format(username),
                'https://www.furaffinity.net/scraps/{}/'.format(username),
                'https://www.furaffinity.net/favorites/{}/'.format(username),
            ])
        elif item_type == 'journal':
            start_num, end_num = item_value.split('-', 1)

            for num in range(start_num, end_num + 1):
                wget_args.append(
                    'https://www.furaffinity.net/journal/{}/'.format(num)
                )

        elif item_type == 'submission':
            start_num, end_num = item_value.split('-', 1)

            for num in range(start_num, end_num + 1):
                wget_args.extend([
                    'https://www.furaffinity.net/view/{}/'.format(num),
                    'https://www.furaffinity.net/full/{}/'.format(num),
                ]
            )

        else:
            raise Exception('Unknown item type.')

        if 'bind_address' in globals():
            wget_args.extend(['--bind-address', globals()['bind_address']])
            print('')
            print('*** Wget will bind address at {0} ***'.format(
                globals()['bind_address']))
            print('')

        return realize(wget_args, item)


###########################################################################
# Initialize the project.
#
# This will be shown in the warrior management panel. The logo should not
# be too big. The deadline is optional.
project = Project(
    title="Furaffinity",
    project_html="""
        <img class="project-logo" alt="Project logo" src="http://archiveteam.org/images/1/1b/Fa_logo.png" height="50px" title=""/>
        <h2>FurAffinity
            <span class="links">
                <a href="http://furaffinity.net/">Website</a> &middot;
                <a href="http://tracker.archiveteam.org/furaffinity">Leaderboard</a> &middot;
                <a href="http://archiveteam.org/index.php?title=FurAffinity">Wiki</a>
            </span>
        </h2>
        <p>Downloading FurAffinity</p>
        <!--<p class="projectBroadcastMessage"></p>-->
    """,
    # utc_deadline=datetime.datetime(2000, 1, 1, 23, 59, 0)
)

pipeline = Pipeline(
    CheckIP(),
    GetItemFromTracker("http://%s/%s" % (TRACKER_HOST, TRACKER_ID), downloader,
                       VERSION),
    PrepareDirectories(warc_prefix="furaffinity"),
    ExternalProcess(
        'Begin',
        [sys.executable, 'helper.py', 'begin'],
        env={
            'user_agent': user_agent,
            'bind_address': globals().get('bind_address', ''),
            'disco_tracker': DISCO_TRACKER_URL,
            "item_dir": ItemValue("item_dir"),
        },
        accept_on_exit_code=[0],
    ),
    LimitConcurrent(
        NumberConfigValue(
            min=1, max=6, default=globals().get("num_procs", "1"),
            name="shared:fadisco:num_procs", title="Number of Processes",
            description="The maximum number of concurrent download processes."
        ),
        WgetDownload(
            WgetArgs(),
            max_tries=1,
            accept_on_exit_code=[0, 4, 7, 8],
            env={
                "item_dir": ItemValue("item_dir"),
                "downloader": downloader
            }
        ),
    ),
    ExternalProcess(
        'End',
        [sys.executable, 'helper.py', 'end'],
        env={
            'user_agent': user_agent,
            'bind_address': globals().get('bind_address', ''),
            'disco_tracker': DISCO_TRACKER_URL,
            "item_dir": ItemValue("item_dir"),
        },
        accept_on_exit_code=[0],
    ),
    PrepareStatsForTracker(
        defaults={"downloader": downloader, "version": VERSION},
        file_groups={
            "data": [
                ItemInterpolation("%(item_dir)s/%(warc_file_base)s.warc.gz"),
            ]
        },
        id_function=stats_id_function,
    ),
    MoveFiles(),
    LimitConcurrent(
        NumberConfigValue(min=1, max=4, default="1",
                          name="shared:rsync_threads", title="Rsync threads",
                          description="The maximum number of concurrent uploads."),
        UploadWithTracker(
            "http://%s/%s" % (TRACKER_HOST, TRACKER_ID),
            downloader=downloader,
            version=VERSION,
            files=[
                ItemInterpolation("%(data_dir)s/%(warc_file_base)s.warc.gz"),
            ],
            rsync_target_source_path=ItemInterpolation("%(data_dir)s/"),
            rsync_extra_args=[
                "--recursive",
                "--partial",
                "--partial-dir", ".rsync-tmp",
                ]
        ),
    ),
    SendDoneToTracker(
        tracker_url="http://%s/%s" % (TRACKER_HOST, TRACKER_ID),
        stats=ItemValue("stats")
    )
)
