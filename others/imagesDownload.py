#!/usr/bin/env python3
# encoding UTF-8

# Author: Pavel Raur (xraurp00@stud.fit.vutbr.cz)
# Project: wikidata2
# Description: Downloads images and other media files from parsed wikidata dump.

import os  # filesystem manipulation
import sys  # stderr, stdout, exit
import requests  # download images over http
# import magic  # check downloaded file type
import json
import argparse
import hashlib  # for getting wikimedia path url

# get script name
SCRIPT_NAME = os.path.basename(sys.argv[0])


def get_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '--image-db', '-d',
        help='Image database file.',
        default='',
        type=str
    )
    argparser.add_argument(
        '--image-folder', '-f',
        help='Folder where to store images.',
        default='/mnt/data/kb/images/wikimedia/commons/',
        type=str
    )
    argparser.add_argument(
        '--no-download',
        help='Do not download images during processing.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '--do-not-save-db',
        help='Do not save changes to image database after finish.',
        default=False,
        action='store_true'
    )
    action = argparser.add_mutually_exclusive_group()
    action.add_argument(
        '--image', '-i',
        help='Name of image to process.',
        type=str
    )
    action.add_argument(
        '--image-list', '-l',
        help='File with image list to process. Each image url should be on separate line.',
        type=str
    )
    action.add_argument(
        '--download-missing', '-m',
        help='Downloads images that are in database but arn\'t downloaded.',
        default=False,
        action='store_true'
    )
    action.add_argument(
        '--build-db', '-b',
        help='Builds or updates picture database from images stared in image folder.',
        default=False,
        action='store_true'
    )
    action.add_argument(
        '--fix-names',
        help='Renames images that were imported to database and doesn\'t use the 255 char long names.',
        default=False,
        action='store_true'
    )
    argparser.add_argument(
        '--verbose', '-v',
        help='Prints additional information about what is being done to stderr and stdout. '
             'Useful when building db, fixing names or downloading missing images.',
        default=False,
        action='store_true'
    )
    return argparser.parse_args()


class ImageDownloadError(Exception):
    """Error thrown if download fails"""

    def __init__(self, status_code, url, strerror="Failed to download image!"):
        self.status_code = status_code
        self.url = url
        self.strerror = strerror

    def __str__(self):
        return self.strerror + ((" url: " + self.url) if self.url else "") \
               + (((", " if self.url else "") + " status_code: " + str(self.status_code)) if self.status_code else "")


