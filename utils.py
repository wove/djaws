import os
from django.conf import settings
from boto import connect_s3
from boto.s3.key import Key


def get_or_create_bucket(bucket_name, connection):
    """
    Gets an s3 bucket by name or creates a new bucket if the bucket does not
    exist, then configures the bucket as a website
    """
    bucket = connection.create_bucket(bucket_name, policy='public-read')
    bucket.configure_website(suffix='index.html', error_key='error.html')
    return bucket


def create_file_dict(content_directory):
    """
    Creates a dictionary of files from the content_directory with relative
    paths as keys and absolute paths as values (keys for files at root level do
    not include the './' prefix)
    """
    site_files = {}
    for root, dir_names, file_names in os.walk(content_directory):
        for file_name in file_names:
            rel_path = os.path.relpath(root, content_directory)
            if rel_path == '.':
                key = file_name
            else:
                key = os.path.join(rel_path, file_name)
            value = os.path.join(root, file_name)
            site_files[key] = value
    return site_files


def upload_site_files(bucket, site_files):
    """
    Uploads files in site_files dictionary to bucket
    """
    for key, value in site_files.iteritems():
        k = Key(bucket)
        k.key = key
        k.set_contents_from_filename(value, policy='public-read')


def delete_redundant_s3_objects(bucket, site_files):
    """
    Deletes objects from bucket that aren't in site_files dictionary
    """
    bucket_list_result = bucket.list()
    obsolete_keys = []
    for key in bucket_list_result:
        if key.name not in site_files:
            obsolete_keys.append(key.name)
    bucket.delete_keys(obsolete_keys)


def publish_site(bucket_name,
                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                 content_directory=settings.CONTENT_DIRECTORY):
    """
    Gets existing bucket or creates and configures a new bucket as a website,
    uploads files from the content_directory, then deletes redundant objects
    from the bucket
    """
    connection = connect_s3(aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)
    bucket = get_or_create_bucket(bucket_name, connection)
    site_files = create_file_dict(content_directory)
    upload_site_files(bucket, site_files)
    delete_redundant_s3_objects(bucket, site_files)


def delete_site(bucket_name,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY):
    """
    Deletes the s3 bucket
    """
    connection = connect_s3(aws_access_key_id=aws_access_key_id,
                            aws_secret_access_key=aws_secret_access_key)
    bucket = connection.get_bucket(bucket_name)
    bucket_list_result = bucket.list()
    bucket.delete_keys([key.name for key in bucket_list_result])
    bucket.delete()
