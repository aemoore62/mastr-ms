import os
import os.path
import posixpath, urllib, mimetypes
import pickle
from datetime import datetime, timedelta
import copy
import json
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import EmailMessage
from ccg_django_utils import webhelpers
from mastrms.mdatasync_server.models import *
from mastrms.repository.models import *
from mastrms.mdatasync_server.rules import *
from mastrms.app.utils.file_utils import ensure_repo_filestore_dir_with_owner, set_repo_file_ownerships

import logging
logger = logging.getLogger("mastrms.mdatasync_server")


class FixedEmailMessage(EmailMessage):
    def __init__(self, subject='', body='', from_email=None, to=None, cc=None,
                 bcc=None, connection=None, attachments=None, headers=None):
        """
        Initialize a single email message (which can be sent to multiple
        recipients).

        All strings used to create the message can be Unicode strings (or UTF-8
        bytestrings). The SafeMIMEText class will handle any necessary encoding
        conversions.
        """
        to_cc_bcc_types = (type(None), list, tuple)
        # test for typical error: people put strings in to, cc and bcc fields
        # see documentation at http://www.djangoproject.com/documentation/email/
        assert isinstance(to, to_cc_bcc_types)
        assert isinstance(cc, to_cc_bcc_types)
        assert isinstance(bcc, to_cc_bcc_types)
        super(FixedEmailMessage, self).__init__(subject, body, from_email, to,
                                           bcc, connection, attachments, headers)
        if cc:
            self.cc = list(cc)
        else:
            self.cc = []

    def recipients(self):
        """
        Returns a list of all recipients of the email (includes direct
        addressees as well as Bcc entries).
        """
        return self.to + self.cc + self.bcc

    def message(self):
        msg = super(FixedEmailMessage, self).message()
        del msg['Bcc'] # if you still use old django versions
        if self.cc:
            msg['Cc'] = ', '.join(self.cc)
        return msg


def checkClientVersion(versionstr):
    logger.debug("Checking client version: %s" % versionstr)
    components = versionstr.split('.')
    if len(components) < 2:
        return False

    major = components[0]
    minor = components[1]

    #accept anything better than 1.4
    if major < 1:
        if minor < 4:
            return False
    return True

def jsonResponse(data):
    jdata = json.dumps(data)
    return HttpResponse(jdata)



@csrf_exempt
def request_sync(request, organisation=None, sitename=None, station=None):
    '''This is the initial request the client makes of the server.
       The client will have sent (via URL or post fields) its
       organisation, sitename, and station, what verstion it is, and whether
       it wants to re-sync already completed files.

       The server should, after verifying that the node exists and that the
       version is acceptable, then go through the experiments which the node
       is involved in, and send back a list of files it wants.

       The return format is:
       {
            files: {},
            runsamples: {},
            details{},
            success: T/F (set to False if no node or version check fails)
            message: "" (a message to explain problems if success is false)

       }
    '''
    node = get_node_from_request(request, organisation, sitename, station)
    resp = {"success": False,
            "message": "",
            "files": {},
            "details":{},
            "runsamples":{}}
    syncold = request.GET.get("sync_completed", False)
    logger.debug('syncold is: %s' % syncold)
    if node is not None:
        ncerror, nodeclient_details = get_nodeclient_details(organisation, sitename, station)
        resp["details"] = nodeclient_details
        version = request.POST.get("version", "")
        if not checkClientVersion(version):
            resp["message"] = "Client version \"%s\" is not supported. Please update." % version
        else:
            resp["success"] = True
            #now get the runs for that nodeclient
            expectedFiles = getExpectedFilesForNode(node, include_completed=syncold)
            expectedincomplete = expectedFiles['incomplete']
            expectedcomplete = expectedFiles['complete']

            logger.debug(expectedFiles)

            for runid in expectedincomplete.keys():
                resp["files"].update(expectedincomplete[runid])

            if syncold:
                for runid in expectedcomplete.keys():
                    resp["files"].update(expectedcomplete[runid])
    else:
        resp["success"] = False
        resp["message"] = "Could not find node %s-%s-%s" % (organisation, sitename, station)

    return HttpResponse(json.dumps(resp))

