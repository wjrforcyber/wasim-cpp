import os
import sys

script_path = os.path.realpath(__file__)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
build_dir = os.path.join(parent_dir, 'build')
sys.path.append(build_dir)

import pywasim


if __name__ == "__main__":
    dut = pywasim.Dut('adder.btor2')                                                        # create dut

    # init dut
    dut.init_value({})                                                                      # init state value
    dut.print_curr_sv()

    # next cycle
    dut.input_value({'a': "a1_symbol", 'b': "b1_symbol"}, [])                                         # set value to input
    dut.step()                                                                              # sim one step
    dut.print_curr_sv()
    dut.check_assertion(dut.out == dut.a + dut.b)

    # next cycle
    dut.input_value({'a': "a2_symbol", 'b': "b2_symbol"}, [])
    dut.step()
    dut.print_curr_sv()
    dut.check_assertion(dut.out == dut.a + dut.b)