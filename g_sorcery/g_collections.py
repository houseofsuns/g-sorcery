#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    g_collections.py
    ~~~~~~~~~~~~~~~~

    Customized classes of standard python data types
    for use withing g-sorcery for custom formatted string output
    substitution in our ebuild templates and classes for storing
    information about packages and dependencies.

    :copyright: (c) 2013 by Brian Dolbec
    :copyright: (c) 2013-2015 by Jauhien Piatlicki
    :license: GPL-2, see LICENSE for more details.
"""

import re

import portage

class elist(list):
    '''Custom list type which adds a customized __str__()
    and takes an optional separator argument

    elist() -> new empty elist
    elist(iterable) -> new elist initialized from iterable's items
    elist(separator='\\n\\t') -> new empty elist with
        newline & tab indented str(x) output
    elist(iterable, ' ') -> new elist initialized from iterable's items
        with space separated str(x) output
    '''

    __slots__ = ('_sep_')

    def __init__(self, iterable=None, separator=' '):
        '''
        iterable: initialize from iterable's items
        separator: string used to join list members with for __str__()
        '''
        list.__init__(self, iterable or [])
        self._sep_ = separator

    def __str__(self):
        '''Custom output function
        'x.__str__() <==> str(separator.join(x))'
        '''
        return self._sep_.join(map(str, self))


class serializable_elist(object):
    """
    A JSON serializable version of elist.
    """

    __slots__ = ('data')

    def __init__(self, iterable=None, separator=' '):
        '''
        iterable: initialize from iterable's items
        separator: string used to join list members with for __str__()
        '''
        self.data = elist(iterable or [], separator)

    def __eq__(self, other):
        return self.data == other.data

    def __iter__(self):
        return iter(self.data)

    def __str__(self):
        '''Custom output function
        '''
        return str(self.data)

    def append(self, x):
        self.data.append(x)

    def extend(self, xs):
        self.data.extend(xs)

    def serialize(self):
        return {"separator": self.data._sep_, "data" : self.data}

    @classmethod
    def deserialize(cls, value):
        return serializable_elist(value["data"], separator = value["separator"])


#todo: replace Package with something better

class Package(object):
    """
    Class to store full package name: category/package-version
    """
    __slots__ = ('category', 'name', 'version')

    def __init__(self, category, package, version):
        self.category = category
        self.name = package
        self.version = version

    def __str__(self):
        return self.category + '/' + self.name + '-' + self.version

    def __eq__(self, other):
        return self.category == other.category and \
            self.name == other.name and \
            self.version == other.version

    def __hash__(self):
        return hash(self.category + self.name + self.version)

    def serialize(self):
        return [self.category, self.name, self.version]

    @classmethod
    def deserialize(cls, value):
        return Package(*value)


#todo equality operator for Dependency, as it can be used in backend dependency solving algorithm

class Dependency(object):
    """
    Class to store a dependency. Uses portage Atom.
    """

    __slots__ = ('atom', 'formatted', 'category', 'package', 'version',
                 'operator', 'usedep', 'useflag')

    def __init__(self, category, package, version="", operator="", usedep="",
                 useflag=""):
        if bool(version) != bool(operator):
            raise ValueError('Version and operator must be specified'
                             ' together.')
        atom_str = f'{category}/{package}'
        if operator and version:
            atom_str = f'{operator}{atom_str}-{version}'
        formatted = atom_str
        if usedep:
            formatted = f'{formatted}[{usedep}]'
        if useflag:
            formatted = f'{useflag}? ( {formatted} )'
        object.__setattr__(self, "atom", portage.dep.Atom(atom_str))
        object.__setattr__(self, "formatted", formatted)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "package", package)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "operator", operator)
        object.__setattr__(self, "usedep", usedep)
        object.__setattr__(self, "useflag", useflag)

    def __setattr__(self, name, value):
        raise AttributeError("Dependency instances are immutable",
                             self.__class__, name, value)

    def __str__(self):
        return self.formatted

    def serialize(self):
        return str(self)

    @classmethod
    def deserialize(cls, value):
        mo = re.fullmatch(r'(?:([A-Za-z0-9+_@-]+)\?)?\s*'
                          r'\(?\s*([=<>!~A-Za-z0-9+_./-]*)(?:\[(.*)\])?\s*\)?',
                          value)
        rawuseflag, rawatom, rawusedep = mo.groups()
        atom = portage.dep.Atom(rawatom)
        operator = portage.dep.get_operator(atom)
        cpv = portage.dep.dep_getcpv(atom)
        category, rest = portage.catsplit(cpv)
        usedep = rawusedep or ''
        useflag = rawuseflag or ''

        if operator:
            package, version, revision = portage.pkgsplit(rest)
        else:
            package = rest
            version = ""
            operator = ""

        return Dependency(category, package, version, operator, usedep,
                          useflag)
