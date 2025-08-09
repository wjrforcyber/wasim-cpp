from pywasim import Dut, zero_extend


if __name__ == "__main__":
    dut = Dut('adder.btor2')    # create dut

    # init dut
    dut.init_value({})          # init state value
    dut.print_curr_sv()         # print current state value
    
    # next cycle
    dut.a.value = "a1"          # set input value
    dut.b.value = "b1"
    print(dut.a.value)
    dut.a.unset()
    dut.a.value = "anew"        # set input value
    # print(dut.f)              # this should raise an error
    dut.step()                  # sim one step
    dut.print_curr_sv()

    a0 = dut.a.value

    # next cycle
    dut.a.value = "a2"
    dut.b.value = "b2"
    dut.step()
    dut.print_curr_sv()

    b1 = dut.b.value
    out1 = dut.out.value

    # assert
    dut.check_assertion(out1 == zero_extend(a0, 1) + zero_extend(b1, 1))
    
