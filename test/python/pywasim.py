import os
import sys

script_path = os.path.realpath(__file__)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
build_dir = os.path.join(parent_dir, 'build')
sys.path.append(build_dir)

from pywasimbase import *
# TransSys, Simsimulator

class Dut:
    def __init__(self, btorname):
        self.ts = TransSys(btorname)
        self.simulator = Symsimulator(self.ts)
        self.solver = self.simulator.get_solver()

        self.iv_dict = {}
        self.prop = self._get_property()


    def _get_property(self):
        prop_list = self.ts.prop()
        if not prop_list:
            print("No property to check!")
            return None
        elif len(prop_list) == 1:
            print("property:", prop_list[0])
            return prop_list[0]
        else:
            prop_i = prop_list[0]
            for idx in range(1, len(prop_list)):
                # prop_i = pywasim.make_term("And", prop_i, prop_list[idx])
                prop_i = prop_i & prop_list[idx]
            print("property:", prop_i)
            return prop_i

    def init_value(self, d):
        var_dict = self.simulator.convert(d)
        self.simulator.init(var_dict)

    def step(self):
        var_dict = self.simulator.convert(self.iv_dict)
        self.iv_dict = {}
        self.simulator.set_input(var_dict, [])
        self.simulator.sim_one_step()

    def back_step(self):
        self.simulator.backtrack()
        self.simulator.undo_set_input()

    def step_cycle(self):
        return self.simulator.tracelen()

    def check_prop(self):
        cur_prop = self.simulator.interpret_state_expr_on_curr_frame(self.prop)
        assumptions = self.simulator.all_assumptions()
        print(f"property: {cur_prop.to_string()}")
        for a in assumptions:
            print(f"assumption: {a.to_string()}")

        self.solver.push()
        for a in assumptions:
            self.solver.assert_formula(a)
        f = ~cur_prop   # make_term(not, cur_prop)
        self.solver.assert_formula(f)
        res = self.solver.check_sat()
        self.solver.pop()

        if res:
            print("check prop result: fail!")
        else:
            print("check prop result: pass!")
        return not res  # unsat -> return True

    def check_assertion(self, assertion):
        print(f"assertion: {assertion.to_string()}")

        self.solver.push()
        formula = ~assertion    # make_term(not, assertion)
        self.solver.assert_formula(formula)
        res = self.solver.check_sat()
        self.solver.pop()

        if res:
            print("check assertion result: fail!")
        else:
            print("check assertion result: pass!")
        return not res

    def print_curr_sv(self):
        self.simulator.print_current_step()

    def print_curr_assumptions(self):
        self.simulator.print_current_step_assumptions()

    def __getattr__(self, signal_name):
        self.ts.lookup(signal_name) # add a check to make sure the signal_name do exist
        return SignalProxy(self, signal_name)
    
    def get_signal(self, signal_name):
        # just in case some signals have the same name as the class method
        # you can still use this function to get it
        self.ts.lookup(signal_name)
        return SignalProxy(self, signal_name)
    


class SignalProxy:
    def __init__(self, dut, signal_name):
        self.dut = dut           # class Dut instance
        self.name = signal_name  # example: "a"

    @property
    def value(self):
        # if you have assigned, get the one you assigned
        if self.name in self.dut.iv_dict:
            return self.dut.iv_dict[self.name]
        # get current term of signal
        try:
            signal_nr = self.dut.simulator.cur(self.name)
            return signal_nr
        except Exception as e:
            raise ValueError(f"Cannot get value of signal '{self.name}': {e}")

    @value.setter
    def value(self, iv):
        # set input_signal <-> value
        try:
            iv_nr = self.dut.simulator.var(self.name)
            if self.dut.ts.is_input_var(iv_nr):
                self.dut.iv_dict[self.name] = iv
            else:
                raise ValueError(f"No such input variable '{self.name}'.")
        except Exception as e:
            raise ValueError(f"No such variable '{self.name}'.", e)
            
    def unset(self):
        if self.name not in self.dut.iv_dict:
            raise ValueError(f"No such assignment to variable '{self.name}'.")
        del self.dut.iv_dict[self.name]
        

