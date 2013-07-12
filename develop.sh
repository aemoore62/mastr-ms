#!/bin/bash
#
# Script to control Mastrms in dev and test
#

# break on error
set -e 

TOPDIR=$(cd `dirname $0`; pwd)
ACTION=$1
shift

PORT='8000'

PROJECT_NAME='mastrms'
AWS_BUILD_INSTANCE='aws_rpmbuild_centos6'
AWS_STAGING_INSTANCE='aws_syd_mastrms_staging'
TARGET_DIR="/usr/local/src/${PROJECT_NAME}"
CLOSURE="/usr/local/closure/compiler.jar"
TESTING_MODULES="argparse dingus xvfbwrapper nose"
MODULES="MySQL-python==1.2.3 psycopg2==2.4.6 Werkzeug flake8 ${TESTING_MODULES}"
PIP_OPTS="-v -M --download-cache ~/.pip/cache"


function usage() {
    echo ""
    echo "Usage ./develop.sh (test|lint|jslint|dropdb|start|install|clean|purge|pipfreeze|pythonversion|ci_remote_build|ci_staging|ci_staging_tests|ci_rpm_publish|ci_remote_destroy)"
    echo ""
}


function settings() {
    export DJANGO_SETTINGS_MODULE="${PROJECT_NAME}.settings"
}

function activate_virtualenv() {
    source ${TOPDIR}/virt_${PROJECT_NAME}/bin/activate
}

# ssh setup, make sure our ccg commands can run in an automated environment
function ci_ssh_agent() {
    ssh-agent > /tmp/agent.env.sh
    source /tmp/agent.env.sh
    ssh-add ~/.ssh/ccg-syd-staging.pem
}

function build_number_head() {
    export TZ=Australia/Perth
    DATE=`date`
    TIP=`hg tip --template "{node}" 2>/dev/null || /bin/true`
    echo "# Generated by develop.sh"
    echo "build.timestamp=\"$DATE\""
    echo "build.tip=\"$TIP\""
}

# build RPMs on a remote host from ci environment
function ci_remote_build() {
    time ccg ${AWS_BUILD_INSTANCE} boot
    time ccg ${AWS_BUILD_INSTANCE} puppet
    time ccg ${AWS_BUILD_INSTANCE} shutdown:50

    cd ${TOPDIR}

    if [ -z "$BAMBOO_BUILDKEY" ]; then
        # We aren't running under Bamboo, create new build-number.txt.
        build_number_head > build-number.txt
    else
        # Bamboo has already put some useful information in
        # build-number.txt, so append to it.
        build_number_head >> build-number.txt
    fi

    EXCLUDES="('bootstrap'\, '.hg*'\, '.git'\, 'virt*'\, '*.log'\, '*.rpm'\, 'mastrms/build'\, 'mastrms/dist'\, '*.egg-info')"
    SSH_OPTS="-o StrictHostKeyChecking\=no"
    RSYNC_OPTS="-l"
    time ccg ${AWS_BUILD_INSTANCE} rsync_project:local_dir=./,remote_dir=${TARGET_DIR}/,ssh_opts="${SSH_OPTS}",extra_opts="${RSYNC_OPTS}",exclude="${EXCLUDES}",delete=True
    time ccg ${AWS_BUILD_INSTANCE} build_rpm:centos/${PROJECT_NAME}.spec,src=${TARGET_DIR}

    mkdir -p build
    ccg ${AWS_BUILD_INSTANCE} getfile:rpmbuild/RPMS/x86_64/${PROJECT_NAME}*.rpm,build/
}


# publish rpms 
function ci_rpm_publish() {
    time ccg ${AWS_BUILD_INSTANCE} publish_rpm:build/${PROJECT_NAME}*.rpm,release=6
}


# destroy our ci build server
function ci_remote_destroy() {
    ccg ${AWS_BUILD_INSTANCE} destroy
}


# puppet up staging which will install the latest rpm
function ci_staging() {
    ccg ${AWS_STAGING_INSTANCE} boot
    ccg ${AWS_STAGING_INSTANCE} puppet
    ccg ${AWS_STAGING_INSTANCE} shutdown:50
}


