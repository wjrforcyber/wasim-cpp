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
        self.inputvars_list = self.ts.inputvars()
        self.statevars_list = self.ts.statevars()

        self.iv_term_dict = {}
        self.iv_term_dict_default = {}
        self.constraints = []

        self.initialized = False
        # self.prop = self._get_property()

        self.combination = (len(self.statevars_list) == 0)    # comb -> True, seq -> False

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

    def _create_iv_dict(self):
        iv_dict = {}
        idx = str(self.step_cycle())
        for iv in self.inputvars_list:
            iv_dict[iv.to_string()] = iv.to_string()+ "X" + idx # inputvar string dict
        self.iv_term_dict = self.simulator.convert(iv_dict) # create default inputvars term dict
        self.iv_term_dict.update(self.iv_term_dict_default) # set default inputvars

    def set_init(self, d = {}):
        if self.initialized:
            raise RuntimeError("You cannot initialize simulator twice")
        self.initialized = True
        var_dict = self.simulator.convert(d)
        self.simulator.init(var_dict)
        self._create_iv_dict()  # create new inputvars

    def free_init(self, d = {}):
        if self.initialized:
            raise RuntimeError("You cannot initialize simulator twice");
        self.initialized = True
        var_dict = self.simulator.convert(d)
        self.simulator.free_init(var_dict)
        self._create_iv_dict()  # create new inputvars

    def set_constraint(self, constr):
        self.constraints.append(constr)
    
    def unset_constraint(self, constr):
        del self.constraints[constr]

    def clear_constraint(self):
        self.constraints = []

    def step(self, num = 1, asmpt = []):
        for _ in range(num):
            self.iv_term_dict.update(self.iv_term_dict_default) # set default inputvars again, avoid default input vars changed
            self.simulator.set_input(self.iv_term_dict, asmpt)
            self.simulator.sim_one_step()
            self._create_iv_dict()  # create new inputvars
        print (f'<cycle:{self.step_cycle()-1}>')

    def back_step(self):
        self.simulator.backtrack()
        self.simulator.undo_set_input()
        self._create_iv_dict()  # create new inputvars

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

    def check_sat(self, asst, asmpts):
        print('dut.check_sat')
        asmpts_all = self.simulator.all_assumptions()
        asmpts_all.extend(asmpts)
        asmpts_all.extend(self.constraints)
        asmpts_all.append(asst)
        return self.solver.check_sat_assuming(asmpts_all)

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
        return self.var
        
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
        nf = self.dut.simulator.var(self.name)
        if nf in self.dut.iv_term_dict:
            return self.dut.iv_term_dict[nf]
        
        # get current term of signal
        try:
            signal_nr = self.dut.simulator.interpret_state_expr_on_curr_frame(nf)   # only have state vars
            return signal_nr
        except Exception:
            if(self.dut.combination):
                signal_nr = nf.substitute(self.dut.iv_term_dict)
            else:
                signal_nr = self.dut.simulator.interpret_input_and_state_expr_on_curr_frame(nf, self.dut.iv_term_dict)  # have state vars and input vars
                print(f"Warning: expr(dut.{self.name}.value) contains current inputvars; Modifying related inputvars afterward may cause (dut.{self.name}.value) changed.")
            return signal_nr

    @value.setter
    def value(self, iv):
        # set input_signal <-> value
        try:
            iv_nr = self.dut.simulator.var(self.name)
            if self.dut.ts.is_input_var(iv_nr):
                iv_dict = self.dut.simulator.convert({self.name : iv})
                self.dut.iv_term_dict.update(iv_dict)
            else:
                raise ValueError(f"No such input variable '{self.name}'.")
        except Exception as e:
            raise ValueError(f"No such variable '{self.name}'.", e)

    def unset(self):
        iv_nr = self.dut.simulator.var(self.name)
        if iv_nr not in self.dut.iv_term_dict:
            raise ValueError(f"No such assignment to variable '{self.name}'.")
        del self.dut.iv_term_dict[iv_nr]

    @property
    def value_def(self):
        return None

    @value_def.setter
    def value_def(self, iv):
        try:
            iv_nr = self.dut.simulator.var(self.name)
            if self.dut.ts.is_input_var(iv_nr):
                iv_dict = self.dut.simulator.convert({self.name : iv})
                self.dut.iv_term_dict_default.update(iv_dict)
            else:
                raise ValueError(f"No such input variable '{self.name}'.")
        except Exception as e:
            raise ValueError(f"No such variable '{self.name}'.", e)
        
    def unset_def(self):
        iv_nr = self.dut.simulator.var(self.name)
        if iv_nr not in self.dut.iv_term_dict_default:
            raise ValueError(f"No such default assignment to variable '{self.name}'.")
        del self.dut.iv_term_dict_default[iv_nr]


