# coding: utf8

import os
import re
import json
import time
import base64
import requests

from urllib.parse import unquote, urlparse

from .publicsuffix import PublicSuffixList

__version__ = '0.0.1'


class Pac:
    def __init__(self, config={}):
        self._pac = None
        self.config = config
        self._proxies = {}
        self.generated_at = time.strftime(
            '%a, %d %b %Y %H:%M:%S %z',
            time.localtime()
        )
        self.gfwlist_modified = ''
        self.proxy_lst = []
        self.direct_lst = []
        self.user_proxy_lst = []
        self.user_direct_lst = []

        if os.path.isfile(self.config.pac.local_gfwlist):
            self.fetch_local_gfwlist(self.config.pac.local_gfwlist)

    def set_config(self, config):
        self.config = config

    def save_local_gfwlist(self, content):
        with open(self.config.pac.local_gfwlist, 'w') as _gfwlist:
            _gfwlist.write(content)

    def decode_gfwlist(self, encoded_gfwlist):
        return base64.decodebytes(
            encoded_gfwlist.encode('utf8')
        ).decode('utf8')

    def fetch_remote_gfwlist(self, url=None):
        if not url:
            url = self.config.pac.gfwlist_url
        response = requests.get(url, proxies=self._proxies)

        self.gfwlist = '! {}'.format(self.decode_gfwlist(response.text)) \
            .splitlines()
        self.gfwlist_from = response.url
        self.save_local_gfwlist(response.text)

        for line in self.gfwlist:
            if line.startswith('! Last Modified:'):
                self.gfwlist_modified = line.split(':', 1)[1].strip()
                break
        return True

    def fetch_local_gfwlist(self, path=None):
        with open(path) as _gfwlist:
            self.gfwlist = '! {}'.format(self.decode_gfwlist(_gfwlist.read())) \
                .splitlines()
        self.gfwlist_from = path

        for line in self.gfwlist:
            if line.startswith('! Last Modified:'):
                self.gfwlist_modified = line.split(':', 1)[1].strip()
                break
        return True

    def fetch_user_rules(self, path=None):
        if not path:
            path = self.config.pac.user_rules
        with open(path) as user_rule:
            self.user_rules = user_rule.read().splitlines()

    def generate(self, force=False):
        gfwlist = self.gfwlist

        self.direct_lst, self.proxy_lst = self.parse_rules(gfwlist)
        self.user_direct_lst, self.user_proxy_lst = \
            self.parse_rules(self.user_rules)

        self._pac = self.template().replace('__version__', __version__) \
            .replace('__generated__', self.generated_at) \
            .replace('__modified__', self.gfwlist_modified) \
            .replace('__gfwlist_from__', self.gfwlist_from) \
            .replace('__proxy_host__', self.config.local.address) \
            .replace('__proxy_port__', str(self.config.local.port)) \
            .replace('__rules__', self.dumps())
        return self

    def set_proxy(self, http=None, https=None):
        if http:
            self._proxies['http'] = http
        if https:
            self._proxies['https'] = https

    def parse_rules(self, rules):
        proxy_lst = []
        direct_lst = []

        for line in rules:
            proxy, direct = self.parse_rule(line)
            proxy_lst.extend(proxy)
            direct_lst.extend(direct)

        proxy_lst = list(set(proxy_lst))
        proxy_lst.sort()

        direct_lst = list(set(direct_lst))
        direct_lst = [d for d in direct_lst if d not in proxy_lst]
        direct_lst.sort()

        return direct_lst, proxy_lst

    def parse_rule(self, line):
        proxy_lst = []
        direct_lst = []
        if not line or line.startswith('!'):
            return proxy_lst, direct_lst

        if line.startswith('@@'):
            line = line.lstrip('@!.')
            domain = RuleParser.surmise_domain(line)
            if domain:
                direct_lst.append(domain)
                return proxy_lst, direct_lst
        elif line.find('.*') >= 0 or line.startswith('/'):
            line = line.replace('\/', '/').replace('\.', '.')
            try:
                m = re.search(r'[a-z0-9]+\..*', line)
                domain = RuleParser.surmise_domain(m.group(0))
                if domain:
                    proxy_lst.append(domain)
                    return proxy_lst, direct_lst
                m = re.search(r'[a-z]+\.\(.*\)', line)
                m2 = re.split(r'[\(\)]', m.group(0))
                for tld in re.split(r'\|', m2[1]):
                    domain = RuleParser.surmise_domain(
                        '{}{}'.format(m2[0], tld)
                    )
                    if domain:
                        proxy_lst.append(domain)
            except:
                pass
            return proxy_lst, direct_lst
        elif line.startswith('|'):
            line = line.lstrip('|')
        domain = RuleParser.surmise_domain(line)
        if domain:
            proxy_lst.append(domain)
        return proxy_lst, direct_lst

    def dumps(self):
        return json.dumps(
            [
                [self.user_direct_lst, self.user_proxy_lst],
                [self.direct_lst, self.proxy_lst]
            ],
            indent=None if self.config.pac.compress else 2,
            separators=(',', ':') if self.config.pac.compress else None
        )

    def template(self):
        if self.config.pac.compress:
            return ResourceData('pac-tpl.min.js').read()
        return ResourceData('pac-tpl.js').read()

    def save(self, rules=None):
        if not rules:
            rules = self._pac
        with open(self.config.pac.path, 'w') as pac_file:
            pac_file.write(rules)
        return True


class ResourceData:
    def __init__(self, filename):
        self._file = os.path.join(
            os.path.dirname(__file__),
            'resources',
            filename
        )

    def read(self):
        with open(self._file) as f:
            return f.read()

    def get_abs(self):
        return self._file


class RuleParser:
    psl = PublicSuffixList(ResourceData('public_suffix_list.dat').read())

    @classmethod
    def surmise_domain(cls, rule):
        domain = ''
        rule = cls.clear_asterisk(rule).lstrip('.')

        if rule.find('%2f') >= 0:
            rule = unquote(rule)

        if rule.startswith('http:') or rule.startswith('https:'):
            domain = urlparse(rule).hostname
        elif rule.find('/') > 0:
            domain = urlparse('http://' + rule).hostname
        elif rule.find('.') > 0:
            domain = rule

        return cls.get_public_suffix(domain)

    @classmethod
    def clear_asterisk(cls, rule):
        if rule.find('*') < 0:
            return rule
        rule = rule.strip('*')
        rule = rule.replace('/*.', '/')
        rule = re.sub(r'/([a-zA-Z0-9]+)\*\.', '/', rule)
        rule = re.sub(r'\*([a-zA-Z0-9_%]+)', '', rule)
        rule = re.sub(r'^([a-zA-Z0-9_%]+)\*', '', rule)
        return rule

    @classmethod
    def get_public_suffix(cls, host):
        domain = cls.psl.get_public_suffix(host)
        return None if domain.find('.') < 0 else domain
