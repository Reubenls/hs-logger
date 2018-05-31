import wx
import json
import os
import sys
from ctrl_ui import ctrl_frame, job_frame, axes_dialog
from logger import Logger
from job import Job

import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar


class Main_Frame(ctrl_frame):
    def __init__(self,control):
        ctrl_frame.__init__(self,None)
        self.ctrl = control

    def switchToJob(self,event):
        print(event)
        job = event.GetEventObject().GetStringSelection()
        print(job)
        job = self.ctrl.jobs.get(job)
        jframe = job.frame
        jframe.Show()
        jframe.Maximize(False)
        jframe.SetFocus()

    def OnCloseFrame(self, event):
        dialog = wx.MessageDialog(self, message="Are you sure you want to quit?", style=wx.YES_NO,
                                  pos=wx.DefaultPosition)
        response = dialog.ShowModal()

        if (response == wx.ID_YES):
            self.OnExitApp(event)
        else:
            event.StopPropagation()

    def OnExitApp(self, event):
        self.Destroy()
        self.ctrl.shutdown()
        self.ctrl.app.ExitMainLoop()

    def cb (self,event):
        pass

    def err (self,err):
        print(err)

    def file_open(self, event):
        self.dirname = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*", wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.ctrl.open_job_file(self.dirname, self.filename,self.cb,self.err)
        dlg.Destroy()

    def update_inst_list(self, insts):
        self.inst_listbox.Clear()
        self.inst_listbox.InsertItems(list(insts),0)


class myjobframe(job_frame):
    def __init__(self,job):
        job_frame.__init__(self,None)
        self.job = job
        self.resume_b.Enable(False)

    def hide(self,event):
        self.Hide()

    def pause_log( self, event ):
        self.job.pause()
        self.pause_b.Enable(False)
        self.resume_b.Enable(True)

    def resume_log( self, event ):
        self.job.resume()
        self.pause_b.Enable(True)
        self.resume_b.Enable(False)

    def start_log( self, event ):
        self.start_b.Enable(False)
        self.job.start()

    def add_graph(self,event):
        book = self.job_book
        plt = Plot(book)
        book.AddPage(plt,'figure')
        self.Layout()
        self.job.add_graph(plt)

    def get_axes_dialog(self,choices):
        dlg = axes_dialog(self)
        dlg.y_choice.AppendItems(choices)
        dlg.x_choice.AppendItems(choices)
        res = dlg.ShowModal()
        if res ==wx.ID_OK:
            x = dlg.x_choice.GetStringSelection()
            y = dlg.y_choice.GetStringSelection()
        dlg.Destroy()
        return x,y



class Plot(wx.Panel):
    def __init__(self, parent, id=-1, dpi=None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2, 2))
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.toolbar = NavigationToolbar(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
        self.SetSizer(sizer)

# class Job(object):
#     def __init__(self,spec,inst_drivers,frame):
#         self.spec = spec
#         self.logger = logger
#         self.frame = frame


class Controller(object):
    def __init__(self):

        self.jobs = {}
        self.instruments = {'a':'v'}

        self.app = wx.App()
        self.frame = Main_Frame(self)

        self.frame.Show()
        self.app.MainLoop()

    def open_job_file(self, direc, fn, cb, err):
        try:
            f = open(os.path.join(direc, fn), 'r')
            job_spec = json.load(f)
            jn = job_spec["job_name"]
            job_instrument_drivers = self.load_instruments(job_spec["instruments"])
            self.update_instruments(job_instrument_drivers)
            # print(job_instrument_drivers)
            # logger = Logger(job_spec,job_instrument_drivers)
            jframe = myjobframe(None)
            job = Job(job_spec,job_instrument_drivers,jframe)
            jframe.job = job
            self.jobs[jn] = job
            self.frame.job_listbox.InsertItems([jn],0)
            cb(True)

        except ValueError as e:
            print(e)
            err('not a valid job file')
        except OSError as e:
            print(e)
            err('not a valid job file')
        finally:
            f.close()

    def update_instruments(self,insts):
        self.instruments.update(insts)
        self.frame.update_inst_list(self.instruments.keys())


    def load_instruments(self, inst_spec):
        instruments = {}
        for inst_id, instrument in inst_spec.items():
            if inst_id in self.instruments:
                instruments[inst_id] = self.instruments[inst_id]
            else:
                if isinstance(instrument, str):
                    try:
                        instrument = json.load(open(instrument))

                    except (OSError, ValueError):
                        sys.stderr.write("Error Loading Insturment: {}".format(inst_id))
                        sys.exit(1)
                inst_id = instrument["instrument_id"]
                driver_name = instrument["driver"]
                if str.startswith(driver_name, "generic"):
                    driver = getattr(__import__("drivers." + driver_name), driver_name)
                    klass = getattr(driver, driver_name)
                    inst_driver = klass(instrument)
                    instruments[inst_id] = inst_driver
                else:
                    driver = getattr(__import__("drivers." + driver_name), driver_name)
                    klass = getattr(driver, driver_name)
                    inst_driver = klass(instrument)
                    instruments[inst_id] = inst_driver

        return instruments

    def shutdown(self):
        for job in self.jobs.values():
            job.stop()

def main():
    ctrl = Controller()


if __name__ == '__main__':
    main()