import os
import sys

import asyncio
from copywasim import *

script_path = os.path.realpath(__file__)
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
build_dir = os.path.join(parent_dir, 'build')
sys.path.append(build_dir)

import pywasim


async def simple_test(dut):
    clk = Clock(0, 20, units='ns')
    dut.init_value({})
    dut.input_value({'a': "symbol_a0", 'b': "symbol_b0"}, [])                               # set value to input
    dut.print_curr_sv()

    asyncio.create_task(clk.start())                                                        # start clock
    await RisingEdge(clk)                                                             # synchronize clock
    dut.step()
    dut.print_curr_sv()

    for cycle in range(1, 5):
        dut.input_value({'a': "symbol_a" + str(cycle), 'b': "symbol_b" + str(cycle)}, [])
        await RisingEdge(clk)
        dut.step()
        dut.print_curr_sv()
        dut.check_assertion(dut.out == dut.a)


if __name__ == "__main__":
    dut = pywasim.Dut('adder.btor2')                                                        # create dut
    asyncio.run(simple_test(dut))                                                           # Run the test asynchronously

    