# run tests on staging
function ci_staging_tests() {
    # /tmp is used for test results because the apache user has
    # permission to write there.
    REMOTE_TEST_DIR=/tmp
    REMOTE_TEST_RESULTS=${REMOTE_TEST_DIR}/tests.xml

    # Grant permission to create a test database. Assume that database
    # user is same as project name for now.
    DATABASE_USER=${PROJECT_NAME}
    ccg ${AWS_STAGING_INSTANCE} dsudo:"su postgres -c \"psql -c 'ALTER ROLE ${DATABASE_USER} CREATEDB;'\""

    # fixme: this config should be put in nose.cfg or settings.py or similar
    EXCLUDES="--exclude\=yaphc --exclude\=esky --exclude\=httplib2"
    TEST_LIST="mastrms.mastrms.registration.tests mastrms.mastrms.mdatasync_server.tests mastrms.mdatasync_client.client.test.tests"

    # Start virtual X server here to work around a problem starting it
    # from xvfbwrapper.
    ccg ${AWS_STAGING_INSTANCE} drunbg:"Xvfb \:0"

    # Run tests, collect results
    ccg ${AWS_STAGING_INSTANCE} dsudo:"cd ${REMOTE_TEST_DIR} && env DISPLAY\=\:0 dbus-launch ${PROJECT_NAME} test --noinput --with-xunit --xunit-file\=${REMOTE_TEST_RESULTS} ${TEST_LIST} ${EXCLUDES} || true"
    ccg ${AWS_STAGING_INSTANCE} getfile:${REMOTE_TEST_RESULTS},./
}


# lint using flake8
function lint() {
    activate_virtualenv
    cd ${TOPDIR}
    flake8 ${PROJECT_NAME} --ignore=E501 --count
}


# lint js, assumes closure compiler
function jslint() {
    JSFILES="${TOPDIR}/mastrms/mastrms/app/static/js/*.js ${TOPDIR}/mastrms/mastrms/app/static/js/repo/*.js"
    for JS in $JSFILES
    do
        java -jar ${CLOSURE} --js $JS --js_output_file output.js --warning_level DEFAULT --summary_detail_level 3
    done
}


# run the tests using django-admin.py
function djangotests() {
    activate_virtualenv
    django-admin.py test --noinput --with-xunit --xunit-file=tests.xml \
        --exclude="esky" --exclude="yaphc" --exclude="httplib2" \
        ${PROJECT_NAME}
}


function nosetests() {
    activate_virtualenv
    nosetests --with-xunit --xunit-file=tests.xml -v -w tests
}


function nose_collect() {
    activate_virtualenv
    nosetests -v -w tests --collect-only
}


function dropdb() {
    echo "todo"
}


function installapp() {
    # check requirements
    which virtualenv >/dev/null

    echo "Install ${PROJECT_NAME}"
    virtualenv --system-site-packages ${TOPDIR}/virt_${PROJECT_NAME}
    pushd ${TOPDIR}/${PROJECT_NAME}
    ../virt_${PROJECT_NAME}/bin/pip install ${PIP_OPTS} -e .
    popd
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/pip install ${PIP_OPTS} ${MODULES}
}


# django syncdb, migrate and collect static
function syncmigrate() {
    echo "syncdb"
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/django-admin.py syncdb --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> syncdb-develop.log
    echo "migrate"
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/django-admin.py migrate --settings=${DJANGO_SETTINGS_MODULE} 1> migrate-develop.log
    echo "collectstatic"
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/django-admin.py collectstatic --noinput --settings=${DJANGO_SETTINGS_MODULE} 1> collectstatic-develop.log
}


# start runserver
function startserver() {
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/django-admin.py runserver_plus ${port}
}


function pythonversion() {
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/python -V
}


function pipfreeze() {
    echo "${PROJECT_NAME} pip freeze"
    ${TOPDIR}/virt_${PROJECT_NAME}/bin/pip freeze
    echo '' 
}


function clean() {
    find ${TOPDIR}/${PROJECT_NAME} -name "*.pyc" -exec rm -rf {} \;
}


function purge() {
    rm -rf ${TOPDIR}/virt_${PROJECT_NAME}
    rm *.log
}


function runtest() {
    #nosetests
    djangotests
}



case ${ACTION} in
pythonversion)
    pythonversion
    ;;
pipfreeze)
    pipfreeze
    ;;
test)
    settings
    runtest
    ;;
lint)
    lint
    ;;
jslint)
    jslint
    ;;
syncmigrate)
    settings
    syncmigrate
    ;;
start)
    settings
    startserver
    ;;
install)
    settings
    installapp
    ;;
ci_remote_build)
    ci_ssh_agent
    ci_remote_build
    ;;
ci_remote_destroy)
    ci_ssh_agent
    ci_remote_destroy
    ;;
ci_rpm_publish)
    ci_ssh_agent
    ci_rpm_publish
    ;;
ci_staging)
    ci_ssh_agent
    ci_staging
    ;;
ci_staging_tests)
    ci_ssh_agent
    ci_staging_tests
    ;;
dropdb)
    dropdb
    ;;
clean)
    settings
    clean
    ;;
purge)
    settings
    clean
    purge
    ;;
*)
    usage
esac
