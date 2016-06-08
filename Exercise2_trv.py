import simpy
import numpy as np
import pandas as pd
import random

random.seed(42)

def Part(env, name, resources, log):
    print('{0}: {1} is born'.format(env.now, name))
    arrival = env.now

    for i in range(3):
        with resources[i].machine.request() as request:
            # requests entrance to station
            start = env.now
            yield request

            # gets processed
            log.QueueWait(resources[i].name, env.now, env.now-start)
            print('{0}: {1} enters {2}'.format(env.now, name, resources[i].name))
            yield env.process(resources[i].use(name, log))

            # leaves station
            resources[i].machine.release(request)

            # record the time
            print('{0}: {1} leaves {2}'.format(env.now, name, resources[i].name))

    span = env.now - arrival
    log.Span(name, span)

class logbook(object):
    def __init__(self, env):
        self.env = env

        # queue stats
        self.DrillQSize = ['Time', 'Size']
        self.WashQSize = ['Time', 'Size']
        self.InspectQSize = ['Time', 'Size']

        self.DrillQWait = ['Time', 'Wait']
        self.WashQWait = ['Time', 'Wait']
        self.InspectQWait = ['Time', 'Wait']

        # duration stats
        self.PartSpans = ['Part Name', 'Duration']

        # inspection stats
        self.passes = 0
        self.failures = 0

    def QueueSize(self, center, time, entry):
        if entry == []:
            entry = 0

        if center == 'DrillingCenter':
            self.DrillQSize = np.vstack((self.DrillQSize, [time, entry]))
        if center == 'WashingCenter':
            self.WashQSize = np.vstack((self.WashQSize, [time, entry]))
        if center == 'InspectionCenter':
            self.InspectQSize = np.vstack((self.InspectQSize, [time, entry]))

    def QueueWait(self, center, time, entry):
        if center == 'DrillingCenter':
            self.DrillQWait = np.vstack((self.DrillQWait, [time, entry]))
        if center == 'WashingCenter':
            self.WashQWait = np.vstack((self.WashQWait, [time, entry]))
        if center == 'InspectionCenter':
            self.InspectQWait = np.vstack((self.InspectQWait, [time, entry]))

    def InspectionCenter(self, entry):
        if 'Pass' in entry:
            self.passes += 1
        elif 'Fail' in entry:
            self.failures += 1

    def Span(self, partname, duration):
        self.PartSpans = np.vstack((self.PartSpans, [partname, duration]))

    def Record(self):
        print('Passes: {0}'.format(self.passes))
        print('Failures: {0}'.format(self.failures))

        pd.DataFrame(self.DrillQWait).to_csv('DrillQueueWait.csv', sep=',', index=False, header=False)
        pd.DataFrame(self.WashQWait).to_csv('WashQueueWait.csv', sep=',', index=False, header=False)
        pd.DataFrame(self.InspectQWait).to_csv('InspectQueueWait.csv', sep=',', index=False, header=False)

        pd.DataFrame(self.DrillQSize).to_csv('DrillQueueSize.csv', sep=',', index=False, header=False)
        pd.DataFrame(self.WashQSize).to_csv('WashQueueSize.csv', sep=',', index=False, header=False)
        pd.DataFrame(self.InspectQSize).to_csv('InspectQueueSize.csv', sep=',', index=False, header=False)

        pd.DataFrame(self.PartSpans).to_csv('PartSpan.csv', sep=',', index=False, header=False)

class Center(object):
    def __init__(self, name, env, cap, mintime, midtime, maxtime):
        self.env = env
        self.name = name
        self.machine = simpy.Resource(env, capacity=cap)
        self.delaymin = mintime
        self.delaymid = midtime
        self.delaymax = maxtime
        self.failrate = 0.2

    def use(self, partname, log):
        # enter queue length into logbook
        log.QueueSize(self.name, self.env.now, len(self.machine.queue))

        # processing time
        yield self.env.timeout(random.triangular(self.delaymin, self.delaymax, self.delaymid))
        print('{0}: {1} finishes with {2}'.format(env.now, self.name, partname))

        # perform inspection test
        if self.name == 'InspectionCenter':
            result = random.randint(0, 100)
            if result>20:
                print('>> {0} Passes Inspection'.format(partname))
                log.InspectionCenter('Pass')
            else:
                print('>> {0} Fails Inspection'.format(partname))
                log.InspectionCenter('Fail')


def setup(env, log):

    # create all the resources!
    Drill = Center('DrillingCenter', env, 1, 1, 3, 6)
    Wash = Center('WashingCenter', env, 1, 1, 3, 6)
    Inspect = Center('InspectionCenter', env, 1, 5, 5, 5)

    # the schedule!
    itiner = [Drill, Wash, Inspect]

    # the first part!
    env.process(Part(env, 'Part0', itiner, log))

    # part spawn!
    num = 0
    while True:
        num += 1
        name = 'Part'+str(num)

        yield env.timeout(random.expovariate(0.2))
        # yield env.timeout(random.randint())
        # yield env.timeout(random.triangular(50, 100, 150))
        env.process(Part(env, name, itiner, log))


# defining the environment
env = simpy.Environment()

# initialize logbook
log = logbook(env)

# trigger startup process
env.process(setup(env, log))

# execute simulation!
env.run(until=480)
log.Record()
