#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    fileutils.py
    ~~~~~~~~~~~~

    file utilities

    :copyright: (c) 2013-2015 by Jauhien Piatlicki
    :license: GPL-2, see LICENSE for more details.
"""

import glob
import json
import hashlib
import os
import pathlib
import tarfile

from .compatibility import TemporaryDirectory
from .exceptions import FileJSONError, DownloadingError
from .serialization import JSONSerializer, deserializeHook

class FileJSONData(object):
    """
    Class for files with JSON compatible data.
    """
    def __init__(self, directory, name, mandatories=None):
        """
        Args:
            directory: File directory.
            name: File name.
            mandatories: List of requiered keys.
        """
        self.directory = os.path.abspath(directory)
        self.name = name
        self.path = os.path.join(directory, name)
        if not mandatories:
            self.mandatories = []
        else:
            self.mandatories = mandatories

    def read(self):
        """
        Read file.
        """
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        content = {}
        if not os.path.isfile(self.path):
            for key in self.mandatories:
                content[key] = ""
            self.write_content(content)
        else:
            content = self.read_content()
            for key in self.mandatories:
                if not key in content:
                    raise FileJSONError('lack of mandatory key: ' + key)

        return content

    def read_content(self):
        """
        Real read operation with deserialization. Should be overridden.
        """
        return []

    def write(self, content):
        """
        Write file.
        """
        for key in self.mandatories:
            if not key in content:
                raise FileJSONError('lack of mandatory key: ' + key)
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        self.write_content(content)

    def write_content(self, content):
        """
        Real write operation with serialization. Should be overridden.
        """
        pass


class FileJSON(FileJSONData):
    """
    Class for JSON files. Supports custom JSON serialization
    provided by g_sorcery.serialization.
    """

    def read_content(self):
        """
        Read JSON file.
        """
        content = {}
        with open(self.path, 'r') as f:
            content = json.load(f, object_hook=deserializeHook)
        return content

    def write_content(self, content):
        """
        Write JSON file.
        """
        with open(self.path, 'w') as f:
            json.dump(content, f, indent=2, sort_keys=True, cls=JSONSerializer)


def hash_file(name, hasher, blocksize=65536):
    """
    Get a file hash.

    Args:
        name: file name.
        hasher: Hasher.
        blocksize: Blocksize.

    Returns:
        Hash value.
    """
    with open(name, 'rb') as f:
        buf = f.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(blocksize)
    return hasher.hexdigest()

def copy_all(src, dst):
    """
    Copy entire tree.

    Args:
       src: Source.
       dst: Destination.
    """
    os.system("cp -rv " + src + "/* " + dst)

def wget(uri, directory, output="", timeout = None):
    """
    Fetch a file.

    Args:
        uri: URI.
        directory: Directory where file should be saved.
        output: Name of output file.
        timeout: Timeout for wget.

    Returns:
        Nonzero in case of a failure.
    """
    if timeout is None:
        timeout_str = ' '
    else:
        timeout_str = ' -T ' + str(timeout)

    if output:
        ret = os.system('wget ' + uri +
                        ' -O ' + os.path.join(directory, output) + timeout_str)
    else:
        ret = os.system('wget -P ' + directory + ' ' + uri + timeout_str)
    return ret

def get_pkgpath(root = None):
    """
    Get package path.

    Args:
        root: module file path

    Returns:
        Package path.
    """
    if not root:
        root = __file__
    if os.path.islink(root):
        root = os.path.realpath(root)
    return os.path.dirname(os.path.abspath(root))

class ManifestEntry(object):
    """
    A manifest entry for a file.
    """

    __slots__ = ('directory', 'name', 'ftype',
                 'size', 'sha512', 'blake2b')

    def __init__(self, directory, name, ftype):
        self.directory = directory
        self.name = name
        self.ftype = ftype
        self.digest()

    def digest(self):
        """
        Digest a file associated with a manifest entry.
        """
        h_sha512 = hashlib.new('SHA512')
        h_blake2b = hashlib.new('blake2b')
        with open(os.path.join(self.directory, self.name), 'rb') as f:
            src = f.read()
        h_sha512.update(src)
        h_blake2b.update(src)
        self.size = str(len(src))
        self.sha512 = h_sha512.hexdigest()
        self.blake2b = h_blake2b.hexdigest()


def fast_manifest(directory):
    """
    Digest package directory.
    This function is intended to be used in place of pkgdev manifest,
    as it is to slow.

    Args:
        directory: Directory.
    """
    directory_path = pathlib.Path(directory)
    manifest = []

    files_path = directory_path / 'files'
    for aux in files_path.glob('*'):
        manifest.append(ManifestEntry(aux.parent, aux.name, "AUX"))
    for ebuild in directory_path.glob("*.ebuild"):
        manifest.append(ManifestEntry(directory, ebuild.name, "EBUILD"))
    metadata = directory_path / "metadata.xml"
    if metadata.is_file():
        manifest.append(ManifestEntry(directory, "metadata.xml", "MISC"))

    manifest = [" ".join([m.ftype, m.name, m.size,
                          "SHA512", m.sha512, "BLAKE2B", m.blake2b])
                for m in manifest]

    manifest_path = directory_path / "Manifest"
    if manifest_path.is_file():
        with open(manifest_path, 'r') as f:
            for line in f.read().splitlines():
                if line.startswith('DIST'):
                    manifest.append(line)
        manifest.sort()

    with open(manifest_path, 'w') as f:
        f.write('\n'.join(manifest) + '\n')


def _call_parser(f_name, parser, open_file = True, open_mode = 'r'):
    """
    Call parser on a given file.

    Args:
        f_name: File name.
        parser: Parser function.
        open_file: Whether parser accepts a file descriptor.
        open_mode: Open mode for a file.

    Returns:
        A dictionary with one entry. Key if a file name, content is
    content returned by parser.
    """
    data = None
    if open_file:
        with open(f_name, open_mode) as f:
            data = parser(f)
    else:
        data = parser(f_name)
    return {os.path.basename(f_name): data}


def load_remote_file(uri, parser, open_file = True, open_mode = 'r', output = "", timeout = None):
    """
    Load files from an URI.

    Args:
        uri: URI.
        parser: Parser that will be applied to downloaded files.
        open_file: Whether parser accepts a file descriptor.
        open_mode: Open mode for a file.
        output: What output name should downloaded file have.
        timeout: URI access timeout.
    (it will be a key identifying data loaded from this file)

    Returns:
        Dictionary with a loaded data. Key is filename, content is data returned by parser.
    """
    download_dir = TemporaryDirectory()
    loaded_data = {}
    if wget(uri, download_dir.name, output, timeout=timeout):
        raise DownloadingError("wget failed: " + uri)
    for f_name in glob.glob(os.path.join(download_dir.name, "*")):
        if tarfile.is_tarfile(f_name):
            unpack_dir = TemporaryDirectory()
            with tarfile.open(f_name) as f:
                f.extractall(unpack_dir.name)
            for uf_name in glob.glob(os.path.join(unpack_dir, "*")):
                loaded_data.update(_call_parser(uf_name, parser,
                                    open_file=open_file, open_mode=open_mode))
            del unpack_dir
        else:
            name, extention = os.path.splitext(f_name)
            if extention in [".xz", ".lzma"]:
                if (os.system("xz -d " + f_name)):
                    raise DownloadingError("xz failed: "
                                + f_name + " from " + uri)
                f_name = name
            loaded_data.update(_call_parser(f_name, parser,
                                open_file=open_file, open_mode=open_mode))
    del download_dir
    return loaded_data