def get_node_from_request(request, organisation=None, sitename=None, station=None):
    retval = None

    if organisation is None:
        organisation = request.REQUEST('organisation', None)
    if sitename is None:
        sitename = request.REQUEST('sitename', None)
    if station is None:
        station = request.REQUEST('station', None)

    logger.debug("Searching for node org=%s, sitename=%s, station=%s" % (organisation, sitename, station))
    try:
        nodeclient = NodeClient.objects.get(organisation_name = organisation, site_name=sitename, station_name = station)
        retval = nodeclient
    except:
        retval = None
        logger.warning("No nodeclient existed with organisation=%s, sitename=%s, station=%s" % (organisation, sitename, station))

    return retval

def get_node_clients(request, *args):
    ncs = NodeClient.objects.all()
    result = {}
    for n in ncs:
        if not result.has_key(n.organisation_name):
            result[n.organisation_name] = {}
        o = result[n.organisation_name]
        if not o.has_key(n.site_name):
            o[n.site_name] = []
        o[n.site_name].append(n.station_name)
    return jsonResponse(result)

def getExpectedFilesForNode(nodeclient, include_completed = False):
    """
    Based on the experiments that a given nodeclient is involved in,
    return the files which the server expects.

    If include_completed is false, this will be every file which
    the server has not marked as complete.

    If include_complete is true, this will be every file from both
    incomplete and complete experiments/runs which the server has not
    marked as complete.

    Returns a dictionary with 'complete' and 'incomplete' keys, whose values are
    dicts keyed on runid.
    """
    incomplete = {}
    complete = {}

    #now get the runs for that nodeclient
    runs = Run.objects.filter(machine = nodeclient)
    for run in runs:
        logger.debug('Finding runsamples for run')
        if not run.is_complete() or include_completed:
            runsamples = run.runsample_set.exclude(filename="")
            runsamples = runsamples.exclude(filename__isnull=True) # fixme: fix the model

            #Build a filesdict of all the files for these runsamples
            for rs in runsamples:
                logger.debug('Getting files for runsamples');

                target_dict = complete if rs.complete else incomplete

                abspath, relpath = rs.filepaths()
                runfiles = target_dict.setdefault(run.id, {})

                if runfiles.has_key(rs.filename):
                    logger.warning( 'Duplicate filename detected for %s' % (rs.filename.encode('utf-8')))

                runfiles[rs.filename] = [run.id, rs.id, relpath, os.path.exists(os.path.join(abspath, rs.filename))]

    return {'complete': complete, 'incomplete': incomplete}


def get_nodeclient_details(organisation_name, site_name, station_name):
    nodeclient_details = {}
    error = None
    try:
        nodeclient = NodeClient.objects.get(organisation_name = organisation_name, site_name=site_name, station_name = station_name)

        nchost = nodeclient.hostname
        if nchost is not None and len(nchost) > 0:
            nodeclient_details['host'] = str(nchost)
        ncflags = nodeclient.flags
        if ncflags is not None and len(ncflags) > 0:
            nodeclient_details['flags'] = str(ncflags)
        ncuname = nodeclient.username
        if ncuname is not None and len(ncuname) > 0:
            nodeclient_details['username'] = str(ncuname)

        #The rootdir tells the client where on the host filesystem to dump the files
        nodeclient_details['rootdir'] = settings.REPO_FILES_ROOT

        try:
            rulesset = NodeRules.objects.filter(parent_node = nodeclient)
            nodeclient_details['rules'] = [x.__unicode__() for x in rulesset]
        except Exception, e:
            error = '%s, %s' % (error, 'Unable to resolve ruleset: %s' % (str(e)))
    except Exception, e:
        #status = 1
        logger.debug("exception encountered: %s" % (e))
        error = "%s, %s" % (error, 'Unable to resolve end machine to stored NodeClient: %s' % str(e) )

    return error, nodeclient_details


def check_run_sample_file_exists(runsampleid):
    ''' Checks that the file for a given runsampleid is present in the filesystem'''
    fileexists = False
    try:
        rs = RunSample.objects.get(id=runsampleid)
        abssamplepath, relsamplepath = rs.filepaths()
        complete_filename = os.path.join(abssamplepath, rs.filename)
        fileexists = os.path.exists(complete_filename)
        logger.debug( 'Checking file %s:%s' % (complete_filename.encode('utf-8'), fileexists) )
    except Exception, e:
        logger.debug('Could not check runsample file for runsampleid: %s: %s' % (str(runsampleid), e))

    return fileexists

