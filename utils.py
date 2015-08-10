import os
import re
from django.conf import settings
from boto import connect_s3
from boto.s3.key import Key


class Site:
    def get_or_create_bucket(self, connection=None):
        """
        Gets an s3 bucket by name or creates a new bucket if the bucket does not
        exist, then configures the bucket as a website
        """
        if connection is None:
            connection = connect_s3(self.aws_access_key_id,
                                    self.aws_secret_access_key)
        bucket = connection.create_bucket(self.name, policy='public-read')
        bucket.configure_website(suffix='index.html', error_key='error.html')

    def create_file_dict(self):
        """
        Creates a dictionary of files from the content_directory with relative
        paths as keys and absolute paths as values (keys for files at root level
        do not include the './' prefix)
        """
        site_files = {}
        for root, dir_names, file_names in os.walk(self.content_directory):
            for file_name in file_names:
                rel_path = os.path.relpath(root, self.content_directory)
                if rel_path == '.':
                    key = file_name
                else:
                    key = os.path.join(rel_path, file_name)
                value = os.path.join(root, file_name)
                site_files[key] = value
        self.site_files = site_files

    def upload_site_files(self, bucket=None, connection=None):
        """
        Uploads files in site_files dictionary to bucket
        """
        if connection is None:
            connection = connect_s3(self.aws_access_key_id,
                                    self.aws_secret_access_key)
        if bucket is None:
            bucket = connection.get_bucket(self.name)
        for key, value in self.site_files.iteritems():
            k = Key(bucket)
            k.key = key
            k.set_contents_from_filename(value, policy='public-read')

    def delete_redundant_objects(self, bucket=None, connection=None):
        """
        Deletes objects from bucket that aren't in site_files dictionary
        """
        if connection is None:
            connection = connect_s3(self.aws_access_key_id,
                                    self.aws_secret_access_key)
        if bucket is None:
            bucket = connection.get_bucket(self.name)
        bucket_list_result = bucket.list()
        obsolete_keys = []
        for key in bucket_list_result:
            if key.name not in self.site_files:
                obsolete_keys.append(key.name)
        bucket.delete_keys(obsolete_keys)

    def publish_site(self):
        """
        Gets existing bucket or creates and configures a new bucket as a website,
        uploads files from the content_directory, then deletes redundant objects
        from the bucket
        """
        connection = connect_s3(self.aws_access_key_id,
                                self.aws_secret_access_key)
        self.get_or_create_bucket(connection=connection)
        bucket = connection.get_bucket(self.name)
        self.create_file_dict()
        self.upload_site_files(bucket=bucket, connection=connection)
        self.delete_redundant_objects(bucket=bucket, connection=connection)

    def delete_site(self):
        """
        Deletes the s3 bucket
        """
        connection = connect_s3(self.aws_access_key_id,
                                self.aws_secret_access_key)
        bucket = connection.get_bucket(self.name)
        bucket_list_result = bucket.list()
        bucket.delete_keys([key.name for key in bucket_list_result])
        bucket.delete()

    def validate_site_name(self, name):
        """
        Ensures the site name is DNS compliant and creates a secondary name with
        the 'www' prefix if the site name doesn't include it and a secondary name
        without the 'www' prefix if the site name does include it.
        """
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if all(allowed.match(x) for x in name.split(".")):
            self.name = name
        else:
            raise ValueError('{} is not a DNS compliant name.'.format(name))
        if name.split('.')[0] == 'www':
            self.secondary_name = name.partition('www.')[2]
        else:
            self.secondary_name = 'www.{}'.format(name)

    def __init__(self, name,
                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                 content_directory=settings.CONTENT_DIRECTORY):
        self.validate_site_name(name)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.content_directory = content_directory
