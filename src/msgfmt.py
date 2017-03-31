#! /usr/bin/env python
# -*- coding: utf8 -*-
# Written by Martin v. Loewis <loewis@informatik.hu-berlin.de>
#
# Changed by songww<sww4718168@gmail.com> for the placeless
# translation service (PTS) of Zope
#
# Fixed some bugs and updated to support msgctxt
# by Hanno Schlichting <hanno@hannosch.eu>

"""Generate binary message catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a binary GNU catalog (.mo file). This is essentially the same function as the
GNU msgfmt program, however, it is a simpler implementation.

This file was taken from Python-2.3.2/Tools/i18n and altered in several ways.
Now you can simply use it from another python module:

  from msgfmt import Msgfmt
  mo = Msgfmt(po).get()

where po is path to a po file as string, an opened po file ready for reading or
a list of strings (readlines of a po file) and mo is the compiled mo file as
binary string.

Exceptions:

  * IOError if the file couldn't be read

  * msgfmt.PoSyntaxError if the po file has syntax errors
"""

import io
import array
import codecs
import struct

from ast import literal_eval


class Msgfmt:

    def __init__(self, po, name='unknown'):
        self.po = po
        self.name = name
        self.messages = {}
        self.openfile = False
        # Start off assuming latin-1, so everything decodes without failure,
        # until we know the exact encoding
        self.encoding = 'utf8'

    def read_from_po(self):
        """ read po data from self.po and return an iterator """
        output = []
        if isinstance(self.po, str):
            output = open(self.po, 'rb')
        elif isinstance(self.po, io.TextIOWrapper):
            self.po.seek(0)
            self.openfile = True
            output = self.po
        elif isinstance(self.po, list):
            output = self.po
        if not output:
            raise ValueError("self.po is invalid! %s" % type(self.po))
        if isinstance(output, io.TextIOWrapper):
            # remove BOM from the start of the parsed input
            first = output.readline()
            if len(first) == 0:
                return output.readlines()
            if first.startswith(codecs.BOM_UTF8):
                first = first.lstrip(codecs.BOM_UTF8)
            return [first] + output.readlines()
        return output

    def add(self, context, id, string, fuzzy):
        "Add a non-empty and non-fuzzy translation to the dictionary."
        if string and not fuzzy:
            # The context is put before the id and separated by a EOT char.
            if context:
                id = context + u'\x04' + id
            if not id:
                # See whether there is an encoding declaration
                if isinstance(string, bytes):
                    string = string.decode(self.encoding)
            self.messages[id] = string

    def generate(self):
        "Return the generated output."
        # the keys are sorted in the .mo file
        keys = sorted(self.messages.keys())
        offsets = []
        ids = strs = b''
        for id in keys:
            msg = self.messages[id].encode(self.encoding)
            id = id.encode(self.encoding)
            # For each string, we need size and file offset. Each string is
            # NUL terminated; the NUL does not count into the size.
            offsets.append((len(ids), len(id), len(strs),
                            len(msg)))
            ids += id + b'\0'
            strs += msg + b'\0'
        output = b''
        # The header is 7 32-bit unsigned integers. We don't use hash tables,
        # so the keys start right after the index tables.
        keystart = 7 * 4 + 16 * len(keys)
        # and the values start after the keys
        valuestart = keystart + len(ids)
        koffsets = []
        voffsets = []
        # The string table first has the list of keys, then the list of values.
        # Each entry has first the size of the string, then the file offset.
        for o1, l1, o2, l2 in offsets:
            koffsets += [l1, o1 + keystart]
            voffsets += [l2, o2 + valuestart]
        offsets = koffsets + voffsets
        # Even though we don't use a hashtable, we still set its offset to be
        # binary compatible with the gnu gettext format produced by:
        # msgfmt file.po --no-hash
        output = struct.pack("Iiiiiii",
                             0x950412de,        # Magic
                             0,                 # Version
                             len(keys),         # # of entries
                             7 * 4,             # start of key index
                             7 * 4 + len(keys) * 8,  # start of value index
                             0, keystart)       # size and offset of hash table
        output += array.array("i", offsets).tobytes()
        output += ids
        output += strs
        return output

    def get(self):
        """ """
        self.read()
        # Compute output
        return self.generate()

    def read(self, header_only=False):
        """ """
        ID = 1
        STR = 2
        CTXT = 3

        section = None
        fuzzy = 0
        msgid = msgstr = msgctxt = ''

        # Parse the catalog
        lno = 0
        for l in self.read_from_po():
            l = l.decode(self.encoding)
            lno += 1
            # If we get a comment line after a msgstr or a line starting with
            # msgid or msgctxt, this is a new entry
            if section == STR and (l[0] == '#' or (l[0] == 'm' and
               (l.startswith('msgctxt') or l.startswith('msgid')))):
                self.add(msgctxt, msgid, msgstr, fuzzy)
                section = None
                fuzzy = 0
                # If we only want the header we stop after the first message
                if header_only:
                    break
            # Record a fuzzy mark
            if l[:2] == '#,' and 'fuzzy' in l:
                fuzzy = 1
            # Skip comments
            if l[0] == '#':
                continue
            # Now we are in a msgctxt section
            if l.startswith('msgctxt'):
                section = CTXT
                l = l[7:]
                msgctxt = ''
            # Now we are in a msgid section, output previous section
            elif (l.startswith('msgid') and
                  not l.startswith('msgid_plural')):
                if section == STR:
                    self.add(msgid, msgstr, fuzzy)
                section = ID
                l = l[5:]
                msgid = msgstr = ''
                is_plural = False
            # This is a message with plural forms
            elif l.startswith('msgid_plural'):
                if section != ID:
                    raise SyntaxError(
                        'msgid_plural not preceeded by '
                        'msgid on line %d of po file %s' %
                        (lno, repr(self.name)))
                l = l[12:]
                msgid += u'\0'  # separator of singular and plural
                is_plural = True
            # Now we are in a msgstr section
            elif l.startswith('msgstr'):
                section = STR
                if l.startswith('msgstr['):
                    if not is_plural:
                        raise SyntaxError(
                            'plural without msgid_plural '
                            'on line %d of po file %s' %
                            (lno, repr(self.name)))
                    l = l.split(']', 1)[1]
                    if msgstr:
                        # Separator of the various plural forms
                        msgstr += u'\0'
                elif is_plural:
                    raise SyntaxError(
                        'indexed msgstr required for plural on line %d of po \
                        file %s' % (lno, repr(self.name)))
                else:
                    l = l[6:]
            # Skip empty lines
            l = l.strip()
            if not l:
                continue
            # TODO: Does this always follow Python escape semantics?
            try:
                l = literal_eval(l)
            except Exception as msg:
                raise SyntaxError(
                    '%s (line %d of po file %s): \n%s' %
                    (msg, lno, repr(self.name), l))
            if isinstance(l, bytes):
                l = l.decode(self.encoding)
            if section == CTXT:
                msgctxt += l
            elif section == ID:
                msgid += l
            elif section == STR:
                msgstr += l
            else:
                raise SyntaxError(
                    'error on line %d of po file %s' % (lno, repr(self.name)))

        # Add last entry
        if section == STR:
            self.add(msgctxt, msgid, msgstr, fuzzy)

        if self.openfile:
            self.po.close()

    def save_to_mo(self):
        return self.get()
