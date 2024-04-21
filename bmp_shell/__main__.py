#!/usr/bin/env python
# SPDX-License-Identifier: BSD-3-Clause
import sys
from pathlib import Path

try:
	from bmp_shell.repl import main
except ImportError:
	bmp_shell_path = Path(sys.argv[0]).resolve()

	if (bmp_shell_path.parent / 'bmp_shell').is_dir():
		sys.path.insert(0, str(bmp_shell_path.parent))

	from bmp_shell.repl import main

sys.exit(main())
