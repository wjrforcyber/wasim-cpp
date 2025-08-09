import os
import sys
import inspect
import ast
from functools import wraps

script_path = os.path.realpath(__file__)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
build_dir = os.path.join(parent_dir, 'build')
sys.path.append(build_dir)

from pywasimbase import *
# TransSys, Simsimulator

_all_coroutine = []
_all_states = []

class Dut:
    def __init__(self, btorname):
        self.ts = TransSys(btorname)
        self.simulator = Symsimulator(self.ts)
        self.solver = self.simulator.get_solver()
        
        self._do_not_interpret_var = False # if true, will not return SignalProxy
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
        v = self.ts.lookup(signal_name) # add a check to make sure the signal_name do exist
        if self._do_not_interpret_var:
            return VarProxy(self, signal_name, v)
        else:
            return SignalProxy(self, signal_name)
    
    def get_signal(self, signal_name):
        # just in case some signals have the same name as the class method
        # you can still use this function to get it
        v = self.ts.lookup(signal_name)
        if self._do_not_interpret_var:
            return VarProxy(self, signal_name, v)
        else:
            return SignalProxy(self, signal_name)
    
class VarProxy:
    def __init__(self, dut, name, var):
        self.dut = dut  # class Dut instance
        self.name = name
        self.var = var  # example: "a"
    @property
    def value(self):
        return v
        
    @value.setter
    def value(self, iv):
        raise RuntimeError(f"You cannot set value to '{self.name}'.")
    
    

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
        


class async_simulator(object):
    def __init__(self, dut):
        self._state_ptr = None # should point to a pywasim_local_state object
        self.dut = dut
        
    def _set_stateptr(self, ptr):
        self._state_ptr = ptr
        
    # branch condition?
        
    def wait_cycle(self, num:int = 1):
        assert(self._state_ptr)
        assert(num > 0)
        self._state_ptr.await_cond = await_condition(cycle = num)
        
    def wait_task(self, task):
        assert(isinstance(task, pywasim_local_state))
        assert(self._state_ptr)
        self._state_ptr.await_cond = await_condition(execthread = task)        
        
    def wait_cond(self, cond):
        assert(self._state_ptr)
        self._state_ptr.await_cond = await_condition(cond = cond)
        
    def wait_posedge(self, signal):
        assert(self._state_ptr)
        assert False # not implemented
        pass
        
    def wait_negedge(self, signal):
        assert(self._state_ptr)
        assert False # not implemented
        pass
        

class await_condition(object):
    def __init__(self, cycle = -1, cond = None, execthread = None):
        self.cycle = cycle
        self.cond = cond
        self.execthread = execthread
    # you will need to test if this is ready

