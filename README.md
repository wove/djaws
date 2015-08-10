# Djaws
### A small Django app for publishing the contents of a directory to an Amazon S3 bucket and configuring the bucket to serve the contents as a static website  

#### To do
* Add Route 53 / domain configuration
* Add tests
* Package it up
* Update this documentation

#### Usage
**Add configuration to `settings.py`**

    # Example Djaws configuration

    CONTENT_DIRECTORY = os.path.join(BASE_DIR, 'static_site_directory')
    AWS_ACCESS_KEY_ID = 'your access key ID'
    AWS_SECRET_ACCESS_KEY = 'your secret access key'

**Publish or update your site**

 `name` must be a string that complies with the [s3 bucket naming rules](http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules) 

    from djaws import Site

    site = Site('name')
    site.publish_site()

**Delete your site**

    site.delete_site()