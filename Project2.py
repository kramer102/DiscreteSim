import simpy
import numpy as np
import random
import quandl
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt

# iterations
NUMTRIALS = 2
# 20 year simulation
RUNTIME = int(365*20)
# sample from historical or future data
SAMPLE = 'h'


class user(object):
    def __init__(self, env, initial):
        self.env = env
        self.wallet = simpy.Container(env, 1000000, initial)
        self.wallethistory = []

        # interested or not in investing
        self.interest = 1

    def life(self):
        while True:
            # probability of bad event
            # 1% chance of 1 bad thing in a 5 year period

            # something weird happens every once in awhile
            trouble = random.expovariate(1/(5*365))
            if trouble < 0: trouble = 0
            yield self.env.timeout(trouble)

            # alea iacta est
            chance = random.randint(0, 100)

            # fate has smiled on you
            if chance > 50:
                bonus = np.random.normal(4000, 2000)
                yield self.wallet.put(bonus)
                # the gods shit on you
            elif chance < 50:
                cost = np.random.normal(4000, 2000)
                yield self.wallet.get(cost)

    def bills(self, rent, utilities, insurance):
        while True:
            # pay bills once a month
            yield self.env.timeout(30)

            # misc expenses
            extra = np.random.normal(300, 100)
            if extra < 0: extra = 0

            # total expenses
            expenses = rent+utilities+insurance+extra
            yield self.wallet.get(expenses)

    def income(self, wage, period):
        while True:
            # get paid once per pay period
            yield self.env.timeout(period)

            # deposit paycheck into wallet
            yield self.wallet.put(wage)


class Market(object):
    def __init__(self):
        # grab market data from quandl
        quandl.ApiConfig.api_key = 'zFCX5bmbwZvgGzHu5szi'
        snp_index = quandl.get("YAHOO/FUND_VFINX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")
        mining_eft = quandl.get("YAHOO/FUND_VGPMX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")
        total_bond = quandl.get("YAHOO/FUND_VBMFX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")

        self.snp_index = np.asarray(snp_index.Close)
        self.mining_eft = np.asarray(mining_eft.Close)
        self.total_bond = np.asarray(total_bond.Close)

        # modeled each fund as a normal distribution
        self.loc1, self.scale1 = st.norm.fit(snp_index)
        self.loc2, self.scale2 = st.norm.fit(mining_eft)
        self.loc3, self.scale3 = st.norm.fit(total_bond)

    def history(self, time, account):
        if account.name == 'mining':
            return self.mining_eft[time]
        if account.name == 'index':
            return self.snp_index[time]
        if account.name == 'bond':
            return self.total_bond[time]

    def generate(self, account):
        if account.name == 'mining':
            return np.random.normal(self.loc1, self.scale1)
        if account.name == 'index':
            return np.random.normal(self.loc2, self.scale2)
        if account.name == 'bond':
            return np.random.normal(self.loc3, self.scale3)

    def update(self, env, account):
        percentchange = 0
        # if trial is using historical data
        if SAMPLE == 'h':
            percentchange = self.history(int(env.now), account)
        # if trial is using future data
        elif SAMPLE == 'f':
            percentchange = self.generate(account)

        # calculate change
        change = percentchange*account.level

        # update balance
        if change > 0:
            yield account.put(change)
        elif change < 0:
            yield account.get(change)

        # log balance change
        account.value.append([env.now, percentchange, change, account.level])

    def run(self, env, user, accounts):
        while True:
            for i in range(len(accounts)):

                # update the worth of each account
                self.update(env, accounts[i])

            # store wallet history
            user.wallethistory.append(env.now, user.wallet.level)

            # wait until next day
            yield env.timeout(1)


