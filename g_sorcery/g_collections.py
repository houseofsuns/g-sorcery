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

import functools
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


@functools.total_ordering
class Version(object):
    """
    Class to store a version.
    """

    __slots__ = ('formatted', 'components', 'suffix', 'alpha', 'beta', 'pre',
                 'rc', 'p', 'revision')

    def __init__(self, components, suffix="", alpha=None, beta=None, pre=None,
                 rc=None, p=None, revision=None):
        formatted = f'{".".join(map(str, components))}{suffix}'
        if alpha is not None:
            formatted = f'{formatted}_alpha{alpha}'
        if beta is not None:
            formatted = f'{formatted}_beta{beta}'
        if pre is not None:
            formatted = f'{formatted}_pre{pre}'
        if rc is not None:
            formatted = f'{formatted}_rc{rc}'
        if p is not None:
            formatted = f'{formatted}_p{p}'
        if revision is not None:
            formatted = f'{formatted}-r{revision}'
        object.__setattr__(self, "formatted", formatted)
        object.__setattr__(self, 'components', components)
        object.__setattr__(self, 'suffix', suffix)
        object.__setattr__(self, 'alpha', alpha)
        object.__setattr__(self, 'beta', beta)
        object.__setattr__(self, 'pre', pre)
        object.__setattr__(self, 'rc', rc)
        object.__setattr__(self, 'p', p)
        object.__setattr__(self, 'revision', revision)

    def __setattr__(self, name, value):
        raise AttributeError("Version instances are immutable",
                             self.__class__, name, value)

    def __str__(self):
        return self.formatted

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        # Treat missing components as zero
        l = max(len(self.components), len(other.components))
        sc = self.components + ((0,) * (l - len(self.components)))
        oc = other.components + ((0,) * (l - len(other.components)))
        if sc != oc:
            return False
        return all(getattr(self, attr) == getattr(other, attr)
                   for attr in ['suffix', 'alpha', 'beta', 'pre',
                                'rc', 'p', 'revision'])

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        # Treat missing components as zero
        l = max(len(self.components), len(other.components))
        sc = self.components + ((0,) * (l - len(self.components)))
        oc = other.components + ((0,) * (l - len(other.components)))
        if sc != oc:
            return sc < oc
        if self.suffix != other.suffix:
            return self.suffix < other.suffix
        for attr, sign in [('alpha', -1), ('beta', -1), ('pre', -1),
                           ('rc', -1), ('p', 1), ('revision', 1)]:
            if (sa := getattr(self, attr)) != (oa := getattr(other, attr)):
                if sa is not None and oa is not None:
                    return sa < oa
                else:
                    return sign*int(sa is not None) < sign*int(oa is not None)
        # Here we have equality
        return False

    def __hash__(self):
        # Be careful as we treat missing components as zero, so existing zeros
        # need to be dropped
        normalized_components = tuple(reversed(self.components))
        while normalized_components and normalized_components[0] == 0:
            normalized_components = normalized_components[1:]
        data = (normalized_components) + tuple(
            getattr(self, attr) for attr in ['suffix', 'alpha', 'beta', 'pre',
                                             'rc', 'p', 'revision'])
        return hash(data)

    def serialize(self):
        return str(self)

    @classmethod
    def deserialize(cls, value):
        mo = re.fullmatch(
            r'([0-9\.]+)([a-z])?(?:_alpha([0-9]+))?(?:_beta([0-9]+))?'
            r'(?:_pre([0-9]+))?(?:_rc([0-9]+))?(?:_p([0-9]+))?(?:-r([0-9]+))?',
            value)
        (rawcomponents, rawsuffix, rawalpha, rawbeta, rawpre, rawrc, rawp,
         rawrevision) = mo.groups()
        components = tuple(map(int, rawcomponents.split('.')))
        suffix = rawsuffix or ""
        alpha = int(rawalpha) if rawalpha else None
        beta = int(rawbeta) if rawbeta else None
        pre = int(rawpre) if rawpre else None
        rc = int(rawrc) if rawrc else None
        p = int(rawp) if rawp else None
        revision = int(rawrevision) if rawrevision else None
        return Version(components, suffix, alpha, beta, pre, rc, p, revision)
