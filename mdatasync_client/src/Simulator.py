import wx
import time
from WxLogger import Log
from identifiers import *
import wx.lib.filebrowsebutton as filebrowse
import os
import os.path
import sys
import tempfile
import logging

logger = logging.getLogger(__name__)

__all__ = ["Simulator", "WorkList"]

class Simulator(object):
    """
    The simulator can generate "data" files from a CSV work list.

    `destdir` is the place to create files; a temporary directory is
    used by default.

    If `temp_files` is True, then TEMPBASE, TEMPDAT and TEMPDIR files
    will be dropped into any sample directory ending with .d.
    """
    def __init__(self, destdir=None, temp_files=False):
        self.destdir = self._setup_destdir(destdir)
        self.generate_temp_files = temp_files
        self._created_files = []
        self._created_dirs = set()

    TEMP_NAMES = ['TEMPBASE', 'TEMPDAT', 'TEMPDIR']

    def _setup_destdir(self, destdir=None):
        if destdir is None:
            destdir = tempfile.mkdtemp(prefix="simulator-")

        if not os.path.exists(destdir):
            logger.info("Creating directory %s" % destdir)
            self._create_dir(destdir)
        else:
            logger.info("Using directory %s" % destdir)

        return destdir

    def process_worklist(self, worklist):
        """
        Creates "data" for each item in `worklist`. This should be a
        list of filenames, such as what is created by
        :class:`WorkList`.
        """
        count = 0
        for count, listitem in enumerate(worklist):
            fname = os.path.join(self.destdir, listitem)
            if not os.path.exists(fname):
                try:
                    if fname.endswith('.d'):
                        #create a directory instead, and blat a bunch of files there.
                        self._create_dir(fname)
                        logger.info("Created dir %d: %s" % (count, fname))
                        for i in range(5):
                            self._create_file(fname, str(i))
                        if self.generate_temp_files:
                            if count == 0:
                                for temp_file in self.TEMP_NAMES:
                                    self._create_file(fname, temp_file)
                            if count == 1:
                                self._create_file(fname, self.TEMP_NAMES[0])
                            if count == 2:
                                self._create_file(fname, self.TEMP_NAMES[1])
                            if count == 3:
                                self._create_file(fname, self.TEMP_NAMES[2])
                    else:
                        open(fname, 'w').close()
                        self._created_files.append(fname)
                        logger.info("Wrote item %d: %s" % (count, fname))
                except Exception, e:
                    logger.error("Error writing item %d:%s - %s" % (count, fname, str(e)))

            else:
                logger.info("Item %d already exits: %s" % (count, fname) )

    def add_more_data_with_worklist(self, worklist):
        """
        Appends/creates "more data" to the files/directories already
        created by `Simulator.process_worklist`.
        """
        for listitem in worklist:
            fname = os.path.join(self.destdir, listitem)
            if not os.path.exists(fname):
                logger.info("was asked to add more data, but item doesn't exist: %s" % fname)
            else:
                if os.path.isdir(fname):
                    # drop another file in the directory
                    file_num = len(os.listdir(fname))
                    self._create_file(fname, str(file_num))
                    self._create_file(fname, str(file_num + 1))
                else:
                    with open(fname, 'w+') as f:
                        f.write("\nHere is some extra data for the test file.\n")
                    logger.info("Updated item: %s" % fname)

    def _create_file(self, dir_name, file_name):
        tfname = os.path.join(dir_name, file_name)
        f = open(tfname, 'w')
        f.write('Test string for data upload of MS Data Sync Client simiulator')
        f.close()
        logger.info('Created file %s' % (tfname))
        self._created_files.append(tfname)

    def _create_dir(self, fname):
        parent = os.path.join(*os.path.split(os.path.normpath(fname))[:-1])
        if not os.path.exists(parent):
            # create parents first
            self._create_dir(parent)

        os.mkdir(fname)
        self._created_dirs.add(fname)

    def cleanup(self):
        """
        This method will delete all files and directories which have
        been created by this simulator.
        """
        for fname in self._created_files:
            logger.info("Removing file %s" % fname)
            try:
                os.remove(fname)
            except OSError:
                logger.exception("cleanup")
        self._created_files = []

        for dirname in sorted(self._created_dirs, reverse=True):
            logger.info("Removing directory %s" % dirname)
            try:
                os.rmdir(dirname)
            except OSError:
                logger.exception("cleanup")
        self._created_dirs.clear()

    @property
    def created_files(self):
        return self._created_files

    @classmethod
    def istemp(cls, filename):
        return any(filename.endswith(name) for name in cls.TEMP_NAMES)

    def relpath(self, filename):
        if not filename.startswith(self.destdir):
            raise ValueError, "filename doesn't start with %s" % self.destdir
        return filename[len(self.destdir)+1:]