class pywasim_local_state(object):
    def __init__(self, coroutine, args, kwargs):
        self.coroutine = coroutine
        self.pc = -1
        self.finished = False
        self.retval = None
        self.args = args
        self.kwargs = kwargs
        self.local = {}
        self.await_cond = None  # await condition could be clock(n)
        self.branch_cond = []
        
    def clone(self):
        ret = pywasim_local_state(self.coroutine, [], {}) # you don't need to clone args and kwargs because it will not branch at invocation
        ret.pc = self.pc
        ret.finished = self.finished
        ret.retval = self.retval
        ret.await_cond = None  # you don't need to deepcopy this
        # this is because when you branch, one thread will have its await set to None to let it continue
        ret.local = self.local.copy()
        ret.branch_cond = self.branch_cond.copy()
        
    def return_value(self):
        return self.retval
    
    def step(self):
        if self.finished:
            return
        if pc >= len(self.coroutine.funbody):
            self.finished = True
            return
                    
        self.local['sim']._set_stateptr(self)
        if isinstance(self.coroutine.funbody[self.pc], ast.Expr):
            expr = self.coroutine.funbody[self.pc]
            if isinstance(expr.value, ast.Call):
                if isinstance(expr.value.func, ast.Attribute) and expr.value.func.value.id == 'sim' and expr.value.func.attr='wait_cond':
                    # in sim.wait_cond(...), you should not immediately
                    # interpret variables
                    self.local['sim'].dut._do_not_interpret_var = True
        
        if isinstance(self.coroutine.funbody[self.pc], ast.Return):
            ret = self.coroutine.funbody[self.pc]
            self.retval = eval(ret.value, locals = self.local)
            self.finished = True
        else:
            # sim.await will set await_cond
            exec(self.coroutine.funbody[self.pc], locals = self.local)
            
        self.local['sim']._set_stateptr(None)
        self.local['sim'].dut._do_not_interpret_var = False
        self.pc += 1
        
        # currently, it is only a quick and dirty implementation
        # in general it is not as easy as it seems to be
        # you should check if it is a while-loop and maintain the frames yourself
        # in this way, you can also handle for example:
        #    if dut.a.value == 0:
        #        ...
        #    else:
        #        ...
        # 
        # and create branches as you see fit
        #
        # currently you can write it as
        #     if sim.is_sat(dut.a.value == 0):
        #        ...
        #
        # but this does not create execution branches
        
    def parse_arg(self):
        assert (self.pc < 0 and not self.finished)
        # parse its args, set the local variables
        code = self.coroutine.lines
        assert (code[0].strip()[0] == '@')
        assert (code[1].strip()[0:3] == 'def')
        func_node = ast.parse(code[1]).body[0]
        assert isinstance(func_node, ast.FunctionDef)
        args = [arg.arg for arg in func_node.args.args]
        idx = 0
        for arg in args:
            if idx < len(self.args):
                self.local[arg] = self.args[idx]
            elif arg in self.kwargs:
                self.local[arg] = self.kwargs[arg]
                del self.kwargs[arg]
            else:
                raise RuntimeError('no arg for ' + arg)
            idx += 1
        if idx < len(self.args):
            if func_node.args.vararg:
                self.local[func_node.args.vararg] = self.args[idx:]
            else:
                raise RuntimeError('too many arguments ' + self.args[idx:])
        if len(self.kwargs):
            if func_node.args.kwarg:
                self.local[func_node.args.kwarg] = self.kwargs
            else:
                raise RuntimeError('too many arguments ' + self.kwargs)
        self.pc = 0
                
                
# create pointers
class pywasim_coroutine(object):
    def __init__(self, lines):
        self.lines = lines.split(sep = '\n')
        self.astnodes = ast.parse(lines)
        assert (len(self.astnodes.body) == 1)
        self.funbody = self.astnodes.body[0].body
        # print (self.funbody[3])
        
    def invoke(self, *args, **kwargs):
        _all_states.append(pywasim_local_state( coroutine = self, args = args, kwargs = kwargs))
        return _all_states[-1]  # you can use sim.wait_task() on this

def register_task(func):
    code = inspect.getsource(func)
    _all_coroutine.append(pywasim_coroutine(lines = code))
    l = len(_all_coroutine)
    def wrapper(*args, **kwargs):
        _all_coroutine[l-1].invoke(*args, **kwargs)
    return wrapper # this is used to register the args
    
def start_loop(sim, dut):
    if len(_all_states) == 0:
        return
        
    any_runnable = True
    while any_runnable:
        any_runnable = False
        for st in _all_states:  # list of pywasim_local_state
            if st.pc < 0:
                # parse its args, set the local variables
                st.parse_arg()
            if st.await_cond is not None:
              # if the task it waits has finished
              # we can remove its blocker so that it can continue
              if st.await_cond.execthread.finished:
                st.await_cond = None
                
            # execute the corountine until we need to wait
            while st.await_cond is None:
                st.step()
                any_runnable = True
                
    # TODO: branch before step
    dut.step()
    # next go through _all_states and decrease cycle or check condition
    for st in _all_states:
        # assert (st.await_cond) # is not None
        # as we append passthrough to _all_states, its await_condition may be None 
        if st.await_cond is None:
            continue # just skip them
        if st.await_cond.cycle:
            st.await_cond.cycle -= 1
            if st.await_cond.cycle == 0:
                st.await_cond = None # remove its blocker so it can continue
        elif st.await_cond.cond:
            # check if this condition can be true
            # check if this condition can be false
            maybe_true = True # TODO FIXME
            maybe_false = True
            if maybe_true and not maybe_false:
                st.await_cond = None
                st.branch_cond.append(st.await_cond.cond)
            elif maybe_false and not maybe_true:
                st.branch_cond.append(~st.await_cond.cond)  # record this as false
            else:
                assert(maybe_true and maybe_false)
                passthrough = st.clone()
                passthrough.branch_cond.append(st.await_cond.cond)
                st.branch_cond.append(~st.await_cond.cond)
                _all_states.append(passthrough)
                
            
    
    

    
    
