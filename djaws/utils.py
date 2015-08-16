import os
import re
import hashlib
from django.conf import settings
from boto import connect_s3
from boto import connect_route53
from boto.s3.key import Key
from boto.s3.website import RedirectLocation


def hashfile(a_file, hasher, blocksize=65536):
    buf = a_file.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = a_file.read(blocksize)
    return hasher.hexdigest()


class Site:
    # A LOCATIONS dictionary because Hosted Zone ID's are not available via
    # the API. http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region
    LOCATIONS = {
        'ap-northeast-1':
            {'website_endpoint': 's3-website-ap-northeast-1.amazonaws.com',
             'hosted_zone_id': 'Z2M4EHUR26P7ZW'},
        'ap-southeast-1':
            {'website_endpoint': 's3-website-ap-southeast-1.amazonaws.com',
             'hosted_zone_id': 'Z3O0J2DXBE1FTB'},
        'ap-southeast-2':
            {'website_endpoint': 's3-website-ap-southeast-2.amazonaws.com',
             'hosted_zone_id': 'Z1WCIGYICN2BYD'},
        'sa-east-1':
            {'website_endpoint': 's3-website-sa-east-1.amazonaws.com',
             'hosted_zone_id': 'Z7KQH4QJS55SO'},
        'us-west-1':
            {'website_endpoint': 's3-website-us-west-1.amazonaws.com',
             'hosted_zone_id': 'Z2F56UZL2M1ACD'},
        'us-west-2':
            {'website_endpoint': 's3-website-us-west-2.amazonaws.com',
             'hosted_zone_id': 'Z3BJ6K6RIION7M'},
        '':
            {'website_endpoint': 's3-website-us-east-1.amazonaws.com',
             'hosted_zone_id': 'Z3AQBSTGFYJSTF'},
        'eu-west-1':
            {'website_endpoint': 's3-website-eu-west-1.amazonaws.com',
             'hosted_zone_id': 'Z1BKCTXD74EZPE'},
        'eu-central-1':
            {'website_endpoint': 's3-website.eu-central-1.amazonaws.com',
             'hosted_zone_id': 'Z21DNDUVLTQW6Q'}
    }

    def create_alternate_name(self, name):
        """
        Returns `name` without 'www' prefix if it is included or with 'www'
        prefix if it is not included.
        """
        if name.split('.')[0] == 'www':
            return name.partition('www.')[2]
        else:
            return 'www.{}'.format(name)

    def create_buckets(self, s3_connection=None, location=''):
        """
        Creates and configures a new bucket as a website. Also creates and
        configures a secondary bucket that is redirected to the primary website
        bucket. The buckets are created using `name` and `secondary_name`
        respectively.

        If the buckets already exist no new buckets are created.
        """
        self.validate_location(location)
        if s3_connection is None:
            s3_connection = connect_s3(self.aws_access_key_id,
                                       self.aws_secret_access_key)
        # create primary bucket and configure as website
        bucket = s3_connection.create_bucket(self.name,
                                             policy='public-read',
                                             location=self.location)
        bucket.configure_website(suffix='index.html', error_key='error.html')
        # create secondary bucket that redirects to primary bucket
        secondary_bucket = s3_connection.create_bucket(self.secondary_name,
                                                       location=self.location)
        redirect_location = RedirectLocation(hostname=self.name)
        secondary_bucket.configure_website(redirect_all_requests_to=redirect_location)

    def create_file_dict(self):
        """
        Returns a dictionary of files from `content_directory` with relative
        paths as keys and a nested dictionary with absolute paths and md5 hashes
        as values. Keys for files at root level do not include the './' prefix.
        """
        site_files = {}
        for root, dir_names, file_names in os.walk(self.content_directory):
            for file_name in file_names:
                rel_path = os.path.relpath(root, self.content_directory)
                if rel_path == '.':
                    key = file_name
                else:
                    key = os.path.join(rel_path, file_name)
                file_path = os.path.join(root, file_name)
                etag = hashfile(open(file_path, 'rb'), hashlib.md5())
                site_files[key] = {'path': file_path, 'etag': etag}
        return site_files

    def create_hosted_zone(self):
        """
        Creates a hosted zone with alias records for the site and adds a list
        of the nameservers to `self.nameservers`. Does not create a new zone if
        a zone with `self.name` already exists.
        """
        r53_connection = connect_route53(self.aws_access_key_id,
                                         self.aws_secret_access_key)
        # Creates zone only if zone does not already exist
        zone = r53_connection.get_zone(self.name + '.')
        if zone is None:
            zone = r53_connection.create_zone(self.name + '.')
            # Adds alias records for `site.name` and `site.secondary_name` buckets
            records = zone.get_records()
            for name in (self.name, self.secondary_name):
                records.add_change('CREATE', name, 'A',
                                   alias_hosted_zone_id=self.hosted_zone_id,
                                   alias_dns_name=self.website_endpoint,
                                   alias_evaluate_target_health=False)
            records.commit()
            self.nameservers = zone.get_nameservers()

    def delete_hosted_zone(self, r53_connection=None, zone=None):
        """
        Deletes a hosted zone.
        """
        if r53_connection is None:
            r53_connection = connect_route53(self.aws_access_key_id,
                                             self.aws_secret_access_key)
        if zone is None:
            zone = r53_connection.get_zone(self.name + '.')
        zone.delete_a(self.name + '.', all=True)
        zone.delete_a(self.secondary_name + '.', all=True)
        zone.delete()

    def delete_site(self):
        """
        Deletes the s3 buckets and any associated hosted zone.
        """
        s3_connection = connect_s3(self.aws_access_key_id,
                                   self.aws_secret_access_key)
        r53_connection = connect_route53(self.aws_access_key_id,
                                         self.aws_secret_access_key)
        for bucket_name in (self.name, self.secondary_name):
            bucket = s3_connection.get_bucket(bucket_name)
            bucket_list_result = bucket.list()
            bucket.delete_keys([key.name for key in bucket_list_result])
            bucket.delete()
        zone = r53_connection.get_zone(self.name + '.')
        if zone is not None:
            self.delete_hosted_zone(r53_connection=r53_connection, zone=zone)

    def publish_site(self, hosted_zone=False, location=''):
        """
        Creates and configures a new bucket as a website as well as a secondary
        redirected bucket if they don't already exist, then uploads new and changed
        files from the `content_directory` to the website bucket, deletes any
        redundant objects from the bucket and creates an optional hosted zone.
        """
        self.validate_location(location)
        s3_connection = connect_s3(self.aws_access_key_id,
                                   self.aws_secret_access_key)
        self.create_buckets(s3_connection=s3_connection, location=self.location)
        bucket = s3_connection.get_bucket(self.name)
        self.site_files = self.create_file_dict()
        self.upload_site_files(bucket=bucket, s3_connection=s3_connection)
        if hosted_zone:
            self.create_hosted_zone()

    def upload_site_files(self, bucket=None, s3_connection=None):
        """
        Uploads files in `site_files` dictionary to the website bucket if a file
        with the same etag doesn't already exist in the bucket and deletes any
        files in the bucket that aren't in the `site_files` dictionary.
        """
        if s3_connection is None:
            s3_connection = connect_s3(self.aws_access_key_id,
                                       self.aws_secret_access_key)
        if bucket is None:
            bucket = s3_connection.get_bucket(self.name)
        bucket_list_result = bucket.list()
        s3_keys = {}
        obsolete_s3_keys = []
        for key in bucket_list_result:
            s3_keys[key.name] = key.etag.strip('"')
            if key.name not in self.site_files:
                obsolete_s3_keys.append(key.name)
        bucket.delete_keys(obsolete_s3_keys)
        for key, value in self.site_files.iteritems():
            if (key not in s3_keys) or (value['etag'] != s3_keys[key]):
                k = Key(bucket)
                k.key = key
                k.set_contents_from_filename(value['path'], policy='public-read')

    def validate_location(self, location):
        if location in self.LOCATIONS:
            self.location = location
            self.hosted_zone_id = self.LOCATIONS[self.location]['hosted_zone_id']
            self.website_endpoint = self.LOCATIONS[self.location]['website_endpoint']
        else:
            raise ValueError('{} is not a valid location. Must be one of {}'
                             .format(location, self.LOCATIONS.keys()))

    def validate_site_name(self, name):
        """
        Ensures `name` is DNS compliant
        """
        allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        if all(allowed.match(x) for x in name.split(".")):
            self.name = name
            self.secondary_name = self.create_alternate_name(name)
        else:
            raise ValueError('{} is not a DNS compliant name.'.format(name))

    def __init__(self, name,
                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                 content_directory=settings.CONTENT_DIRECTORY):
        self.validate_site_name(name)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.content_directory = content_directory
