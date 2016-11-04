import functools
import subprocess
import os
import json
import collections.abc
from datetime import datetime
from datetime import tzinfo
import pytz

from albumin.utils import files_in


class GitRepo:
    def __init__(self, path):
        self.path = path

        if not os.path.isdir(self.path):
            print("Creating directory {}".format(self.path))
            os.makedirs(self.path)

        if not os.path.isdir(os.path.join(self.path, '.git')):
            print("Initializing git repo at {}".format(self.path))
            self._git('init')

        if 'master' not in self.branches:
            self.checkout('master')
            self.commit('Initialize repo', allow_empty=True)

    def _git(self, *commands):
        return subprocess.check_output(
            ('git', *commands),
            universal_newlines=True,
            cwd=self.path,
        )

    @property
    def status(self):
        return self._git('status', '-s')

    @property
    def branches(self):
        branch_list = []
        current_exists = False
        for branch in self._git('branch', '--list').splitlines():
            if branch[0] == '*':
                branch_list.insert(0, branch[2:])
                current_exists = True
            else:
                branch_list.append(branch[2:])
        if branch_list and not current_exists:
            raise RuntimeError(
                'No current branch found among: \n'
                '    {}\n    in {}'.format(branch_list, self.path))
        return tuple(branch_list)

    def add(self, path):
        return self._git('add', path)

    def rm(self, path):
        return self._git('rm', '-rf', path)

    def checkout(self, branch, new_branch=True):
        command = ['checkout', branch]
        if new_branch and branch not in self.branches:
            command.insert(1, '-b')
        return self._git(*command)

    def commit(self, message, add=True, allow_empty=False):
        command = ['commit', '-m', message]
        if add: command.append('-a')
        if allow_empty: command.append('--allow-empty')
        return self._git(*command)

    def cherry_pick(self, branch):
        return self._git("cherry-pick", branch)

    def stash(self, pop=False):
        command = ['stash']
        if pop: command.append('pop')
        return self._git(*command)

    @property
    def tree_hash(self):
        commit = self._git('cat-file', 'commit', 'HEAD').split()
        return commit[commit.index('tree') + 1]

    def __repr__(self):
        return 'GitRepo(path={!r})'.format(self.path)


class GitAnnexRepo(GitRepo):
    def __init__(self, path):
        super().__init__(path)
        self.annex = GitAnnex(self)

    @classmethod
    def make_annex(cls, repo):
        repo.annex = GitAnnex(repo)
        repo.__class__ = cls

    def __repr__(self):
        return 'GitAnnexRepo(path={!r})'.format(self.path)


class GitAnnex(collections.abc.Mapping):
    def __init__(self, repo):
        self.repo = repo
        self._annex = functools.partial(repo._git, 'annex')

        if not os.path.isdir(os.path.join(repo.path, '.git', 'annex')):
            print("Initializing git-annex at {}".format(repo.path))
            self._annex('init', 'albumin')

    def import_(self, path, duplicate=True):
        if os.path.basename(path) in os.listdir(self.repo.path):
            raise ValueError('Import path basename conflict')
        command = ['import', path]
        if duplicate: command.append('--duplicate')
        return self._annex(*command)

    def calckey(self, file_path):
        return self._annex('calckey', file_path).rstrip()

    def fromkey(self, key, file_path):
        return self._annex('fromkey', key, file_path)

    def lookupkey(self, file_path):
        return self._annex('lookupkey', file_path)

    @property
    def keys(self):
        jsons = self._annex('metadata', '--all', '--json').splitlines()
        meta_list = [json.loads(json_) for json_ in jsons]
        return {meta['key'] for meta in meta_list}

    @property
    def files(self):
        jsons = self._annex('metadata', '--json').splitlines()
        meta_list = [json.loads(json_) for json_ in jsons]
        return {meta['file']: meta['key'] for meta in meta_list}

    def __getitem__(self, key):
        return GitAnnexMetadata(self, key)

    def __contains__(self, key):
        return key in self.keys

    def __iter__(self):
        yield from self.keys

    def __len__(self):
        return len(self.keys)

    def __repr__(self):
        return 'GitAnnex(repo={!r})'.format(self.repo)


class GitAnnexMetadata(collections.abc.MutableMapping):
    def __init__(self, annex, key):
        self.key = key
        self.annex = annex
        self._meta = functools.partial(
            annex._annex, 'metadata', '--key', key)

    def datetime_format(self, values):
        for v in values:
            if isinstance(v, datetime):
                v_utc = v.astimezone(pytz.utc)
                dt_str = v_utc.strftime('%Y-%m-%d@%H-%M-%S')
                values.remove(v)
                values.add(dt_str)
        return values

    def datetime_parse(self, values, timezone=None):
        if not timezone:
            timezone = self['timezone']
        if not timezone:
            timezone = pytz.utc
        for v in values:
            try:
                dt_obj = datetime.strptime(v, '%Y-%m-%d@%H-%M-%S')
                dt_utc = pytz.utc.localize(dt_obj)
                dt_local = dt_utc.astimezone(timezone)
                values.remove(v)
                values.add(dt_local)
            except (ValueError, TypeError):
                continue
        return values

    def timezone_parse(self, values):
        for v in values:
            try:
                tz = pytz.timezone(v)
                values.remove(v)
                values.add(tz)
            except:
                continue
        return values

    def timezone_format(self, values):
        for v in values:
            if isinstance(v, tzinfo):
                tzname = v.tzname(None)
                values.remove(v)
                values.add(tzname)
        return values

    def sync_ymd(self):
        dt = self['datetime']
        self['year'] = dt.strftime('%Y')
        self['month'] = dt.strftime('%m')
        self['day'] = dt.strftime('%d')

    def __getitem__(self, meta_key):
        values = self._meta('-g', meta_key).splitlines()
        return_value = set(values)

        if meta_key == 'datetime':
            self.datetime_parse(return_value)
        elif meta_key.endswith('lastchanged'):
            self.datetime_parse(return_value, timezone=pytz.utc)
        elif meta_key == 'timezone':
            self.timezone_parse(return_value)

        if len(return_value) == 1:
            return return_value.pop()
        else:
            return return_value

    def __setitem__(self, meta_key, value):
        if meta_key.endswith('lastchanged'):
            raise KeyError(meta_key)

        old_value = self[meta_key]
        if not isinstance(value, set):
            value = {value}
        if not isinstance(old_value, set):
            old_value = {old_value}

        if meta_key == 'datetime':
            self.datetime_format(value)
            self.datetime_format(old_value)
        elif meta_key == 'timezone':
            self.timezone_format(value)
            self.timezone_format(old_value)

        cmds = []
        for v in value - old_value:
            cmds += ['-s', '{}+={}'.format(meta_key, v)]
        for v in old_value - value:
            cmds += ['-s', '{}-={}'.format(meta_key, v)]
        self._meta(*cmds)

        if meta_key == 'datetime':
            self.sync_ymd()

    def __delitem__(self, meta_key):
        self._meta('-r', meta_key)
        if meta_key == 'datetime':
            self.sync_ymd()

    def __contains__(self, meta_key):
        return self[meta_key] > set()

    def __iter__(self):
        json_ = self._meta('--json')
        fields = json.loads(json_)['fields']
        for field in fields.keys():
            if not field.endswith('lastchanged'):
                yield field

    def __len__(self):
        len([x for x in self])

    def __repr__(self):
        repr_ = 'GitAnnexFileMetadata(key={!r}, path={!r})'
        return repr_.format(self.key, self.annex.repo.path)
