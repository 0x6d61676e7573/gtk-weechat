VERSION = '1.1.8'

# bootstrap if we need to
try:
    import setuptools  # noqa
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()

from setuptools import setup, find_packages

classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        ]


setup(author='x6d61676e7573 and others',
      classifiers=classifiers,
      description='GTK Weechat-Relay client',
      name='gtk-weechat',
      url='https://github.com/0x6d61676e7573',
      version=VERSION,
      packages=find_packages(),
      package_data={'gtk_weechat': ['*.css']},
      entry_points={'console_scripts': ['gtk-weechat=gtk_weechat.gtk_weechat:main']},
      install_requires=['pycairo', 'PyGObject'],
      extras_require={'dev': []},
      setup_requires=["wheel"],
      zip_safe=False
      )
