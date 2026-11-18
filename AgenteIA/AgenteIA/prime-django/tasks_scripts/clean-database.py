#!/usr/bin/env python
"""
Copyright (c) 2019 - present AppSeed.us
"""

import os
import sys
import logging
from venv import logger

logger = logging.getLogger(__name__)


def main(argv):
    try:
        print(" EXEC -> " + os.path.basename(__file__))

        # Unix ErrCode
        exit(0)

    except Exception as e:
        logger.exception("Err: " + str(e))
        exit(1)


if __name__ == "__main__":
    main(sys.argv)
