#!/usr/bin/env python3
import os
from setuptools import setup

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def get_version():
    """ Find the version of the package"""
    version = None
    version_file = os.path.join(BASEDIR, 'ovos_tts_plugin_elevenlabs', 'version.py')
    major, minor, build, alpha = (None, None, None, None)
    with open(version_file) as f:
        for line in f:
            if 'VERSION_MAJOR' in line:
                major = line.split('=')[1].strip()
            elif 'VERSION_MINOR' in line:
                minor = line.split('=')[1].strip()
            elif 'VERSION_BUILD' in line:
                build = line.split('=')[1].strip()
            elif 'VERSION_ALPHA' in line:
                alpha = line.split('=')[1].strip()

            if ((major and minor and build and alpha) or
                    '# END_VERSION_BLOCK' in line):
                break
    version = f"{major}.{minor}.{build}"
    if alpha and int(alpha) > 0:
        version += f"a{alpha}"
    return version


def required(requirements_file):
    """ Read requirements file and remove comments and empty lines. """
    with open(os.path.join(BASEDIR, requirements_file), 'r') as f:
        requirements = f.read().splitlines()
        if 'MYCROFT_LOOSE_REQUIREMENTS' in os.environ:
            print('USING LOOSE REQUIREMENTS!')
            requirements = [r.replace('==', '>=').replace('~=', '>=') for r in requirements]
        return [pkg for pkg in requirements
                if pkg.strip() and not pkg.startswith("#")]


PLUGIN_ENTRY_POINT = 'ovos-tts-plugin-elevenlabs = ovos_tts_plugin_elevenlabs:ElevenLabsTTSPlugin'
CONFIG_ENTRY_POINT = 'ovos-tts-plugin-elevenlabs.config = ovos_tts_plugin_elevenlabs:ElevenLabsTTSConfig'

setup(
    name='ovos-tts-plugin-elevenlabs',
    version=get_version(),
    description='ElevenLabs TTS plugin for OVOS',
    url='https://github.com/jaredcobb/ovos-tts-plugin-elevenlabs',
    author='Jared Cobb',
    license='Apache-2.0',
    packages=['ovos_tts_plugin_elevenlabs'],
    install_requires=required("requirements.txt"),
    zip_safe=True,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Linguistic',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='mycroft plugin tts OVOS OpenVoiceOS',
    entry_points={
        'mycroft.plugin.tts': PLUGIN_ENTRY_POINT,
        'mycroft.plugin.tts.config': CONFIG_ENTRY_POINT
    }
)
