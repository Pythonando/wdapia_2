import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger


def get_logging_config(log_dir: str, log_level: str = 'DEBUG') -> dict:
    """Return Django LOGGING configuration with JSON formatter."""

    os.makedirs(log_dir, exist_ok=True)

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': jsonlogger.JsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s',
                'timestamp': True,
            },
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(name)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'verbose',
            },
            'file': {
                'level': log_level,
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'django.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
            },
            'error_file': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(log_dir, 'error.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'formatter': 'json',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'file', 'error_file'],
                'level': 'WARNING',
                'propagate': False,
            },
            'django.server': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
            },
            'django.db.backends': {
                'handlers': ['console'],
                'level': 'WARNING',
                'propagate': False,
            },
            'core': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            },
            'produtos': {
                'handlers': ['console', 'file'],
                'level': log_level,
                'propagate': False,
            },
        },
    }
