import os

from .base import *

# Throttle requests in production
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = float(os.getenv("AUTOTHROTTLE_START_DELAY", 1.5))
AUTOTHROTTLE_MAX_DELAY = float(os.getenv("AUTOTHROTTLE_MAX_DELAY", 30.0))
AUTOTHROTTLE_TARGET_CONCURRENCY = float(
    os.getenv("AUTOTHROTTLE_TARGET_CONCURRENCY", 3.0)
)

SENTRY_DSN = os.getenv("SENTRY_DSN")

EXTENSIONS = {"scrapy_sentry.extensions.Errors": 10}

FEED_EXPORTERS = {"json": "scrapy.exporters.JsonItemExporter"}

FEED_FORMAT = "json"

FEED_STORAGES = {"s3": "scrapy.extensions.feedexport.S3FeedStorage"}

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")

FEED_URI = f"s3://{S3_BUCKET}/%(time)s/%(name)s.json"