class ImageDownloader:
    """
    Download images from list. Generates image database.
    """

    def __init__(self, image_folder, database_path=''):
        self.wikimedia_url_prefix = 'https://upload.wikimedia.org/wikipedia/commons/'
        self.db_path = database_path
        self.image_folder = image_folder
        self.images = {}
        if database_path:
            try:
                self.images = self.load_db()
            except FileNotFoundError:
                # create new db and save it to db_path
                pass

    def load_db(self):
        """
        Loads picture database from json file.
        :return: dict with picture database
        :raise JSONDecodeError if json file is corrupted or not a json
        :raise OSError if file is not found or can't be opened
        """
        file = open(self.db_path, 'r')
        content = json.load(file)
        file.close()
        return content

    def save_db(self):
        """
        Dumps picture database to json file.
        :raise OSError if file is not writable
        """
        file = open(self.db_path, 'w')
        json.dump(self.images, file, indent=4, sort_keys=True)
        file.close()

    def get_image_wikimedia_url(self, image_name):
        """
        Appends url prefix and image specific path prefix for wikimedia
        :param image_name: filename of the image
        :return: image wikimedia url
        """
        img_hash = hashlib.md5(image_name.encode('UTF-8')).hexdigest()
        url = self.wikimedia_url_prefix + img_hash[:1] + '/' + img_hash[:2] + '/' + image_name
        return url

    def get_image_fs_path(self, image_name):
        """
        Creates image filesystem path and shortens filename to 255 chars.
        :param image_name: name of the image (image key can't be used, hash will differ!!)
        :return: image filename with path
        """
        img_hash = hashlib.md5(image_name.encode('UTF-8')).hexdigest()
        img_key = self.get_key_from_name(image_name)
        path = os.path.join(self.image_folder, img_hash[:1], img_hash[:2], img_key)
        return path

    def download_image(self, image_name):
        """
        Downloads given image.
        :param image_name: name of the image
        :raise requests.exceptions.RequestException if connection fails (Inherited from OSError)
        :raise OSError if picture cannot be written to file
        :raise ImageDownloadError if image could not be downloaded
        """
        url = self.get_image_wikimedia_url(image_name)  # get url where image is located
        path = self.get_image_fs_path(image_name)  # get name of file where image will be stored after download
        request = requests.get(url)
        if request.status_code == 200:
            file = open(path, 'wb')
            file.write(request.content)
            file.close()
            if self.is_in_db(image_name):  # change status if image is in db
                self.images[self.get_key_from_name(image_name)]['downloaded'] = True
        else:
            # TODO
            #  check for redirects
            raise ImageDownloadError(request.status_code, url)

    @staticmethod
    def get_key_from_name(image_name):
        """
        Creates database key from image name.
        Shrinks image name to 255 chars keeping suffix.
        :param image_name: name of the image
        :return image db key
        """
        img_key = image_name
        if len(img_key) > 255:
            # cut the name to 255 chars - length of suffix - 1 (.)
            # append . and suffix
            img_key = image_name[:255 - len(image_name.split('.')[-1]) - 1] + '.' + image_name.split('.')[-1]
        return img_key

    def add_image_to_db(self, image_name, downloaded=False):
        """
        Adds new image to database of images, if not already there.
        :param image_name: name of the image
        :param downloaded: tels if image is already downloaded or not
        :return True if image is downloaded, false otherwise
        """
        img_key = self.get_key_from_name(image_name)
        if img_key not in self.images:
            self.images[img_key] = {'downloaded': downloaded, 'original_name': image_name}
        return self.images[img_key]['downloaded']

    def is_in_db(self, image_name):
        """
        Checks if image is in database.
        :param image_name: name or key of the image
        :return True if image is in db, else False
        """
        img_key = self.get_key_from_name(image_name)
        return True if img_key in self.images else False

    def is_downloaded(self, image_name):
        """
        Checks if image is downloaded.
        :param image_name: name or key of the image
        :return True if image is downloaded, else False
        """
        img_key = self.get_key_from_name(image_name)
        if img_key in self.images:
            return self.images[img_key]['downloaded']
        return False

    def add_from_file(self, fd, download=True):
        """
        Adds images listed in file. Each image name must be on separate line.
        Images are downloaded by default.
        :param fd: file descriptor
        :param download: enable automatic download after image is added to db
        """
        images = fd.readlines()
        for image in images:
            if image[-1] == '\n':  # cut eol
                image = image[:-1]
            if not self.add_image_to_db(image):  # add img to db and check if is downloaded
                if download:  # download newly added images if download is enabled
                    try:
                        self.download_image(self.get_image_wikimedia_url(image))
                    except OSError as e:
                        sys.stderr.write("Failed to write image to file: " + str(e.filename)
                                         + ", image: " + image + "\n")
                    except ImageDownloadError as e:
                        sys.stderr.write("Failed to download image: url: " + str(e.url) + ", response: "
                                         + str(e.status_code) + ", error msg: " + str(e.strerror) + "\n")

    def build_db(self, verbose=False):
        """
        Creates or updates image database from images downloaded on disk.
        :param verbose: list files, that are already in database
                        (useful for creating new db and checking conflicting key names)
        """
        dirs = [os.scandir(self.image_folder)]  # list of directories to loop through (deep search)
        while len(dirs) > 0:
            # get next file
            try:
                file = next(dirs[len(dirs) - 1])
            except StopIteration:  # no more files in the folder
                dirs.pop()
                continue
            # add to dirs to loop through
            if file.is_dir():
                dirs.append(os.scandir(file))
            # add to image db
            elif file.is_file():
                if verbose and self.is_in_db(file.name):
                    sys.stderr.write("Conflicting image found: " + file.name + " conflicts with: "
                                     + self.images[self.get_key_from_name(file.name)]['original_name']
                                     + "\n")
                # will not do anything if image is already in database
                self.add_image_to_db(file.name, True)
            # TODO
            #  symlink or what is this?
            else:
                sys.stderr.write("Unknown file type: " + file.name + "\n")

    def download_missing(self, verbose=False):
        """
        Downloads images that are in db but aren't downloaded.
        :param verbose: print names of downloaded images
        """
        to_download = [image['original_name'] for image in self.images if not image['downloaded']]
        for img in to_download:
            try:
                self.download_image(img)
                if verbose:
                    sys.stdout.write("Image downloaded: " + img + "\n")
            except ImageDownloadError as e:
                sys.stderr.write("Failed to download image! url: " + e.url + ", status code: " + e.status_code
                                 + ", Error text: " + e.strerror + "\n")
            except requests.exceptions.RequestException:
                sys.stderr.write("Connection to server failed! Image to download: " + img + "\n")
            except OSError as e:
                sys.stderr.write("Failed to write to file! Filename: " + e.filename + "\n")

    def fix_file_names(self, verbose=False):
        """
        Renames images to their db key names (255 chars long).
        :param verbose: print renamed files
        """
        for img in self.images:
            new_name = self.get_image_fs_path(img['original_name'])
            old_name = os.path.join(os.path.dirname(new_name), img['original_name'])
            if os.path.exists(old_name):
                # check if file exists before replacement (unix doesn't check automatically)
                if os.path.exists(new_name):
                    sys.stderr.write("Failed to rename " + old_name + " to " + new_name + "! File already exists!\n")
                else:
                    try:
                        os.rename(old_name, new_name)
                        if verbose:
                            sys.stdout.write("File renamed from " + old_name + " to " + new_name + "\n")
                    except OSError:
                        sys.stderr.write("Failed to rename " + old_name + " to " + new_name + "! Check privileges!\n")


def main():
    args = get_args()
    downloader = ImageDownloader(args.image_folder, args.image_db)

    # download single image
    if args.image:
        if args.image_db:  # add image to db
            downloader.add_image_to_db(args.image)
        if not args.no_download:
            downloader.download_image(args.image)

    # download images from list in given file
    elif args.image_list:
        with open(args.image_list, 'r') as img_list:
            if args.image_db:  # add images to db
                downloader.add_from_file(img_list, not args.no_download)
            elif not args.no_download:  # download only
                for image in img_list:
                    if image[-1] == '\n':
                        image = image[:-1]
                    downloader.download_image(image)

    # build db from already downloaded images
    elif args.build_db:
        downloader.build_db(args.verbose)

    # download missing images
    elif args.download_missing:
        downloader.download_missing(args.verbose)

    # rename files to use 255 char names (useful for importing old images to db)
    elif args.fix_names:
        downloader.fix_file_names(args.verbose)

    # save images db
    if args.image_db and not args.do_not_save_db:
        downloader.save_db()

    return 0


if __name__ == '__main__':
    sys.exit(main())