class GeneratePopup(wx.Dialog):
    def __init__(self, log, parent, fileslist, destdir, generate_temp_files = False):
        self.log = log
        self.generate_temp_files = generate_temp_files
        wx.Dialog.__init__(self, parent, -1)
        self.destdir = destdir
        self.contentPanel = wx.Panel(self, -1)
        _cp = self.contentPanel
        self.listctrl = wx.ListBox(_cp, -1, style=wx.LB_MULTIPLE)


        self.listctrl.InsertItems([i for i in fileslist], 0)
        for p in xrange(0, len(fileslist)):
            self.listctrl.Select(p)

        self.textlabel = wx.StaticText(_cp, -1, "Files to Generate:")
        self.OkButton = wx.Button(_cp, id=wx.ID_OK)
        self.OkButton.Bind(wx.EVT_BUTTON, self.GenerateFiles)
        self.CancelButton = wx.Button(_cp, id=wx.ID_CANCEL)
        self.buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttonsizer.Add(self.OkButton, 0, flag=wx.ALL, border=2)
        self.buttonsizer.Add(self.CancelButton, 0, flag=wx.ALL, border=2)

        self.contentsizer = wx.BoxSizer(wx.VERTICAL)
        self.contentsizer.Add(self.textlabel, 0, flag=wx.ALL, border=2)
        self.contentsizer.Add(self.listctrl, 0, flag=wx.ALL|wx.GROW, border=2)
        self.contentsizer.Add(self.buttonsizer, 1, flag=wx.ALL|wx.GROW, border=2)
        _p = self.contentsizer

        self.contentPanel.SetSizerAndFit(_p)
        _p.Fit(self)

    def GenerateFiles(self, evt):
        print self.destdir

        countes = self.listctrl.GetSelections()
        worklist = []
        for count in countes:
            worklist.append(self.listctrl.Items[count])

        sim = Simulator(self.destdir, temp_files=self.generate_temp_files)
        sim.process_worklist(worklist)

        self.EndModal(0)


class MainWindow(wx.Frame):
    def __init__(self, parent):
        self.shouldGenerateTempFiles = False
        wx.Frame.__init__(self, parent, -1, "MS Simulator")

        self.contentPanel = wx.Panel(self, -1)
        _cp = self.contentPanel
        self.inputText =  wx.TextCtrl(_cp, -1,
                                    style = wx.TE_MULTILINE|wx.HSCROLL)

        self.outputText =  wx.TextCtrl(_cp, -1,
                                    style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)

        self.inputLabel = wx.StaticText(parent = _cp)
        self.inputLabel.SetLabel(label='Paste worklist here')

        self.outputLabel = wx.StaticText(parent = _cp)
        self.outputLabel.SetLabel(label='Log')

        self.genButton = wx.Button(_cp, ID_GENERATEFILES_BUTTON)
        self.genButton.SetLabel("Generate Files")
        self.genButton.Bind(wx.EVT_BUTTON, self.OnGenerate)

        self.clearButton = wx.Button(_cp, ID_CLEARINPUT_BUTTON)
        self.clearButton.SetLabel("Clear")
        self.clearButton.Bind(wx.EVT_BUTTON, self.OnClear)

        self.tempGenerationCheckBox = wx.CheckBox(_cp, -1, 'Generate temp files')
        self.tempGenerationCheckBox.Bind(wx.EVT_CHECKBOX, self.toggleTempFiles)

        self.filectrl = filebrowse.DirBrowseButton(_cp, -1, size=(450, -1), changeCallback = None, labelText='Choose Dir', startDirectory = str('.') )
        #ctrl.SetValue(str(self.config.getValue(key)) )

        self.panelSizer = wx.BoxSizer(wx.VERTICAL)

        self.log = Log(self.outputText)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(self.log)
        wx.Log_SetActiveTarget(self.log)

        if wx.Platform == "__WXMAC__":
            self.inputText.MacCheckSpelling(False)
            self.outputText.MacCheckSpelling(False)

        _p = self.panelSizer
        #tsizer.Add(self.inputText, 1, flag=wx.ALL, border=2)
        _p.Add(self.inputLabel, 0, flag=wx.ALL, border=2)
        _p.Add(self.inputText, 1, flag=wx.ALL|wx.GROW, border=2)
        _p.Add(self.clearButton, 0, flag=wx.ALL, border=2)
        _p.Add(self.filectrl, 1, flag=wx.ALL|wx.GROW, border=2)
        _p.Add(self.tempGenerationCheckBox, 0, flag=wx.ALL, border=2)
        _p.Add(self.genButton, 0, flag=wx.ALL, border=2)
        _p.Add(self.outputLabel, 0, flag=wx.ALL, border=2)
        _p.Add(self.outputText, 1, flag=wx.ALL|wx.GROW, border=2)

        self.contentPanel.SetSizerAndFit(_p)
        self.panelSizer.Fit(self)

    def toggleTempFiles(self, event):
        self.shouldGenerateTempFiles = not self.shouldGenerateTempFiles

    def OnGenerate(self, event):
        self.log('Generate')
        worklist = WorkList(self.inputText.GetValue())
        print worklist

        dlg = GeneratePopup(self.log, self, worklist, self.filectrl.GetValue(), self.shouldGenerateTempFiles)
        dlg.ShowModal()
        dlg.Destroy()


    def OnClear(self, event):
        self.log('Clear')
        self.inputText.Clear()

class WorkList(list):
    """
    WorkList is a list of sample filenames loaded a CSV file. `text`
    is the CSV-formatted worklist.
    """
    def __init__(self, text):
        for line in text.splitlines():
            try:
                uname, srcdir, fname, methdir, methfile, sampname = line.split(',')
                self.append(fname)
            except ValueError:
                pass

class MSSimulatorApp(wx.PySimpleApp):
    def OnInit(self):
        self.win = MainWindow(None)
        self.win.Show(True)
        self.SetTopWindow(self.win)
        return True

def main():
    m = MSSimulatorApp(None)
    m.MainLoop()
    return 0

if __name__ == "__main__":
    sys.exit(main())