class Investor(object):
    def __init__(self, env):
        self.env = env
        self.buyhistory = []
        self.sellhistory = []

    def invest(self, user, accounts):

        while True:
            # every 15 days invest money
            if np.mod(env.now, 15) == 0.0:

                # amount sert aside to invest every pay period
                amount = 0.1*user.wallet.level
                yield user.wallet.get(amount)

                # allocation strategy
                strategy = [1/3, 1/3, 1/3]

                # place investments
                for i in range(len(accounts)):

                    yield accounts[i].investment.put(int(strategy[i]*amount))
                    self.buyhistory.append([self.env.now, accounts[i].name, int(strategy[i]*amount), accounts[i].balance])

    def sell(self, user, accounts):

        while True:
            # to be replaced with a sell strategy
            criteria = 0

            if user.wallet.level == 0 | criteria:
                # total amount needed
                amount = 2000

                # in ieu of real strategy
                strategy = [1/3, 1/3, 1/3]

                # place investments
                for i in range(len(accounts)):

                    yield accounts[i].investment.get(int(strategy[i]*amount))
                    self.sellhistory.append([self.env.now, accounts[i].name, int(strategy[i]*amount), accounts[i].balance])


class Account(simpy.Container):
    def __init__(self, env, cap, init, name, buyin, buyfeerate, sellfeerate):
        simpy.Container.__init__(self, env, cap, init)
        self.env = env
        self.name = name
        self.buyin = buyin
        self.put(self.buyin)
        self.buyfeerate = buyfeerate
        self.sellfeerate = sellfeerate

        self.value = []
        self.fees = []

    def put(self, *args, **kwargs):
        amount = args[1]
        fee = self.buyfeerate*amount
        amount -= fee
        newargs = args[0], amount
        self.fees.append([self.env.now, fee, 'buy'])
        return simpy.Container.put(*newargs, **kwargs)

    def get(self, *args, **kwargs):
        amount = args[1]
        fee = self.sellfeerate*amount
        amount -= fee
        newargs = args[0], amount
        self.fees.append([self.env.now, fee, 'sell'])
        return simpy.Container.put(*newargs, **kwargs)


class logbook(object):
    def __init__(self):
        self.trial = 0
        self.buyhistory = []
        self.sellhistory = []
        self.feehistory = []
        self.valuehistory = []
        self.wallethistory = []

    def record(self, trial, investor, accounts, user):
        self.trial += 1
        self.buyhistory.append(investor.buyhistory)
        self.sellhistory.append(investor.sellhistory)
        self.wallethistory.append(user.wallethistory)

        for i in range(len(accounts)):
            self.valuehistory[i].append(accounts[i].value)
            self.feehistory[i].append(accounts[i].fees)

    def store(self, env, trial, investor, accounts, user):
        while True:
            # stores all data at the last second
            yield env.timeout(RUNTIME)
            self.record(trial, investor, accounts, user)


def setup(env, trial):
    log = logbook()

    # Jack Attack
    Jack = user(env, 1000)

    # Rich Chambers
    Rich = Investor(env)

    # investment accounts to open
    mining = Account(env, 100000, 0, 'mining', 150, 0.011, 0.008)
    index = Account(env, 100000, 0, 'index', 100, 0.016, 0.009)
    bond = Account(env, 100000, 0, 'bond', 100, 0.006, 0.012)

    accounts = [mining, index, bond]

    # market process
    env.process(market.run(env, Jack, accounts))

    # investor processes
    env.process(Rich.invest(Jack, accounts))
    env.process(Rich.sell(Jack, accounts))

    # user processes
    env.process(Jack.life())
    env.process(Jack.bills(1300, 200, 300))
    env.process(Jack.income(1500, 15))

    # prepare logbook to store data
    env.process(log.store(env, trial, Rich, accounts, Jack))

#initialize market to be used for all trials
market = Market()

# run all trials
for i in range(1, NUMTRIALS+1):

    print('\n * * * * * * Trial {0} * * * * * * \n'.format(i))

    # switches to future (generated) data for second half of trials
    if i > int(NUMTRIALS/2):
        SAMPLE = 'f'

    # defining the environment
    env = simpy.Environment()

    # trigger startup process
    env.process(setup(env, i))

    # execute simulation!
    env.run(until=RUNTIME)
    del env

# peace
