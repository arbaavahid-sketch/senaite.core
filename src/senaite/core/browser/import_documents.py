# -*- coding: utf-8 -*-
#
# One-off admin tool: bulk-import ISO controlled documents from a server
# directory into the "controlleddocuments" register. Derives the document
# code / title / type from each file name (TLP-* = procedure, TLF-* = form,
# TLQP / TLM = record). Dry-run by default; ?apply=1 creates; ?effective=1
# also approves them (draft -> effective). ManageBika only.
#
# Usage:
#   1) copy the files into the senaite data volume, e.g. /data/iso_docs
#   2) open @@import-controlled-documents?dir=/data/iso_docs   (dry-run)
#   3) then  ...?dir=/data/iso_docs&apply=1&effective=1

import mimetypes
import os
import re

from Products.Five.browser import BrowserView
from plone.namedfile.file import NamedBlobFile

from bika.lims import api
from bika.lims.api import safe_unicode

CODE_RE = re.compile(u"^(TL[A-Z]{1,3}(?:-\\d+){0,3})")
DOC_EXTS = (".pdf", ".docx", ".doc", ".pptx", ".xlsx")

# Never import these (sensitive): password lists.
SKIP_MARKERS = (u"کلمات عبور", u"كلمات عبور", u"TLF-20-02", u"password")


def _type_for(code):
    if code.startswith("TLP"):
        return "sop"
    if code.startswith("TLF"):
        return "form"
    if code.startswith(("TLQP", "TLM", "TLQ")):
        return "record"
    return "record"


def _parse(basename):
    basename = safe_unicode(basename)
    name = os.path.splitext(basename)[0]
    # The code may appear anywhere in the name (start, end, or glued to text).
    m = CODE_RE.search(name)
    if m:
        code = m.group(1)
        title = name[:m.start()] + u" " + name[m.end():]
    else:
        code = u""
        title = name
    # If the code has no number (e.g. bare "TLP" or "TLM") but a trailing
    # number was left in the name, treat it as the missing document number.
    if code and not re.search(u"\\d", code):
        tnum = re.search(u"(\\d{1,3})\\s*$", title)
        if tnum:
            code = u"%s-%s" % (code, tnum.group(1))
            title = title[:tnum.start()]
    # Clean the title: drop stray file extensions and collapse punctuation.
    title = re.sub(u"(?i)\\b(docx|pptx|xlsx|pdf|doc)\\b", u" ", title)
    title = re.sub(u"[\\s\\.\\-_]+", u" ", title).strip()
    if not title:
        title = code or name
    return code, title, _type_for(code or u"")


class ImportControlledDocumentsView(BrowserView):
    """Bulk-create ControlledDocument objects from files in a server folder."""

    def __call__(self):
        # Keep the directory as a bytestring for filesystem calls so os.walk
        # tolerates any non-UTF-8 (mojibake) filenames; decode per-name later.
        directory = self.request.get("dir") or "/data/iso_docs"
        if isinstance(directory, unicode):  # noqa: F821 (py2)
            directory = directory.encode("utf-8")
        apply = bool(self.request.get("apply"))
        make_effective = bool(self.request.get("effective"))

        out = []
        out.append(u"MODE: %s%s" % (
            u"APPLY" if apply else u"DRY-RUN (add &apply=1 to create)",
            u" + EFFECTIVE" if (apply and make_effective) else u""))
        out.append(u"directory: %s" % safe_unicode(directory))

        if not os.path.isdir(directory):
            out.append(u"ERROR: directory not found inside the container.")
            return self._text(out)

        try:
            container = api.get_senaite_setup().controlleddocuments
        except Exception:
            out.append(u"ERROR: 'controlleddocuments' register not found. "
                       u"Open @@install-documents first.")
            return self._text(out)

        # Existing (document_id, title) to avoid duplicates on re-run.
        existing = set()
        for obj in container.objectValues():
            existing.add((
                safe_unicode(getattr(obj, "document_id", u"") or u""),
                safe_unicode(getattr(obj, "title", u"") or u"")))

        # Collect files; prefer a .pdf over a same-named .docx/.pptx sibling.
        files = []
        for root, _dirs, names in os.walk(directory):
            pdf_stems = set(os.path.splitext(n)[0] for n in names
                            if n.lower().endswith(".pdf"))
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext not in DOC_EXTS:
                    continue
                if ext != ".pdf" and os.path.splitext(n)[0] in pdf_stems:
                    continue  # a PDF version exists, use that instead
                files.append(os.path.join(root, n))
        files.sort()

        created = skipped = sensitive = errors = 0
        lines = []
        for path in files:
            basename = safe_unicode(os.path.basename(path))
            if any(mk in basename or mk in safe_unicode(path)
                   for mk in SKIP_MARKERS):
                sensitive += 1
                lines.append(u"SKIP (sensitive)\t%s" % basename)
                continue
            code, title, dtype = _parse(os.path.basename(path))
            if (code, title) in existing:
                skipped += 1
                continue
            # Reserve this (code, title) so cross-folder duplicates are only
            # counted/created once, in dry-run and apply alike.
            existing.add((code, title))
            lines.append(u"%s\t%s\t%s\t%s" % (
                u"CREATE" if apply else u"would create", code, dtype, title))
            if not apply:
                continue
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                ct = mimetypes.guess_type(path)[0] or "application/octet-stream"
                blob = NamedBlobFile(data=data, filename=basename,
                                     contentType=ct)
                obj = api.create(
                    container, "ControlledDocument", title=title,
                    document_id=code, document_type=dtype, version=u"00",
                    file=blob)
                obj = self._clean_id(container, obj, code)
                created += 1
                if make_effective:
                    try:
                        api.do_transition_for(obj, "approve")
                    except Exception:
                        pass
            except Exception as exc:  # noqa
                errors += 1
                lines.append(u"ERROR\t%s\t%s" % (basename, safe_unicode(exc)))

        summary = [
            u"",
            u"files found: %d" % len(files),
            u"created: %d" % created,
            u"already present (skipped): %d" % skipped,
            u"sensitive (skipped): %d" % sensitive,
            u"errors: %d" % errors,
            u"",
            u"--- details ---",
        ]
        return self._text(out + summary + lines)

    def _clean_id(self, container, obj, code):
        """Rename to a clean ascii id (documents get a Persian-title id by
        default). Best effort."""
        try:
            base = (code or u"doc").lower().replace(u"-", u"")
            base = re.sub(r"[^a-z0-9]", u"", base) or u"doc"
            new_id = base
            n = 1
            existing_ids = set(container.objectIds())
            while new_id in existing_ids:
                n += 1
                new_id = u"%s-%d" % (base, n)
            old_id = api.get_id(obj)
            if old_id != new_id:
                container.manage_renameObject(old_id, new_id)
                return container[new_id]
        except Exception:
            pass
        return obj

    def _text(self, lines):
        self.request.response.setHeader(
            "Content-Type", "text/plain; charset=utf-8")
        return u"\n".join(lines).encode("utf-8")
