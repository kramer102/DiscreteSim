import simpy
import numpy as np
import random
import quandl
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt

# iterations
NUMTRIALS = 4
# 20 year simulation
# RUNTIME = int(365*20)
RUNTIME = 365
# sample from historical or future data
SAMPLE = 'h'
# to grab data from quandl or just import from csv
GRAB = False


class user(object):
    def __init__(self, env, initial):
        self.env = env
        self.wallet = simpy.Container(env, 1000000, initial)
        self.wallethistory = []

        self.wage = 1500

        # interested or not in investing
        self.interest = 1

        env.process(self.life())
        env.process(self.bills(1300, 200, 300))
        env.process(self.income(15))

    def life(self):
        while True:
            # probability of bad event
            # 1% chance of 1 bad thing in a 5 year period

            # something weird happens every once in awhile
            trouble = random.expovariate(0.00055)
            if trouble < 0: trouble = 0
            yield self.env.timeout(trouble)

            # alea iacta est
            chance = random.randint(0, 100)

            # fate has smiled on you
            if chance > 50:
                bonus = np.random.normal(4000, 2000)
                yield self.wallet.put(bonus)
                print('something wonderful has happened. {0}').format(bonus)
            # the gods shit on you
            elif chance < 50:
                cost = np.random.normal(4000, 2000)
                yield self.wallet.get(cost)
                print('something terrible has happened. {0}').format(cost)

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
            print('bills paid {0}').format(expenses)

    def income(self, period):
        while True:
            # get paid once per pay period
            yield self.env.timeout(period)

            # deposit paycheck into wallet
            yield self.wallet.put(self.wage)
            print('payday {0}').format(self.wage)


class Market(object):
    def __init__(self):
        print 'acquiring market data'

        if GRAB == True:
            # grab market data from quandl
            quandl.ApiConfig.api_key = 'zFCX5bmbwZvgGzHu5szi'
            snp_index = quandl.get("YAHOO/FUND_VFINX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")
            mining_eft = quandl.get("YAHOO/FUND_VGPMX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")
            total_bond = quandl.get("YAHOO/FUND_VBMFX", authtoken="zFCX5bmbwZvgGzHu5szi", transform="rdiff")
        else:
            snp_index = pd.read_csv('snp_index.csv')
            mining_eft = pd.read_csv('mining_eft.csv')
            total_bond = pd.read_csv('total_bond.csv')
            
        self.snp_index = np.asarray(snp_index.Close)
        self.mining_eft = np.asarray(mining_eft.Close)
        self.total_bond = np.asarray(total_bond.Close)

        # modeled each fund as a normal distribution
        self.loc1, self.scale1 = st.norm.fit(self.snp_index)
        self.loc2, self.scale2 = st.norm.fit(self.mining_eft)
        self.loc3, self.scale3 = st.norm.fit(self.total_bond)

        print 'market data acquired and modeled'

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

        # print account.name, account.level, change

        # update balance
        if change > 0.0:
            account.put(account, change)
        elif change < 0.0:
            change = -1*change
            account.get(account, change)

        # log balance change
        account.value.append([env.now, percentchange, change, account.level])

    def run(self, env, user, accounts):
        while True:
            print('\n- - day: {0} - -').format(env.now)

            for i in range(len(accounts)):
                # update the worth of each account
                self.update(env, accounts[i])
                print('{0} closes at balance {1}').format(accounts[i].name, accounts[i].level)

            # store wallet history
            user.wallethistory.append([env.now, user.wallet.level])
            print('>> wallet level at: {0}').format(user.wallet.level)

            # wait until next day
            yield env.timeout(1)


class Investor(object):
    def __init__(self, env, client, accounts):
        self.env = env
        # formatted as [day, account name, amount bought, total account value]
        self.buyhistory = []
        # formatted as [day, account name, amount sold, total account value]
        self.sellhistory = []

        env.process(self.invest(client, accounts))
        env.process(self.sell(client, accounts))

    def invest(self, user, accounts):

        while True:
            # every 15 days invest money

            if np.mod(env.now, 15) == 0.0:

                # amount set aside to invest every pay period
                amount = 0.1*user.wage
                yield user.wallet.get(amount)

                # allocation strategy
                strategy = [0.33, 0.33, 0.33]

                # place investments
                for i in range(len(accounts)):
                    print('{0} invested in {1}').format(int(strategy[i]*amount), accounts[i].name)
                    yield accounts[i].put(accounts[i], int(strategy[i]*amount))
                    self.buyhistory.append([self.env.now, accounts[i].name, int(strategy[i]*amount), accounts[i].level])

            yield env.timeout(1)

    def sell(self, user, accounts):

        while True:
            # to be replaced with a sell strategy
            criteria = 0

            if user.wallet.level == 0 | criteria:
                # total amount needed
                amount = 2000

                # in ieu of real strategy
                strategy = [0.33, 0.33, 0.33]

                # sell investments
                for i in range(len(accounts)):
                    print('{0} sold of {1}').format(int(strategy[i]*amount), accounts[i].name)
                    yield accounts[i].investment.get(accounts[i], int(strategy[i]*amount))
                    self.sellhistory.append([self.env.now, accounts[i].name, int(strategy[i]*amount), accounts[i].level])

                # deposit into account
                yield user.wallet.put(amount)

            yield env.timeout(1)