class async_simulator(object):
    def __init__(self, dut):
        self._state_ptr = None # should point to a pywasim_local_state object
        self.dut = dut
        self.finished = False
    def get_var(self, name):
        return self.dut.simulator.get_var(name)
    def set_var(self, name, width:int):
        return self.dut.simulator.set_var(width, name)

    def check_valid(self, expr):
        assert (self._state_ptr)
        print('<solver call>')
        can_sat = self.dut.check_sat(~expr, self._state_ptr.branch_cond)
        print('<end solver call>')
        if can_sat:
            # the behavior here should be controllable
            # it should also be debuggable
            # maybe dump waveform
            raise AssertionError('check_valid failed')
            print("check_valid failed")
            return False
        print("check_valid pass")
        return True        
        
    def _set_stateptr(self, ptr):
        self._state_ptr = ptr
        
    # branch condition?
    def finish(self):
        self.finished = True

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
    def __init__(self, cycle = 0, cond = None, execthread = None):
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
        
    def clone(self): # it returns a passthrough object
        ret = pywasim_local_state(self.coroutine, [], {}) # you don't need to clone args and kwargs because it will not branch at invocation
        ret.pc = self.pc
        ret.finished = self.finished
        ret.retval = self.retval
        ret.await_cond = None  # you don't need to deepcopy this
        # this is because when you branch, one thread will have its await set to None to let it continue
        ret.local = self.local.copy()
        ret.branch_cond = self.branch_cond.copy()
        return ret
        
    def return_value(self):
        return self.retval
    
    def step(self):
        if self.finished:
            print ('<coroutine finished>')
            return
        if self.pc >= len(self.coroutine.funbody):
            print ('<coroutine finished>')
            self.finished = True
            return
                    
        print(f'<coroutine.pc:{self.pc}>')
        self.local['sim']._set_stateptr(self)
        if isinstance(self.coroutine.funbody[self.pc], ast.Expr):
            expr = self.coroutine.funbody[self.pc]
            if isinstance(expr.value, ast.Call):
                if isinstance(expr.value.func, ast.Attribute) and expr.value.func.value.id == 'sim' and expr.value.func.attr == 'wait_cond':
                    # in sim.wait_cond(...), you should not immediately
                    # interpret variables
                    self.local['sim'].dut._do_not_interpret_var = True
        
        if isinstance(self.coroutine.funbody[self.pc], ast.Return):
            ret = self.coroutine.funbody[self.pc]
            self.retval = eval(ret.value, {},  self.local)
            print ('<coroutine finished>')
            self.finished = True
        else:
            # sim.await will set await_cond
            tmp_stmt = ast.Module(body=[self.coroutine.funbody[self.pc]], type_ignores=[])
            exec(compile(tmp_stmt, "<ast>", "exec"), {}, self.local)
            
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
        #     if sim.check_sat(dut.a.value == 0):
        #        ...
        #
        # but this does not create execution branches
        
    def parse_arg(self):
        assert (self.pc < 0 and not self.finished)
        # parse its args, set the local variables
        func_node = self.coroutine.astnodes.body[0]
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
    
def start_loop(sim, dut, bound = -1):
    if len(_all_states) == 0:
        return

    if sim.dut is not dut:
        raise RuntimeError("Simulator and DUT do not match")

    if not dut.initialized:
        raise RuntimeError("Simulator has not been initialized")
    curr_step = 0
    while bound < 0 or curr_step < bound:
        if sim.finished:
            break
        async_one_step(sim, dut)
        curr_step += 1


def async_one_step(sim, dut):
    if len(_all_states) == 0:
        return
        
    any_runnable = True
    all_finished = True

    while any_runnable:
        any_runnable = False
        for idx,st in enumerate(_all_states):  # list of pywasim_local_state
            print(f'<coroutine #{idx}>')
            if st.finished:
                continue
            #else
            all_finished = False

            if st.pc < 0:
                # parse its args, set the local variables
                st.parse_arg()
            if st.await_cond is not None and st.await_cond.execthread is not None:
              # if the task it waits has finished
              # we can remove its blocker so that it can continue
              if st.await_cond.execthread.finished:
                st.await_cond = None
                
            # execute the corountine until we need to wait
            while st.await_cond is None and not st.finished:
                st.step()
                any_runnable = True

    if all_finished:
        print('<finished>')
        sim.finish()
        return

    # TODO: branch before step
    print('<dut.step>')
    dut.step()
    # next go through _all_states and decrease cycle or check condition
    for idx,st in enumerate(_all_states):
        print(f'<coroutine #{idx} post>')
        # assert (st.await_cond) # is not None
        # as we append passthrough to _all_states, its await_condition may be None 
        if st.await_cond is None:
            continue # just skip them
        print (st.await_cond)
        if st.await_cond.cycle:
            st.await_cond.cycle -= 1
            if st.await_cond.cycle <= 0:
                st.await_cond = None # remove its blocker so it can continue
                continue
        elif st.await_cond.cond is not None:
            # check if this condition can be true
            # check if this condition can be false
            cond_curr = dut.simulator.interpret_input_and_state_expr_on_curr_frame(st.await_cond.cond, dut.iv_term_dict)
            maybe_true = dut.check_sat(cond_curr, st.branch_cond )
            maybe_false = dut.check_sat(~cond_curr, st.branch_cond )
            print('branch:',maybe_true, maybe_false)
            if maybe_true and not maybe_false:
                st.await_cond = None
                st.branch_cond.append(cond_curr)
            elif maybe_false and not maybe_true:
                st.branch_cond.append(~cond_curr)  # record this as false
            else:
                assert(maybe_true and maybe_false)
                passthrough = st.clone()
                passthrough.branch_cond.append(cond_curr)
                st.branch_cond.append(~cond_curr)
                _all_states.append(passthrough)
                
            
    
    

    
    
