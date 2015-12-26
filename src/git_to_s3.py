import os
import string
import tempfile
from zipfile import ZipFile

import json
import urllib2
import boto3
import re

ARCHIVE_SUFFIX = "/archive/master.zip"
BUCKET_NAME = "smallfami.ly"
REGION = "us-west-1"

bucket = boto3.resource('s3', region_name=REGION).Bucket(BUCKET_NAME)


def get_content_type(filename):
    if re.match(r'.*\.html', filename, re.IGNORECASE):
        return "text/html"
    elif re.match(r'.*\.jpg', filename, re.IGNORECASE):
        return "image/jpeg"
    elif re.match(r'.*\.png', filename, re.IGNORECASE):
        return "image/png"
    elif re.match(r'.*\.css', filename, re.IGNORECASE):
        return "text/css"
    else:
        return None


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
            full_path = os.path.join(root, file)
            relative_path = "{}/{}".format(relative_dir, file) if relative_dir else file
            content_type = get_content_type(file)
            print "{} -> {} (Content type: {})".format(full_path, relative_path, content_type)
            args = [full_path, relative_path]
            if content_type:
                args.append({'ContentType': content_type})
            bucket.upload_file(*args)
