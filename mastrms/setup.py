import setuptools
import os
from setuptools import setup
from mastrms import VERSION

data_files = {}
start_dir = os.getcwd()
for package in ('app', 'admin', 'dashboard', 'login', 'mdatasync_server', 'quote', 'registration', 'repository', 'users'):
    data_files['mastrms.' + package] = []
    os.chdir(os.path.join('mastrms', package))
    for data_dir in ('templates', 'static', 'migrations', 'fixtures', 'views', 'utils'):
        data_files['mastrms.' + package].extend(
            [os.path.join(subdir,f) for (subdir, dirs, files) in os.walk(data_dir) for f in files])
    os.chdir(start_dir)

setup(name='django-mastrms',
    version=VERSION,
    description='Mastr MS',
    long_description='Django Mastr MS web application',
    author='Centre for Comparative Genomics',
    author_email='web@ccg.murdoch.edu.au',
    packages=[
        'mastrms',
        'mastrms.app',
        'mastrms.admin',
        'mastrms.dashboard',
        'mastrms.login',
        'mastrms.mdatasync_client',
        'mastrms.mdatasync_client.client',
        'mastrms.mdatasync_client.client.plogging',
        'mastrms.mdatasync_client.client.yaphc',
        'mastrms.mdatasync_client.client.httplib2',
        'mastrms.mdatasync_client.client.tendo',
        'mastrms.mdatasync_client.client.test',
        'mastrms.mdatasync_server',
        'mastrms.mdatasync_server.management',
        'mastrms.mdatasync_server.management.commands',
        'mastrms.quote',
        'mastrms.registration',
        'mastrms.repository',
        'mastrms.users',
        'mastrms.testutils',
    ],
    package_data=data_files,
    zip_safe=False,
    install_requires=[
        'Django==1.5.5',
        'South==0.8.2',
        'ccg-extras==0.1.6',
        'django-picklefield==0.1.9',
        'django-templatetag-sugar==0.1',
        'pyparsing==1.5.6',
        'wsgiref==0.1.2',
        'python-memcached==1.48',
        'django-userlog==0.1',
        'django-extensions>=1.2.5',
        'django-nose',
        'dingus',
    ],
    dependency_links = [
        "http://repo.ccgapps.com.au"
    ],
)
