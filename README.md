# Djaws
### A small Django app for publishing the contents of a directory to an Amazon S3 bucket and configuring the bucket to serve the contents as a static website  

##### To do
* Package it up
* Add tests
* Add Route 53 / Domain configuration

#### Usage
* Add configuration to `settings.py`
```
# Example Djaws configuration

CONTENT_DIRECTORY = os.path.join(BASE_DIR, 'your_static_site_directory_name')
AWS_ACCESS_KEY_ID = 'your access key ID'
AWS_SECRET_ACCESS_KEY = 'your secret access key'
```

* Publish your site
`bucket_name` must be a string that complies with [s3 bucket naming rules](http://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules) 
```
publish_site('bucket_name')
```

* Delete your site
```
delete_site('bucket_name')
```