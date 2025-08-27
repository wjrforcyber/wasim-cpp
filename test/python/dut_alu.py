from pywasim import Dut


if __name__ == "__main__":
    dut = Dut('../../design/pywasim-test/alu.btor2')     # create dut

    # init dut
    dut.set_init()          # init state value

    dut.a.value = "a0"
    dut.b.value = "b0"
    dut.control.value = 0
    dut.comb()
    print("out:", dut.out.value)

    dut.a.value = "a1"
    dut.b.value = "b1"
    dut.control.value = 1
    dut.comb()
    print("out:", dut.out.value)


