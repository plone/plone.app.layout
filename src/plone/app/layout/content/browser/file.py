from AccessControl import getSecurityManager
from OFS.interfaces import IFolder
from plone.app.dexterity.interfaces import IDXFileFactory
from plone.base.permissions import AddPortalContent
from plone.uuid.interfaces import IUUID
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView

import json
import logging
import mimetypes
import os

logger = logging.getLogger("plone")


def _bool(val):
    if val.lower() in ("t", "true", "1", "on"):
        return True
    return False


def _tus_int(val):
    try:
        return int(val)
    except (ValueError, TypeError, AttributeError):
        return 60 * 60  # default here...


possible_tus_options = {
    "tmp_file_dir": str,
    "send_file": _bool,
    "upload_valid_duration": _tus_int,
}

TUS_ENABLED = False
if os.environ.get("TUS_ENABLED"):
    # tus resumable upload standard, see http://tus.io
    try:
        from tus import Tus
        from tus import Zope2RequestAdapter

        tus_settings = {}
        for option, converter in possible_tus_options.items():
            name = "TUS_%s" % option.upper()
            if name in os.environ:
                tus_settings[option] = converter(os.environ[name])

            tmp_file_dir = tus_settings.get("tmp_file_dir")
            if tmp_file_dir is None:
                logger.warn(
                    "You are trying to enable tus but no"
                    "TUS_TMP_FILE_DIR environment setting is set."
                )
            elif not os.path.exists(tmp_file_dir) or not os.path.isdir(tmp_file_dir):
                logger.warn(
                    "The TUS_TMP_FILE_DIR does not point to a valid " "directory."
                )
            elif not os.access(tmp_file_dir, os.W_OK):
                logger.warn("The TUS_TMP_FILE_DIR is not writable")
            else:
                TUS_ENABLED = True
                logger.info("tus file upload support is successfully " "configured")
    except ImportError:
        logger.warn(
            "TUS_ENABLED is set; however, tus python package is " "not installed"
        )
else:
    try:
        import tus

        tus  # pyflakes
    except ImportError:
        pass
    else:
        logger.warn(
            "You have the tus python package installed but it is "
            "not configured for this plone client"
        )


class FileUploadView(BrowserView):
    """
    Handle file uploads with potential
    special handling of TUS resumable uploads
    """

    tus_uid = None

    def __contains__(self, uid):
        return self.tus_uid and self.tus_uid == uid

    def __getitem__(self, uid):
        if self.tus_uid is None:
            self.tus_uid = uid
            self.__doc__ = "foobar"  # why is this necessary?
            return self
        else:
            raise KeyError

    def __call__(self):
        # Check if user has permission to add content here
        sm = getSecurityManager()
        if not sm.checkPermission(AddPortalContent, self.context):
            response = self.request.RESPONSE
            response.setStatus(403)
            return "You are not authorized to add content to this folder."

        req = self.request
        tusrequest = False
        if TUS_ENABLED:
            adapter = Zope2RequestAdapter(req)
            tus = Tus(adapter, **tus_settings)
            if tus.valid:
                tusrequest = True
                tus.handle()
                if not tus.upload_finished:
                    return
                else:
                    filename = req.getHeader("FILENAME")
                    if tus.send_file:
                        filedata = req._file
                        filedata.filename = filename
                    else:
                        filepath = req._file.read()
                        filedata = open(filepath)
        if not tusrequest:
            if req.REQUEST_METHOD != "POST":
                return
            filedata = self.request.form.get("file", None)
            if filedata is None:
                return
            filename = filedata.filename
        content_type = mimetypes.guess_type(filename)[0] or ""

        if not filedata:
            return

        ctr = getToolByName(self.context, "content_type_registry")
        type_ = ctr.findTypeName(filename.lower(), content_type, "") or "File"

        # Now check that the object is not restricted to be added in the
        # current context
        allowed_ids = [fti.getId() for fti in self.context.allowedContentTypes()]
        if type_ not in allowed_ids:
            response = self.request.RESPONSE
            response.setStatus(403)
            if type_ == "File":
                return "You cannot add a File to this folder, try another one"
            if type_ == "Image":
                return "You cannot add an Image to this folder, " "try another one"

        factory = IDXFileFactory(self.context)
        obj = factory(filename, content_type, filedata)

        result = {"type": "", "size": 0}

        if "File" in obj.portal_type:
            result["size"] = obj.file.getSize()
            result["type"] = obj.file.contentType
        elif "Image" in obj.portal_type:
            result["size"] = obj.image.getSize()
            result["type"] = obj.image.contentType

        if tusrequest:
            tus.cleanup_file()
        result.update(
            {
                "url": obj.absolute_url(),
                "name": obj.getId(),
                "UID": IUUID(obj),
                "filename": filename,
            }
        )

        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        return json.dumps(result)


class AllowUploadView(BrowserView):
    def __call__(self):
        """Return JSON structure to indicate if File or Image uploads are
        allowed in the current container.
        """
        self.request.response.setHeader(
            "Content-Type", "application/json; charset=utf-8"
        )
        context = self.context
        if self.request.form.get("path"):
            context = context.unrestrictedTraverse(self.request.form.get("path"))

        allow_images = False
        allow_files = False
        if IFolder.providedBy(context):
            allowed_types = [t.getId() for t in context.allowedContentTypes()]
            allow_images = "Image" in allowed_types
            allow_files = "File" in allowed_types

        return json.dumps(
            {
                "allowUpload": allow_images or allow_files,
                "allowImages": allow_images,
                "allowFiles": allow_files,
            }
        )
