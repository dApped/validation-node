import logging
import os
from logging.config import dictConfig

import sentry_sdk
from sentry_sdk import configure_scope
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

import common


def init_logging():
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.WARN  # Send warn as events
    )
    sentry_sdk.init(
        dsn=os.getenv('SENTRY_DSN'),
        environment=os.getenv('FLASK_ENV'),
        integrations=[sentry_logging, FlaskIntegration()])

    with configure_scope() as scope:
        scope.user = {'node_id': common.node_id()}

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'f': {
                'format': '%(asctime)s [%(levelname)s] %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'f',
                'level': 'INFO',
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'f',
                'filename': 'logs/validation_node.log',
                'mode': 'a',
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'f',
                'filename': 'logs/gunicorn.error.log',
                'mode': 'a',
            },
            'access_file': {
                'class': 'logging.FileHandler',
                'formatter': 'f',
                'filename': 'logs/gunicorn.access.log',
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'loggers': {
            'gunicorn.error': {
                'level': 'INFO',
                'handlers': ['console', 'error_file'],
                'propagate': True
            },
            'gunicorn.access': {
                'level': 'INFO',
                'handlers': ['access_file'],
                'propagate': False
            },
        }
    }
    dictConfig(logging_config)
