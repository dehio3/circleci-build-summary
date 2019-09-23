#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
from pathlib import Path


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

CIRCLECI_TOKEN = os.getenv('CIRCLECI_TOKEN')
CIRCLECI_URL = os.getenv('CIRCLECI_URL')
CIRCLECI_GET_BUILD_LIMIT = os.getenv('CIRCLECI_GET_BUILD_LIMIT')
GITHUB_ORGANIZATION_NAME = os.getenv('GITHUB_ORGANIZATION_NAME')
DYNAMODB_ENDPOINT = os.getenv('DYNAMODB_ENDPOINT')
DYNANODB_TABLE_NAME = os.getenv('DYNANODB_TABLE_NAME')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
