#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging.config
import settings
import sys
import boto3
import requests

# logging
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('__name__')

# env
CIRCLECI_TOKEN = settings.CIRCLECI_TOKEN
CIRCLECI_URL = settings.CIRCLECI_URL
CIRCLECI_GET_BUILD_LIMIT = settings.CIRCLECI_GET_BUILD_LIMIT
DYNAMODB_ENDPOINT = settings.DYNAMODB_ENDPOINT
DYNANODB_TABLE_NAME = settings.DYNANODB_TABLE_NAME

dynamodb = boto3.resource(
    'dynamodb',
    # endpoint_url=DYNAMODB_ENDPOINT
    region_name=DYNAMODB_ENDPOINT
)


def circleci_build_data_get(url, token, limit):
    """Return the builds data
    https://circleci.com/docs/api/v1-reference/#recent-builds

    Args:
        url (str)   : CircleCI api url
        token (srt) : CirlceCI token
        limit (int) : CircleCI get build data limit

    return:
        response_json（json）: build data
    """

    params = (
        ('limit', limit),
        ('offset', 0),
    )

    if url == 'https://circleci.com':
        api_url = '{}/api/v1.1/recent-builds'.format(url)
    else:
        api_url = '{}/api/v1/admin/recent-builds'.format(url)

    response = requests.get(api_url, params=params, auth=(token, ''))

    try:
        response.raise_for_status()
    except Exception as err:
        logger.error(err)
        sys.exit(1)

    # text to json
    response_json = json.loads(response.text)

    return response_json


def put_dynamodb(table, item):
    """ Put DynamoDB

    Args:
        table(str)  DynamoDB Table Name
        item(dict)  CircleCI Build data
    """

    table = dynamodb.Table(table)

    try:
        table.put_item(Item=item)
    except Exception as err:
        logger.error(err)
        sys.exit(1)


def change_empty_value_to_none(build):
    """ Change empty string to "None"

    Args:
        build(dict) Change Data

    Return:
        build(dict)

    Note:
        https://github.com/boto/boto3/issues/1035
    """
    for k, v in build.items():
        if isinstance(v, dict):
            change_empty_value_to_none(v)
        elif isinstance(v, list):
            for i in v:
                if type(i) is not str:
                    change_empty_value_to_none(i)
        elif v == "":
            build[k] = None

    return build


def main(event, lambda_context):
    logger.info('start')

    logger.info('build date get start')
    builds_data = circleci_build_data_get(
        CIRCLECI_URL, CIRCLECI_TOKEN, CIRCLECI_GET_BUILD_LIMIT)
    logger.info('build date get end')

    logger.info('build data put dynamodb start')
    for build in builds_data:
        # get queued time
        # queued_at: 2019-01-10T08:36:22.224Z (UTC)
        queued_at = build.get('queued_at')

        # exclude not run build
        if not queued_at:
            continue

        # put DynamoDB
        logger.debug(build)
        convert_buid = change_empty_value_to_none(build)
        put_dynamodb(DYNANODB_TABLE_NAME, convert_buid)

    logger.info('build data put dynamodb end')

    logger.info('end')


if __name__ == "__main__":
    main(None, None)
