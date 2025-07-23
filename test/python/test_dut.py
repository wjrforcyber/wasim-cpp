import os
import sys

script_path = os.path.realpath(__file__)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
build_dir = os.path.join(parent_dir, 'build')
sys.path.append(build_dir)

import pywasim


if __name__ == "__main__":
    dut = pywasim.Dut('pipe.btor2')                                                         # create dut

    # init dut
    dut.init_value({})                                                                      # init state value
    dut.input_value({'a': "a0_symbol", 'b': "b0_symbol", 'c': "c0_symbol", 'rst':0}, [])    # set value to input

    cur_state = dut.get_curr_state([])                                                      # print init stage signal
    sv = cur_state.get_sv()
    for key in sv:
      print(key, ":",sv[key])

    dut.check_prop()                                                                        # check assertion
    
    # next cycle
    dut.step()                                                                              # sim one step
    dut.input_value({'a': "a1_symbol", 'b': "b1_symbol", 'c': "c1_symbol", 'rst':0}, [])

    cur_state = dut.get_curr_state([])
    sv = cur_state.get_sv()
    for key in sv:
      print(key, ":",sv[key])

    dut.check_prop()