class Account(simpy.Container):
    def __init__(self, env, cap, init, name, buyin, buyfeerate, sellfeerate):
        simpy.Container.__init__(self, env, cap, init)
        self.env = env
        self.name = name
        self.buyin = buyin
        self.buyfeerate = buyfeerate
        self.sellfeerate = sellfeerate

        # formatted as [day, % change, $ change, total account value]
        self.value = []
        # formatted as [day, fee paid, buying/selling]
        self.fees = []

        self.put(self, self.buyin)

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

        # formatted as [trial]
        #   each item formatted as [day, account name, amount bought, total account value]
        self.buyhistory = []

        # formatted as [trial]
        #   each item formatted as [day, account name, amount sold, total account value]
        self.sellhistory = []

        # formatted as [[account fund][trial][day]]
        #   each item formatted as [day, fee paid, buying/selling]
        self.feehistory = [[],[],[]]

        # formatted as [[account fund][trial][day]]
        #   each item formatted as [day, % change, $ change, total account value]
        self.valuehistory = [[],[],[]]

        # formatted as [trial]
        #   each item formatted as [day, wallet balance]
        self.wallethistory = []

        # store the market behavior for a each trial
        self.market = []

    def record(self, trial, investor, accounts, user):
        self.trial += 1
        self.buyhistory.append(investor.buyhistory)
        self.sellhistory.append(investor.sellhistory)
        self.wallethistory.append(user.wallethistory)

        for i in range(3):
            self.valuehistory[i].append(accounts[i].value)
            self.feehistory[i].append(accounts[i].fees)

    def store(self, env, trial, investor, accounts, user):
        while True:
            # stores all data at the last second
            yield env.timeout(RUNTIME-1)
            self.record(trial, investor, accounts, user)


def graph():
    # plot wallet value over time
    wh = []
    f1, (plot1, plot2) = plt.subplots(2, sharex=True)
    plot1.set_title('Worth over Time')
    plt.xlabel('Time (days)')
    plt.ylabel('Wallet (dollars)')
    # makes wh, a list of wallet history dataframes for each trial
    for i in range(NUMTRIALS):
        # plot the wallet history over time for each trial
        wh.append(pd.DataFrame(log.wallethistory[i]).set_index(0))
        plot1.plot(wh[i])

    # plot 2 should be here and should show net worth
    f1.savefig('worth.png')
    plt.show()

    # plot comparison of value of all three accounts over time
    index_val = []
    mining_val = []
    bond_val = []
    f2, (plot1, plot2, plot3) = plt.subplots(3, sharex=True)
    plt.xlabel('Time (days)')
    plt.ylabel('Value (dollars)')
    for i in range(NUMTRIALS):
        # plot the value of the investments in the mining account
        index_val.append(pd.DataFrame(log.valuehistory[0][i]).set_index(0))
        plot1.plot(index_val[i].ix[:, 2])
        # plot the value of the investments in the index account
        mining_val.append(pd.DataFrame(log.valuehistory[1][i]).set_index(0))
        plot2.plot(mining_val[i].ix[:, 2])
        # plot the value of the investments in the bond account
        bond_val.append(pd.DataFrame(log.valuehistory[2][i]).set_index(0))
        plot3.plot(bond_val[i].ix[:, 2])
    plt.title('Investment Account Value over Time')
    f2.savefig('accountvalues.png')
    plt.show()

    sh = []
    bh = []
    # plot comparison of buying and selling of all three accounts over time
    f3, (plot1, plot2) = plt.subplots(2, sharex=True)
    plot1.set_title('Investments Sold')
    plot2.set_title('Investments Bought')
    plt.xlabel('Time (days)')
    plt.ylabel('Investments (dollars)')
    for i in range(NUMTRIALS):
        sh.append(pd.DataFrame(log.sellhistory[i], columns=['day', 'account', 'amount', 'total']))
        plot1.plot(sh[i][sh[i].account == 'index'].amount, c='red')
        plot1.plot(sh[i][sh[i].account == 'mining'].amount, c='green')
        plot1.plot(sh[i][sh[i].account == 'bond'].amount, c='blue')

        bh.append(pd.DataFrame(log.buyhistory[i], columns=['day', 'account', 'amount', 'total']))
        plot2.plot(bh[i][bh[i].account == 'index'].amount, c='red')
        plot2.plot(bh[i][bh[i].account == 'mining'].amount, c='green')
        plot2.plot(bh[i][bh[i].account == 'bond'].amount, c='blue')
    f3.savefig('buysell.png')
    plt.show()


def setup(env, trial):
    print 'setting up...\n'

    # Jack Attack
    Jack = user(env, 1000)

    # investment accounts to open
    mining = Account(env, 100000, 0, 'mining', 150, 0.011, 0.008)
    index = Account(env, 100000, 0, 'index', 100, 0.016, 0.009)
    bond = Account(env, 100000, 0, 'bond', 100, 0.006, 0.012)

    accounts = [mining, index, bond]

    for i in range(len(accounts)):
        print('{0} opening balance: {1}').format(accounts[i].name, accounts[i].level)

    # Rich Chambers (actual name of an accountant I knew)
    Rich = Investor(env, Jack, accounts)

    # initialize and prepare logbook to store data
    env.process(log.store(env, trial, Rich, accounts, Jack))

    # market process
    env.process(market.run(env, Jack, accounts))


# initialize market to be used for all trials
market = Market()

# initialize logbook
log = logbook()

# run all trials
for i in range(1, NUMTRIALS+1):

    print('\n * * * * * * Trial {0} * * * * * * \n'.format(i))

    # switches to future (generated) data for second half of trials
    if i > int(NUMTRIALS/2):
        SAMPLE = 'f'

    # defining the environment
    env = simpy.Environment()

    # trigger startup process
    setup(env, i)

    # execute simulation!
    env.run(until=RUNTIME)
    del env

graph()

print '\npeace'
