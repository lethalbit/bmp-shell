#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup, find_packages
from pathlib    import Path

REPO_ROOT   = Path(__file__).parent
README_FILE = (REPO_ROOT / 'README.md')

def vcs_ver():
	def scheme(version):
		if version.tag and not version.distance:
			return version.format_with('')
		else:
			return version.format_choice('+{node}', '+{node}.dirty')
	return {
		'relative_to': __file__,
		'version_scheme': 'guess-next-dev',
		'local_scheme': scheme
	}


setup(
	name = 'Squishy',
	use_scm_version  = vcs_ver(),
	author           = 'Aki \'lethalbit\' Van Ness',
	author_email     = 'nya@catgirl.link',
	description      = 'JTAG Shell for the 1b2 blackmagic probe',
	license          = 'BSD-3-Clause',
	python_requires  = '~=3.9',
	zip_safe         = True,
	url              = 'https://github.com/lethalbit/bmp-shell',

	long_description = README_FILE.read_text(),
	long_description_content_type = 'text/markdown',

	setup_requires   = [
		'wheel',
		'setuptools',
		'setuptools_scm'
	],

	install_requires  = [
		'Jinja2',
		'construct>=2.10.67',
		'arrow',
		'rich',

	],

	packages          = find_packages(
		where   = '.',
		exclude = (
			'tests', 'tests.*', 'examples', 'examples.*'
		)
	),
	package_data      = {

	},

	extras_require    = {
		'dev': [
			'nox',
			'setuptools_scm'
		]
	},

	entry_points       = {
		'console_scripts': [
			'bmp-shell = bmp_shell.repl:main',
		]
	},

	classifiers       = [

	],

	project_urls      = {
		'Documentation': 'https://github.com/lethalbit/bmp-shell',
		'Source Code'  : 'https://github.com/lethalbit/bmp-shell',
		'Bug Tracker'  : 'https://github.com/lethalbit/bmp-shell/issues',
	}
)