@csrf_exempt
def check_run_sample_files(request):
    ret = {}
    ret['success'] = False
    ret['description'] = "No Error"
    runsamplefilesjson = request.POST.get('runsamplefiles', None)
    if runsamplefilesjson is not None:
        runsamplefilesdict = json.loads(runsamplefilesjson)
        # so now we have a dict keyed on run, of sample id's whose file should have been received.
        logger.debug('Checking run samples against: %s' % ( runsamplefilesdict) )
        # We iterate through each run, get the samples referred to, and ensure their file exists on disk.
        ret['description'] = ""
        totalruns = 0
        totalsamples = 0
        totalfound = 0

        ret['success'] = True
        ret['description'] = 'Success'
        ret['error'] = 'None'
        ret['synced_samples'] = {}
        for runid in runsamplefilesdict.keys():
            totalruns += 1
            ret['synced_samples'][runid] = []
            logger.debug('Checking files from run %s' % str(runid) )
            runsamples = runsamplefilesdict[runid]
            for runsample in runsamples:
                totalsamples +=1
                runsample = int(runsample)
                try:
                    rs = RunSample.objects.get(id = runsample)
                    rs.complete = check_run_sample_file_exists(runsample)
                    if rs.complete:
                        totalfound += 1
                        ret['synced_samples'][runid].append(rs.id)
                    rs.save()
                except Exception, e:
                    logger.debug('Error: %s' % (e) )
                    ret['success'] = False
                    ret['error'] = "%s" % (str(e))
        ret['description'] = "%s - %d/%d samples marked complete, from %d run(s)" % (ret['description'], totalfound, totalsamples, totalruns)
    else:
        ret['description'] = "No files given"

    return jsonResponse(ret)

@csrf_exempt
def log_upload(request, *args):
    logger.debug('LOGUPLOAD')
    status = 'ok'
    fname_prefix = 'UNKNOWN_'
    if request.POST.has_key('nodename'):
        fname_prefix = request.POST['nodename'] + '_'

    if request.FILES.has_key('uploaded'):
        f = request.FILES['uploaded']
        logger.debug( 'Uploaded file name: %s' % ( f._get_name() ) )
        written_logfile_name = str(os.path.join('synclogs', "%s%s" % (fname_prefix,f._get_name()) ) )
        write_success = _handle_uploaded_file(f, written_logfile_name )#dont allow them to replace arbitrary files
        try:
            if write_success:
                body ="An MS Datasync logfile has been uploaded: %s\r\n" % (written_logfile_name)
            else:
                body = "MS Datasync logfile upload failed: %s\r\n" % (written_logfile_name)
                status = 'Log upload failed'
            e = FixedEmailMessage(subject="MS Datasync Log Upload (%s)" % (fname_prefix.strip('_')), body=body, from_email = settings.RETURN_EMAIL, to = [settings.LOGS_TO_EMAIL])
            e.send()
        except Exception, e:
            logger.warning( 'Unable to send "Log Sent" email: %s' % (str(e)) )

    else:
        logger.warning( 'logupload: No file in the post' )
        status = 'No log posted'

    return jsonResponse(status)

@csrf_exempt
def key_upload(request, *args):
    fname_prefix = 'UNKNOWN_'
    status = 'ok'
    if request.POST.has_key('nodename'):
        fname_prefix = request.POST['nodename'] + '_'

    if request.FILES.has_key('uploaded'):
        f = request.FILES['uploaded']
        logger.debug( 'Uploaded file name: %s' % ( f._get_name() ) )
        written_logfile_name = str(os.path.join('publickeys', "%s%s" % (fname_prefix,'id_rsa.pub')) )
        write_success = _handle_uploaded_file(f, written_logfile_name )#dont allow them to replace arbitrary files

        try:
            if write_success:
                body ="An MS Datasync keyfile has been uploaded: %s\r\n" % (written_logfile_name)
            else:
                body = "MS Datasync keyfile upload failed: %s\r\n" % (written_logfile_name)
                status= 'key upload failed'
            e = FixedEmailMessage(subject="MS Datasync Public Key upload (%s)" % (fname_prefix), body=body, from_email = settings.RETURN_EMAIL, to = [settings.KEYS_TO_EMAIL])
            e.send()
        except Exception, e:
            logger.warning( 'Unable to send "Key Sent" email: %s' % (str(e)) )

    else:
        logger.warning('Keyupload: No file in the post')
        status = 'No key posted'

    return jsonResponse(status)



