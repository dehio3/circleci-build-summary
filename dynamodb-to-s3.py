#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import decimal
import json
import logging.config
import settings
import sys
# import simplejson as json

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from pytz import timezone

# logging
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('__name__')

# env
GITHUB_ORGANIZATION_NAME = settings.GITHUB_ORGANIZATION_NAME
DYNAMODB_ENDPOINT = settings.DYNAMODB_ENDPOINT
DYNANODB_TABLE_NAME = settings.DYNANODB_TABLE_NAME
S3_BUCKET_NAME = settings.S3_BUCKET_NAME

# Helper class to convert a DynamoDB item to JSON.
# https://docs.aws.amazon.com/ja_jp/amazondynamodb/latest/developerguide/GettingStarted.Python.03.html


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if abs(o) % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def get_items_from_dynamodb(endpoint, table_name, query_key):
    """ Get Items From DynamoDB
    Args:
        endpoint(str)
        table_name(str)
        query_key(str)

    Return:
        items(dict)
    """
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=endpoint
    )
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            IndexName='sort_queued_at',
            KeyConditionExpression=Key('username').eq(GITHUB_ORGANIZATION_NAME)
            & Key('queued_at').begins_with(query_key)
        )
    except ClientError as e:
        logger.error(e.response['Error']['Message'])
        sys.exit(1)

    else:
        items = response['Items']
        logger.info("GetItem succeeded")

    return items


def upload_to_s3(bucket_name, local_object_name, s3_object_name):
    """ Upload data to S3
    Args:
         bucket_name (str)          : upload S3 bucket name
         local_object_name (str)    : local file path name
         s3_object_name (str)       : S3 object key name
    """
    s3 = boto3.resource('s3')

    # uplodad json data
    try:
        s3.Bucket(bucket_name).upload_file(local_object_name, s3_object_name)
    except Exception as err:
        logger.error(err)
        sys.exit(1)
    else:
        logger.info("S3 upload succeeded")


def main(event, lambda_context):
    logger.info('start')

    # get one hour ago time
    # 2019-09-19 06:01:00.757651+00:00
    now_time_utc = datetime.now(timezone('UTC'))
    one_hour_ago_time = now_time_utc - timedelta(hours=1)
    logger.info('one_hour_ago_time: {}'.format(one_hour_ago_time))

    # change timezone UTC to JST
    one_hour_ago_time_jst = one_hour_ago_time.astimezone(
        timezone('Asia/Tokyo'))
    logger.info('one_hour_ago_time_jst: {}'.format(one_hour_ago_time_jst))

    # make object name
    # https://docs.aws.amazon.com/ja_jp/athena/latest/ug/partitions.html
    s3_prefix_year = 'year={}'.format(
        "{0:%Y}".format(one_hour_ago_time_jst))
    s3_prefix_month = 'month={}'.format(
        "{0:%m}".format(one_hour_ago_time_jst))
    s3_prefix_day = 'day={}'.format(
        "{0:%d}".format(one_hour_ago_time_jst))
    s3_prefix_name = '{}/{}/{}'.format(s3_prefix_year,
                                       s3_prefix_month, s3_prefix_day)
    logger.info('s3_prefix_name: {}'.format(s3_prefix_name))

    s3_object_name = '{}.json'.format(
        "{0:%Y%m%d%H}".format(one_hour_ago_time_jst))
    logger.info('s3_object_name: {}'.format(s3_object_name))

    # get build summary from dynamodb
    # "queued_at": "2019-07-24T08:38:39.995Z"
    one_hour_ago_time_iso = one_hour_ago_time.replace(
        tzinfo=None).isoformat(timespec='hours')
    logger.info('one_hour_ago_time_iso: {}'.format(one_hour_ago_time_iso))
    # test
    # one_hour_ago_time_iso = "2019-07-24T08"

    # get dynamodb items
    items = get_items_from_dynamodb(
        DYNAMODB_ENDPOINT, DYNANODB_TABLE_NAME, one_hour_ago_time_iso)

    # make s3 uploda tmp file
    s3_object_tmp_name = '/tmp/{}'.format(s3_object_name)
    s3_object_tmp_file = open(s3_object_tmp_name, 'w')

    for item in items:
        item_json = json.dumps(item, cls=DecimalEncoder)
        s3_object_tmp_file.write('{}\n'.format(item_json))

    s3_object_tmp_file.close()

    # upload s3
    s3_object = '{}/{}'.format(s3_prefix_name, s3_object_name)
    upload_to_s3(S3_BUCKET_NAME, s3_object_tmp_name, s3_object)

    logger.info('end')


if __name__ == "__main__":
    main(None, None)
