import pywasim_async

@pywasim_async.register_task
def run1(sim, dut, a, b):  # 
    dut.a.value = a
    dut.b.value = b
    dut.en.value = 1
    sim.wait_cycle(1)
    dut.en.value = 0
    sim.wait_cond(dut.out_en.value == sim.var(a))

@pywasim_async.register_task
def run2(sim, dut, a,b):  # 
    task1 = run1(sim, dut, a,b)
    sim.wait_task(task1)  # this will handle execution to run1
    assert(task1.finished)
    sim.wait_task(task1)  # this should return immediately
    return task1.return_value()
    
s=1
d=2
a=3
b=4
run1(s,d,a,b)
run1(s,d,a,3)
run2(2,3)

for c in pywasim_async._all_states:
  print (c.args)

# create dut
# create sim

# pywasim_async.start_loop
    
  