def _handle_uploaded_file(f, name):
    '''Handles a file upload to the projects REPO_FILES_ROOT
       Expects a django InMemoryUpload object, and a filename'''
    logger.debug( '*** _handle_uploaded_file: enter ***')
    retval = False
    try:
        import os
        reldir = os.path.dirname(name)
        dest_fname = str(os.path.join(settings.REPO_FILES_ROOT, name))
        ensure_repo_filestore_dir_with_owner(reldir)

        destination = open(dest_fname, 'wb+')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
        retval = set_repo_file_ownerships(dest_fname)
    except Exception, e:
        retval = False
        logger.exception('Exception in file upload')
    logger.debug( '*** _handle_uploaded_file: exit ***')
    return retval

@login_required
def utils(request):
    success = True
    message = ''
    #First, if they posted, they want to change the log level.
    if request.method == 'POST':
        #set the log level:
        ll = request.POST.get('loglevel', None)
        success = True
        if ll:
            success, message = set_log_level(int(ll))
        else:
            success = False
            message = 'No valid log level posted.'

    #now we proceed as normal.

    nodeclients = NodeClient.objects.all()
    #Screenshots and logs are in the same dir.
    clientlogdir = os.path.join(settings.REPO_FILES_ROOT , 'synclogs')
    fileslist = []
    if os.path.exists(clientlogdir):
        fileslist = os.listdir(clientlogdir )
    clientlogslist = []
    shotslist = []
    for fname in fileslist:
        if fname.endswith('.png'):
            shotslist.append(fname)
        else:
            clientlogslist.append(fname)

    serverloglist = os.listdir(settings.LOG_DIRECTORY)
    serverloglist.sort()
    clientlogslist.sort()
    shotslist.sort()
    currentLogLevel = logger.getEffectiveLevel()
    levelnames = ['Debug', 'Info', 'Warning', 'Critical', 'Fatal']
    levelvalues = [logging.DEBUG, logging.INFO, logging.WARNING, logging.CRITICAL, logging.FATAL]
    return render_to_response("utils.mako", {'wh':webhelpers, 'serverloglist':serverloglist, 'clientlogslist':clientlogslist, 'shotslist':shotslist, 'currentLogLevel':currentLogLevel, 'levelnames':levelnames, 'levelvalues':levelvalues , 'success':success, 'message':message, 'nodeclients': nodeclients})

@login_required
def tail_log(request, filename=None, linesback=10, since=0):
    since = int(since)
    linesback = int(linesback)
    avgcharsperline=75
    pos = 0
    if filename is None:
        filename = 'mastrms.mdatasync_server.log'

    logfilename = os.path.join(settings.LOG_DIRECTORY, filename)
    file = open(logfilename,'r')

    while 1:
        if (since):
            try: file.seek(since,os.SEEK_SET) #seek from start of file.
            except IOError: file.seek(0)

        else: #else seek from the end
            try: file.seek(-1 * avgcharsperline * linesback,2)
            except IOError: file.seek(0)

        if file.tell() == 0: atstart=1
        else: atstart=0

        lines=file.read().split("\n")
        pos = file.tell()

        #break if we were in 'since' mode, or we had enough lines, or we can't go back further
        if since or (len(lines) > (linesback+1)) or atstart: break

        #Otherwise, we are wanting to get more lines.
        #The lines are bigger than we thought
        avgcharsperline=int(avgcharsperline * 1.3) #Inc avg for retry
    file.close()

    out=""
    if not since:
        if len(lines) > linesback:
            start=len(lines)-linesback -1
        else:
            start=0

        for l in lines[start:len(lines)-1]:
            out=out + l + "\n"
    else:
        for l in lines:
            out += l + "\n"

    return HttpResponse(json.dumps({'data' : out, 'position':pos}) )

@login_required
def serve_file(request, path):
    root = settings.PERSISTENT_FILESTORE
    path = posixpath.normpath(urllib.unquote(path))
    path = path.lstrip('/')
    fullpath = os.path.join(root, path)
    if not os.path.isfile(fullpath):
        raise Http404, '"%s" does not exist' % fullpath
    contents = open(fullpath, 'rb').read()
    mimetype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
    response = HttpResponse(contents, mimetype=mimetype)
    response["Content-Length"] = len(contents)
    return response

def set_log_level(newlevel):
    success = True
    if newlevel in [logging.INFO, logging.DEBUG, logging.WARNING, logging.FATAL, logging.CRITICAL]:
        logger.setLevel(newlevel)
        msg = 'Logging level set to %s' % (str(newlevel))
    else:
        success = False
        msg = 'Unable to set logging level to %s, no such level exists' % (str(newlevel))
    #logger.debug('test')
    #logger.info('test')
    #logger.warning('test')
    #logger.critical('test')
    #logger.fatal('test')
    return (success, msg)
