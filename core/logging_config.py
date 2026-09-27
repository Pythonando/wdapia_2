import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger


class ElasticAPMFormatter(jsonlogger.JsonFormatter):
    """JSON formatter that injects Elastic APM trace context."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        try:
            from elasticapm.trace import get_transaction
            transaction = get_transaction()
            if transaction:
                if hasattr(transaction, 'id'):
                    log_record['transaction.id'] = transaction.id
                if hasattr(transaction, 'trace_parent'):
                    log_record['trace.id'] = transaction.trace_id
        except Exception:
            pass


def get_logging_config(log_dir: str, log_level: str = 'DEBUG') -> dict:
    """Return Django LOGGING configuration with JSON formatter."""

    os.makedirs(log_dir, exist_ok=True)

    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': ElasticAPMFormatter,
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
            'elasticapm': {
                'level': 'ERROR',
                'class': 'elasticapm.contrib.django.handlers.LoggingHandler',
            },
        },
        'loggers': {
            'django': {
                'handlers': ['console', 'file', 'elasticapm'],
                'level': log_level,
                'propagate': False,
            },
            'django.request': {
                'handlers': ['console', 'file', 'error_file', 'elasticapm'],
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
                'handlers': ['console', 'file', 'elasticapm'],
                'level': log_level,
                'propagate': False,
            },
            'produtos': {
                'handlers': ['console', 'file', 'elasticapm'],
                'level': log_level,
                'propagate': False,
            },
            'elasticapm': {
                'handlers': ['console'],
                'level': 'ERROR',
                'propagate': False,
            },
        },
    }
