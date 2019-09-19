import os.path
import string
import json
from logger import logger
from save import Save
import codecs


def load_json_file(filename):
    log = logger()
    if not filename:
        log.warn("load_json_file called without filename")
        return None
    if not os.path.isfile(filename):
        log.error("Unable to find requested file %s" % filename)
        return None
    log.info("loading json file %s" % filename)
    encodings = ['utf-8', 'windows-1250', 'windows-1252', 'ansi']
    data = None
    for encoding in encodings:
        try:
            data = codecs.open(filename, 'r', encoding).read()
        except UnicodeDecodeError as e:
            log.debug("Unable to parse in encoding %s." % encoding)
        else:
            log.debug("loaded using encoding %s." % encoding)
            break
    if not data:
        log.error("Unable to find encoding for %s." % filename)
        return None
    j_data = json.loads(data)
    return j_data


def load_file_by_type(ident, filesystem, save_type):
    filename = filesystem.get_json_filename_for_type(ident, save_type)
    return load_json_file(filename)


def describe_files_by_type(filesystem, save_type):
    output = []
    for filename in filesystem.get_filenames_by_type(save_type):
        json = load_file_by_type(filename, filesystem, save_type)
        name = json['SaveName']
        output.append((name, filename))
    return output


def download_file(filesystem, ident, save_type):
    """Attempt to download all files for a given savefile"""
    log = logger()
    log.info("Downloading %s file %s (from %s)" %
             (save_type.name, ident, filesystem))
    filename = filesystem.get_json_filename_for_type(ident, save_type)
    if not filename:
        log.error("Unable to find data file.")
        return False
    try:
        data = load_json_file(filename)
    except IOError as e:
        log.error("Unable to read data file %s (%s)" % (filename, e))
        return False
    if not data:
        log.error("Unable to read data file %s" % filename)
        return False

    save = Save(savedata=data,
                filename=filename,
                ident=ident,
                save_type=save_type,
                filesystem=filesystem)

    if save.isInstalled:
        log.info("All files already downloaded.")
        return True

    successful = save.download()
    if successful:
        log.info("All files downloaded.")
    else:
        log.info("Some files failed to download.")
    return successful
