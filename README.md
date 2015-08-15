# Djaws
### A small Django app for publishing the contents of a directory to an Amazon S3 bucket which is then configured to serve the contents as a static website  

#### To do
* Add option to register domain name with route53
* Add tests / error handling
* Package it up
* Update this documentation

#### Usage
**Add configuration to `settings.py`**

    # Example Djaws configuration with a CONTENT_DIRECTORY in the Django project directory

    CONTENT_DIRECTORY = os.path.join(BASE_DIR, 'static_site_directory')
    AWS_ACCESS_KEY_ID = 'your access key ID'
    AWS_SECRET_ACCESS_KEY = 'your secret access key'

**Publish or update your site**

    from djaws import Site

    mysite = Site('example.com')
    mysite.publish_site()

**Delete your site**

    mysite.delete_site()

**Get list of nameservers**

Only available if `hosted_zone=True` set when site was published.

    nameservers = mysite.nameservers
    
---
*class* **Site**(name, aws\_access\_key\_id=settings.AWS\_ACCESS\_KEY\_ID, aws\_secret\_access\_key=settings.AWS\_SECRET\_ACCESS\_KEY, content\_directory=settings.CONTENT\_DIRECTORY)

  * *parameters:*

      *  name - (str) must be a string that complies with the [s3 bucket naming rules](http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules). Automatically converted to lowercase.

      * aws\_access\_key\_id - (str) your amazon web services access key. Defaults to access key configured in settings.py.

      * aws\_secret\_access\_key - (str) your amazon web services secret key. Defaults to secret key configured in settings.py.

      * content\_directory - (str) the directory that contains the static site files. Defaults to the directory configured in settings.py.

  * *method* **Site.publish\_site**(hosted_zone=False, location='')

 Creates and configures a new bucket as a website as well as a secondary redirected bucket if they don't already exist. Then uploads files from the `content_directory` to the primary website bucket and deletes any redundant objects from the bucket and creates an optional hosted zone with alias records for each bucket.

      * *parameters:*

        * hosted\_zone - (bool) if `True` creates a hosted zone with alias records for each bucket.

        * location - (str) a string specifying which region to create the buckets in. For options see [s3 regions](http://docs.aws.amazon.com/general/latest/gr/rande.html#s3_region). Defaults to US standard.

  * *method* **Site.delete_site**()

 Deletes the s3 buckets and any associated hosted zone.
