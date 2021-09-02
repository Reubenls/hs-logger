from logger import Logger
import wx
import time
import numpy as np
# from apscheduler.schedulers.background import BackgroundScheduler


class Job(object):
    def __init__(self, spec, inst_drivers, frame):
        print(inst_drivers)
        self.inst_drivers = inst_drivers
        self.spec = spec
        frame_log = Text_Log(frame.job_disp_log)
        self.logger = Logger(self, inst_drivers, frame_log)
        self.frame = frame
        self.frame.SetTitle(u"{}".format(spec.get("job_name")))
        self.graphs = []
        self.frame.add_table(4, len(spec["logged_operations"])+len(spec.get("references", {}))-1)
        self.auto_profile = AutoProfile(self)
        self.frame.add_profile_table(self.auto_profile)
        self.n = 0
        self.pauseStart = time.time()

        # self.sched = BackgroundScheduler()
        # self.sched.add_job(func=self.update_graphs, trigger='interval', seconds=5)
        # self.sched.add_job(func=self.update_table, trigger='interval', seconds=5)
        # self.sched.add_job(func=self.update_autoprofile, trigger='interval', seconds=5)
        # self.sched.start()

    def update_cycle(self):
        self.update_table()
        self.update_graphs()
        self.update_autoprofile()

    def load_profile(self):
        pass

    def auto_profile_actions(self, actions):
        for inst_op, val in actions:
            # inst_op = inst_op.split(".")
            print(inst_op, val)
            if inst_op != "":
                i_id, op_id = inst_op.split(".")
                inst_driver = self.inst_drivers.get(i_id)
                try:
                    inst_driver.write_instrument(op_id, [val])
                except:
                    print("auto profile action error")

    def update_autoprofile(self):
        self.auto_profile.update()

    def new_autoprofile_col(self):
        name, inst_ops, inst_opc, inst_opr = self.frame.get_autoprofile_new_action_dlg()
        self.auto_profile.new_set_op(name, inst_ops, inst_opc, inst_opr)

    def next_point(self):
        self.auto_profile.next_point()

    def new_point(self):
        self.auto_profile.new_point()

    def reset(self):
        pass

    def new_run(self):
        pass

    def next_n(self, n):
        pass

    def last_n(self, n):
        pass

    def assured_soak(self):
        pass

    def pause(self):
        self.logger.pause()
        self.pauseStart = time.time()

    def resume(self):
        self.logger.delay = self.logger.delay + time.time() - self.pauseStart
        self.logger.resume()

    def start(self):
        self.auto_profile.point_start_time = time.time()
        self.auto_profile.move_to_point(self.auto_profile.current_point)
        self.logger.start()

    def stop(self):
        self.logger.stop()
        self.frame.Destroy()
        # self.sched.shutdown()

    def add_graph(self, plt):  # Adds the graph to the list of graphs
        graph_names = []
        for i in range(len(self.graphs)):
            graph_names.append(self.graphs[i][0][1])
        axis_choices = self.logger.opref.copy()
        name, x, y = self.frame.get_add_graph_dialog(axis_choices)
        while graph_names.count(name) > 0:
            name = name + "\'"
        if name == "cancelled":
            return "cancelled"
        else:  # Procedure wasn't cancelled
            self.graphs.append([(plt, name), (x, y)])
            return name

    def append_graph(self, plt):  # Adds a new line to the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        axis_choices = self.logger.opref.copy()
        index, y = self.frame.get_append_graph_dialog(graph_choices, axis_choices)
        axis_check = []
        for i in range(len(self.graphs[index]) - 1):
            axis_check.append(self.graphs[index][i + 1][1])
        if index != -1:  # Procedure wasn't cancelled
            if axis_check.count(y) == 0:
                x = self.graphs[index][1][0]
                self.graphs[index].append((x, y))
            else:
                print("{} already in {}.".format(y, self.graphs[index][0][1]))

    def detract_graph(self, plt):  # Removes a line from the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        graph_index = self.frame.get_detract_graph_graph_dialog(graph_choices)
        if graph_index > -1:  # Procedure wasn't cancelled
            axis_choices = []
            for i in range(len(self.graphs[graph_index])-1):
                axis_choices.append(self.graphs[graph_index][i+1][1])
            axis_index = self.frame.get_detract_graph_axis_dialog(axis_choices)
            if graph_index > -1:  # Procedure wasn't cancelled
                self.graphs[graph_index].pop(axis_index+1)

    def remove_graph(self, plt):  # Removes the selected graph
        graph_choices = []
        for i in range(len(self.graphs)):
            graph_choices.append(self.graphs[i][0][1])
        index = self.frame.get_remove_graph_dialog(graph_choices)
        if index > -1:  # Procedure wasn't cancelled
            self.graphs.pop(index)
        return index + 3

    def update_graphs(self):  # Updates the data depicted in the graphs
        for g in self.graphs:  # g in form of [[graph object, name], [x1, y1], [x2, y2], etc...]
            leg = []
            for i in range(len(g)):
                if i == 0:
                    plt = g[0][0].figure.gca()
                    plt.clear()
                else:
                    x = g[i][0]
                    y = g[i][1]
                    leg.append(y)
                    inst_x, op = x.split('.')
                    if inst_x == "reference":
                        x_val = [d.get(x) for d in self.logger.storeref]
                    else:
                        x_val = [d[1].get(x) for d in self.logger.store]
                    inst_y, op = y.split('.')
                    if inst_y == "reference":
                        y_val = [d.get(y) for d in self.logger.storeref]
                    else:
                        y_val = [d[1].get(y) for d in self.logger.store]
                    plt.plot(x_val, y_val)
            if len(g) > 2:
                plt.legend(leg)
            g[0][0].canvas.draw()

    def update_table(self):
        self.frame.update_table(0)


