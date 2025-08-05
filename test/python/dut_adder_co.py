from copywasim import *
from wasim_dut import Dut
import pywasim


async def simple_test(dut):
    # init
    clk = Clock(0, 20, units='ns')
    dut.init_value({})
    dut.print_curr_sv()

    # run clk
    asyncio.create_task(clk.start())            # start 

    # run step
    for cycle in range(1, 5):
        dut.a.value = "a" + str(cycle)          # set input value
        dut.b.value = "b" + str(cycle)
        await RisingEdge(clk)                   # wait for rising edge
        dut.step()                              # sim one step

        dut.print_curr_sv()
        dut.check_assertion(dut.a.value == dut.b.value)
        # await FallingEdge(clk)                # wait for falling edge


if __name__ == "__main__":
    dut = Dut('adder.btor2')            # create dut
    asyncio.run(simple_test(dut))       # run the test asynchronously

    