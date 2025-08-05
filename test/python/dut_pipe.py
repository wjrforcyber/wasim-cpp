from wasim_dut import Dut
import pywasim


if __name__ == "__main__":
    dut = Dut('pipe.btor2')     # create dut

    # init dut
    dut.init_value({})          # init state value
    dut.print_curr_sv()         # print current state value
    
    # next cycle
    dut.a.value = "a1"          # set input value
    dut.b.value = "b1"
    dut.rst.value = 1
    dut.step()                  # sim one step
    dut.print_curr_sv()
    dut.check_prop()            # check property

    # next cycle
    dut.a.value = "a2"
    dut.b.value = "b2"
    dut.rst.value = 0
    dut.step()
    dut.print_curr_sv()
    dut.check_prop()
