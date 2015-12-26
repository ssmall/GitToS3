import os
import string
import tempfile
from zipfile import ZipFile

import json
import urllib2
import boto3

ARCHIVE_SUFFIX = "/archive/master.zip"
BUCKET_NAME = "smallfami.ly"

bucket = boto3.resource('s3').Bucket(BUCKET_NAME)


def handler(event, context):
    message = json.loads(event["Records"][0]["Sns"]["Message"])
    zip_url = "{}{}".format(message["repository"]["html_url"], ARCHIVE_SUFFIX)
    zip_url = string.replace(zip_url, "https", "http")
    print "Will download from {}".format(zip_url)
    response = urllib2.urlopen(zip_url)
    tmpfile_location = tempfile.mkstemp()[1]
    print "Writing ZIP contents to {}".format(tmpfile_location)
    with open(tmpfile_location, 'w') as tmpfile:
        tmpfile.write(response.read())
    unzip_dir = tempfile.mkdtemp()
    print "Unzipping to {}".format(unzip_dir)
    with ZipFile(tmpfile_location, 'r') as archive:
        archive.extractall(unzip_dir)
    content_root = os.path.join(unzip_dir, os.listdir(unzip_dir)[0])
    print "Deleting contents of S3 bucket '{}'".format(BUCKET_NAME)
    for item in bucket.objects.delete():
        for entry in item["Deleted"]:
            print "Deleted {}".format(entry["Key"])
    print "Uploading new files ..."
    for root, dirs, files in os.walk(content_root):
        relative_dir = string.replace(root, content_root, "")[1:]
        for file in files:
            full_path = os.path.join(root,file)
            relative_path = "{}/{}".format(relative_dir,file) if relative_dir else file
            print "{} -> {}".format(full_path, relative_path)
            bucket.upload_file(full_path,relative_path)

