# Albumin Git Hooks
# Copyright (C) 2016 Alper Nebi Yasak
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import pytz

from albumin.repo import AlbuminRepo
from albumin.imdate import analyze_date


def pre_commit_hook(args):
    """
    Albumin as a pre-commit hook.
    Usage: pre-commit
    """
    repo = current_repo()
    new_files = repo.new_files()

    try:
        timezone = repo.timezone
        print('Timezone: {}'.format(timezone))
    except pytz.exceptions.UnknownTimeZoneError as err:
        print("Invalid time zone: {}".format(err))
        return 1

    if not timezone:
        print("Please set albumin.timezone:")
        print("    $ git -c albumin.timezone=UTC commit ...")
        return 2

    report = analyze_date(
        *map(repo.abs_path, new_files),
        timezone=timezone
    )

    if report.remaining:
        print(report)
        return 3

    file_data = {
        new_files[repo.rel_path(f)]: new
        for f, (new, _) in report.updates.items()
    }

    batch = repo.arrange_by_imdates(imdates=file_data)
    repo.annex.pre_commit()


def pre_commit_annex_hook(args):
    """
    Albumin as a pre-commit-annex git hook.
    Usage: pre-commit-annex <file>...
    """
    pass


def prepare_commit_msg_hook(args):
    """
    Albumin as a pre-commit git hook.
    Usage: prepare-commit-msg <editmsg> [[<commit_type>] <commit_sha>]
    """
    pass


def commit_msg_hook(args):
    """
    Albumin as a pre-commit git hook.
    Usage: commit-msg <editmsg>
    """
    pass


def post_commit_hook(args):
    """
    Albumin as a post-commit git hook.
    Usage: post-commit
    """
    pass


def current_repo():
    return AlbuminRepo(os.getcwd(), create=False)


git_hooks = {
    'pre-commit': pre_commit_hook,
    'pre-commit-annex': pre_commit_annex_hook,
    'prepare-commit-msg': prepare_commit_msg_hook,
    'commit-msg': commit_msg_hook,
    'post-commit': post_commit_hook,
}
