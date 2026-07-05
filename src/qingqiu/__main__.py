"""支持 `python -m qingqiu` 调用"""

import sys

from qingqiu.cli import main

if __name__ == "__main__":
    sys.exit(main())