import os
import zipfile
import json
import urllib.error
from logger import logger
from url import Url
from save_type import SaveType
from filesystem import FileSystem, get_default_fs


def validate_metadata(metadata):
    # TODO: extract into new class
    if not metadata or type(metadata) is not dict:
        return False
    return 'Ver' in metadata and 'Id' in metadata and 'Type' in metadata


def importPak(filesystem, filename):
    log = logger()
    log.debug("About to import {} into {}.".format(filename, filesystem))
    if not os.path.isfile(filename):
        log.error("Unable to find mod pak {}".format(filename))
        return False
    if not zipfile.is_zipfile(filename):
        log.error("Mod pak {} format appears corrupt.".format(filename))
        return False
    try:
        with zipfile.ZipFile(filename, 'r') as zf:
            bad_file = zf.testzip()
            if bad_file:
                log.error(
                    "At least one corrupt file found in {} - {}".format(filename, bad_file))
                return False
            if not zf.comment:
                # TODO: allow overrider
                log.error(
                    "Missing pak header comment in {}. Aborting import.".format(filename))
                return False
            metadata = json.loads(zf.comment.decode('utf-8'))
            if not validate_metadata(metadata):
                log.error(
                    "Unable to read pak header comment in {}. Aborting import.".format(filename))
                return False
            log.info("Extracting {} pak for id {} (pak version {})".format(
                metadata['Type'], metadata['Id'], metadata['Ver']))
            for name in zf.namelist():
                # Note that zips always use '/' as the seperator it seems.
                start = name.split('/')[0]
                if start == 'Saves':
                    log.debug("Extracting {} to {}.".format(
                        name, filesystem.basepath))
                    zf.extract(name, filesystem.basepath)
                else:
                    log.debug("Extracting {} to {}".format(
                        name, filesystem.modpath))
                    zf.extract(name, filesystem.modpath)
    except zipfile.BadZipFile as e:
        log.error("Mod pak {} format appears corrupt - {}.".format(filename, e))
    except zipfile.LargeZipFile as e:
        log.error(
            "Mod pak {} requires large zip capability - {}.\nThis shouldn't happen - please raise a bug.".format(filename, e))
    log.info("Imported {} successfully.".format(filename))
    return True


def get_save_urls(savedata):
    '''
    Iterate over all the values in the json file, building a (key,value) set of
    all the values whose key ends in "URL"
    '''
    log = logger()

    def parse_list(data):
        urls = set()
        for item in data:
            urls |= get_save_urls(item)
        return urls

    def parse_dict(data):
        urls = set()
        if not data:
            return urls
        for key in data:
            if type(data[key]) is not str or key == 'PageURL' or key == 'Rules':
                # If it isn't a string, it can't be an url.
                # Also don't save tablet state / rulebooks
                continue
            if key.endswith('URL') and data[key] != '':
                log.debug("Found {}:{}".format(key, data[key]))
                urls.add(data[key])
                continue
            protocols = data[key].split('://')
            if len(protocols) == 1:
                # not an url
                continue
            if protocols[0] in ['http', 'https', 'ftp']:
                # belt + braces.
                urls.add(data[key])
                log.debug("Found {}:{}".format(key, data[key]))
                continue
        for item in data.values():
            urls |= get_save_urls(item)
        return urls

    if type(savedata) is list:
        return parse_list(savedata)
    if type(savedata) is dict:
        return parse_dict(savedata)
    return set()


class Save:
    def __init__(self, savedata, filename, ident, filesystem, save_type=SaveType.workshop):
        log = logger()
        self.data = savedata
        self.ident = ident
        if self.data['SaveName']:
            self.save_name = self.data['SaveName']
        else:
            self.save_name = self.ident
        self.save_type = save_type
        self.filesystem = filesystem
        self.filename = filename
        # strip the local part off.
        fileparts = self.filename.split(os.path.sep)
        while fileparts[0] != 'Saves' and fileparts[0] != 'Mods':
            fileparts = fileparts[1:]
        self.basename = os.path.join(*fileparts)
        log.debug("filename: {},save_name: {}, basename: {}".format(
            self.filename, self.save_name, self.basename))
        self.load_assets_from_urls()

    def load_assets_from_urls(self):
        log = logger()
        self.urls = [Url(url, self.filesystem)
                     for url in get_save_urls(self.data)]
        self.missing = [x for x in self.urls if not x.exists]
        self.images = [x for x in self.urls if x.exists and x.isImage]
        self.models = [x for x in self.urls if x.exists and not x.isImage]
        log.debug("Urls found {}:{} missing, {} models, {} images".format(
            len(self.urls), len(self.missing), len(self.models), len(self.images)))

    def export(self, export_filename):
        log = logger()
        log.info("About to export %s to %s" % (self.ident, export_filename))
        zfs = FileSystem(base_path="")
        zipComment = {
            "Ver": 1,
            "Id": self.ident,
            "Type": self.save_type.name
        }

        # TODO: error checking.
        with zipfile.ZipFile(export_filename, 'w') as zf:
            zf.comment = json.dumps(zipComment).encode('utf-8')
            log.debug("Writing {} (base {}) to {}".format(self.filename, os.path.basename(
                self.filename), zfs.get_path_by_type(os.path.basename(self.filename), self.save_type)))
            zf.write(self.filename, zfs.get_path_by_type(
                os.path.basename(self.filename), self.save_type))
            for url in self.models:
                log.debug("Writing {} to {}".format(url.location,
                                                    zfs.get_model_path(os.path.basename(url.location))))
                zf.write(url.location, zfs.get_model_path(
                    os.path.basename(url.location)))
            for url in self.images:
                log.debug("Writing {} to {}".format(url.location,
                                                    zfs.get_model_path(os.path.basename(url.location))))
                zf.write(url.location, zfs.get_image_path(
                    os.path.basename(url.location)))
        log.info("File exported.")

    @property
    def isInstalled(self):
        """Is every url referenced by this save installed?"""
        return len(self.missing) == 0

    def download(self):
        log = logger()
        log.warn("About to download files for %s" % self.save_name)
        if self.isInstalled == True:
            log.info("All files already downloaded.")
            return True

        successful = True
        url_counter = 1
        for url in self.missing:
            log.warn("Downloading file {} of {} for {}".format(
                url_counter, len(self.missing), self.save_name))
            result = url.download()
            if not result:
                successful = False
            url_counter += 1

        self.load_assets_from_urls()
        log.info("All files downloaded.")
        return successful

    def __str__(self):
        result = "Save: %s\n" % self.data['SaveName']
        if len(self.missing) > 0:
            result += "Missing:\n"
            for x in self.missing:
                result += str(x)+"\n"
        if len(self.images) > 0:
            result += "Images:\n"
            for x in self.images:
                result += str(x)+"\n"
        if len(self.models) > 0:
            result += "Models:\n"
            for x in self.models:
                result += str(x)+"\n"
        return result


__all__ = ['Save']