class AutoProfile(object):
    def __init__(self, job):
        self.job = job
        self.profile_header = ["Points", "Soak", "Assured"]
        self.points = 1
        self.points_list = [1]
        self.soak = [50]
        self.assured = [0]
        self.operations = {}  # format "Name":(inst_op,[points])
        self.h_name = []  # The first line of the autoprofile contains the names.
        self.h_set = []  # The second line of the autoprofile contains the commands to set the setpoints.
        self.h_check = []  # The third line of the autoprofile contains the commands to read the setpoints.
        self.h_actual = []  # The first line of the autoprofile contains the commands to read the actual values.
        self.stdev_list = []  # This list contains the data required for the assured switch.
        self.current_stdev = ""  # This defines what the standard deviation is of.
        self.a_dif = 0.1  # This is the difference between the actual and measured values that assured allows.
        self.a_std = 0.1  # This is the standard deviation of measured values that assured allows.

        self.current_point = 0
        self.point_start_time = time.time()

    def load_file(self, file_name):
        grid = self.job.frame.grid_auto_profile
        rows1 = len(self.profile_header)
        cols1 = self.points

        with open(file_name, "r") as file:
            self.h_name = file.readline().strip().split(',')
            while self.h_name[0][0] != "P":
                self.h_name[0] = self.h_name[0][1:]  # Remove "ï»¿" from first item.
            self.profile_header = self.h_name.copy()
            self.h_set = file.readline().strip().split(',')
            self.h_check = file.readline().strip().split(',')
            self.h_actual = file.readline().strip().split(',')
            d1 = {}
            for name, inst_op in zip(self.h_name, self.h_set):
                d1[name] = (inst_op, [])
            for line in file:
                line = line.strip().split(',')
                for i in range(len(self.h_name)):
                    name = self.h_name[i]
                    d1[name][1].append(line[i])
            # Extra bit to remove the mandatory fields from the operations list
            # Reset the lists
            self.points_list = []
            self.soak = []
            self.assured = []
            # Fill the lists again
            for i in range(len(d1[self.h_name[0]][1])):
                self.points_list.append(d1["Points"][1][i])
                self.soak.append(d1["Soak"][1][i])
                self.assured.append(d1["Assured"][1][i])
            # Remove the data from d1
            d1.pop("Points")
            d1.pop("Soak")
            d1.pop("Assured")
            # Back to normal code
            self.points = len(d1[self.h_name[3]][1])
            self.operations = d1
            print(self.operations)

        # bSizer = self.job.frame.bSizer181
        # self.job.frame.grid_auto_profile.Destroy()
        # bSizer.Remove(0)
        # grid = wx.grid.Grid(self.job.frame.auto_profile, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        # self.job.frame.grid_auto_profile = grid
        # bSizer.Prepend(grid, 1, wx.ALL | wx.EXPAND, 5)
        # self.job.frame.auto_profile.Layout()
        # self.job.frame.add_profile_table(self)

        self.grid_refresh()

    def new_set_op(self, name, inst_ops, inst_opc, inst_opr, default=0):
        points = [0 for _ in range(self.points)]
        self.operations[name] = (inst_ops, points)
        print(self.operations)
        self.h_name.append(name)
        self.profile_header = self.h_name.copy()
        self.h_set.append(inst_ops)
        self.h_actual.append(inst_opr)
        self.h_check.append(inst_opc)
        print(self.h_set)
        print(self.h_check)
        print(self.h_actual)
        grid = self.job.frame.grid_auto_profile
        # msg = wx.grid.GridTableMessage(grid.table,
        #                                wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED, 1)
        # grid.ProcessTableMessage(msg)
        self.grid_refresh()

    def new_point(self):
        self.points += 1
        self.points_list.append(self.points)
        self.soak.append(self.soak[-1])
        self.assured.append(self.assured[-1])
        op2 = {}
        for name, op_pts in self.operations.items():
            op = op_pts[0]
            pts = op_pts[1]
            pts.append(pts[-1])
            op2[name] = (op, pts)
        self.operations = op2
        # grid = self.job.frame.grid_auto_profile
        # msg = wx.grid.GridTableMessage(grid.table,
        #                                wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, 1)
        # grid.ProcessTableMessage(msg)
        self.grid_refresh()

    def set_value(self, name, point, value):  # to check for out of range and name not found
        if name == "Soak":
            self.soak[point] = value
        elif name == "Assured":
            self.assured[point] = value
        elif name == "Points":
            self.points_list[point] = value
        else:
            op_pts = self.operations.get(name)  # check
            op_pts[1][point] = value

    def get_value(self, name, point):  # to check for out of range and name not found
        if name == "Soak":
            value = self.soak[point]
        elif name == "Assured":
            value = self.assured[point]
        elif name == "Points":
            value = self.points_list[point]
        else:
            op_pts = self.operations.get(name)  # check
            value = op_pts[1][point]
        return value

    def get_header(self):
        return self.profile_header

    def get_current_point(self):
        return self.current_point

    def restart_point(self, point):
        self.move_to_point(point)
        self.point_start_time = time.time()

    def next_point(self):
        self.job.logger.point_to_file()
        if self.points == self.current_point+1:
            self.move_to_point(0)
        else:
            self.move_to_point(self.current_point+1)

    def move_to_point(self, point):
        self.current_point = point
        self.grid_refresh()
        self.point_start_time = time.time()
        actions = []
        for inst_op, vals in self.operations.values():
            actions.append((inst_op, vals[point]))
        print(actions)
        self.job.auto_profile_actions(actions)


    def update(self):
        t1 = self.point_start_time + 60 * float(self.soak[self.current_point])  # - self.job.logger.delay  # if paused
        index = 2 + int(self.assured[self.current_point])
        if index < 3:
            if time.time() > t1:
                self.next_point()
        else:
            inst1, op1 = self.h_check[index].split('.')
            inst2, op2 = self.h_actual[index].split('.')
            value1 = self.check_instrument(inst1, op1)
            value2 = self.check_instrument(inst2, op2)
            if self.h_actual[index] == self.current_stdev:
                self.stdev_list.append(value2)  # If this is the same operation as last time, append the data.
            else:
                self.current_stdev = self.h_actual[index]
                self.stdev_list = []  # Otherwise, start a new array for the new operation.
            if time.time() > t1:
                dif = value2 - value1
                std = self.stdev()
                print("{} {}".format(dif, self.a_dif))
                print("{} {}".format(std, self.a_std))
                if abs(dif) < self.a_dif:
                    if std < self.a_std:
                        self.next_point()
                    else:
                        print("Not sufficiently stable. Standard deviation = {}.".format(std))
                else:
                    print("Point not reached. Difference = {}.".format(dif))

    def check_instrument(self, inst_id, operation_id):
        inst = self.job.logger.instruments.get(inst_id)
        result = inst.read_instrument(operation_id)
        return result[1]

    def stdev(self):
        if self.job.logger.window < len(self.stdev_list):
            std = np.std(self.stdev_list[-self.job.logger.window:])
        else:
            std = np.std(self.stdev_list)
        return std

    def highlight_row(self):
        grid = self.job.frame.grid_auto_profile
        for col in range(len(self.profile_header)):
            for row in range(self.points):
                grid.SetCellBackgroundColour(row, col, wx.Colour(255, 255, 255))
        # grid.SetCellBackgroundColour(colour=grid.GetDefaultCellBackgroundColour())
        for col in range(len(self.profile_header)):
            grid.SetCellBackgroundColour(self.current_point, col, wx.Colour(230, 235, 245))
        # grid.ForceRefresh()

    def grid_refresh(self):
        self.highlight_row()
        grid = self.job.frame.grid_auto_profile
        # self.job.frame.bSizer18.Layout()
        grid.AutoSizeRows()
        # grid.AutoSizeColumns()  # This crashes the system for some reason. Todo fix
        grid.ForceRefresh()


class Text_Log(object):
    def __init__(self, textctrl):
        self.out = textctrl

    def write(self, text):
        text = str(text)+'\n'
        self.out.WriteText(text)
