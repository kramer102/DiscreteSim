import simpy
import numpy as np
import random
import quandl
import pandas as pd
import scipy.stats as st
import matplotlib.pyplot as plt

# notes for tonight:
#   - get all dataframes together
#   - functions for higher level variables (ROI, etc)
#   - reformat plotting function

# then, verification

# next steps:
#   - reformat allocation strategy & selling strategy
#   - add meaningful selling criteria
#   - account for only taking actions on trading days (sample from less days)
#   - add functionality for getting raises
#   - add encompassing structure for testing different criteria/strategies
#       -metaparameters: sell strat, buy strat, sell crit, buy crit, life events, initial conditions
#   - make a function for calculating population metrics over set of all trials

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

        # trims the sparse data portion at beginning of mining_eft
        self.mining_eft = self.mining_eft[150:]
        self.snp_index = self.snp_index[150:]
        self.total_bond = self.total_bond[150:]

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
        # formatted as [day, account name, amount bought, total account]
        self.buyhistory = []
        # formatted as [day, account name, amount sold, total account]
        self.sellhistory = []
        # begin the processes for buying & selling assets
        env.process(self.invest(client, accounts))
        env.process(self.sell(client, accounts))

    def invest(self, user, accounts):
        while True:
            # every 15 days invest money
            # the '+1' is so that you buy on the same day as your paycheck
            if np.mod(env.now+1, 15) == 0.0:
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
            criteria = 0    # to be replaced with a sell strategy......
            if user.wallet.level == 0 | criteria:
                # total amount needed
                amount = 2000

                # in lieu of real strategy
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
        # some amount subtracted off the top for buying fees
        amount = args[1]
        fee = self.buyfeerate*amount
        amount -= fee
        newargs = args[0], amount
        self.fees.append([self.env.now, fee, 'buy'])
        return simpy.Container.put(*newargs, **kwargs)

    def get(self, *args, **kwargs):
        # some amount subtracted off the top for selling fees
        amount = args[1]
        fee = self.sellfeerate*amount
        amount -= fee
        newargs = args[0], amount
        self.fees.append([self.env.now, fee, 'sell'])
        return simpy.Container.put(*newargs, **kwargs)


class logbook(object):
    def __init__(self):
        # the current trial
        self.trial = 0

        # the market window for the current trial
        self.market_start = 0
        self.market_stop = 0

        # formatted as [trial]
        #   investments bought in each account: [day, bought $]
        self.mining_bought = []
        self.index_bought = []
        self.bond_bought = []

        # formatted as [trial]
        #   investments sold in each account: [day, sold $]
        self.mining_sold = []
        self.index_sold = []
        self.bond_sold = []

        # formatted as [trial]
        #   total amount in each account: [day, amount $]
        self.mining_amount = []
        self.index_amount = []
        self.bond_amount = []

        # formatted as [trial]
        #   amount of fees for both bought and sold transactions: [day, fee $]
        self.mining_fees = []
        self.index_fees = []
        self.bond_fees = []

        # formatted as [trial]
        #   store the market behavior for a each trial: [day, asset value]
        self.mining_market = []
        self.index_market = []
        self.bond_market = []

        # formatted as [trial]
        #   wallet balance over trial duration: [day, wallet $]
        self.wallet_history = []
        self.net_worth = []

        # formatted as [trial]
        #   return on Investment for accounts: [day, ROI]
        self.mining_ROI = []
        self.index_ROI = []
        self.bond_ROI = []

        # formatted as [trial]
        #   'trend' for accounts (accumulators): [day, value]
        self.mining_trend = []
        self.index_trend = []
        self.bond_trend = []

    def record(self, investor, accounts, user):
        # records all data from trial and stores in dataframes of more simple structure
        # ie. each metric has a corresponding dataframe object in its list for each trial

        self.wallet_history.append(pd.DataFrame(user.wallethistory, columns=['Day', 'Amount']).set_index('Day'))

        # market performance
        self.mining_market.append(pd.Series(market.mining_eft[self.market_start:self.market_stop]))
        self.index_market.append(pd.Series(market.snp_index[self.market_start:self.market_stop]))
        self.bond_market.append(pd.Series(market.total_bond[self.market_start:self.market_stop]))

        # total account value
        col = ['Day', 'PercentChange', 'AmountChange', 'Value']
        self.mining_amount.append(pd.DataFrame(accounts[0].value, columns=col).set_index('Day').Value)
        self.index_amount.append(pd.DataFrame(accounts[1].value, columns=col).set_index('Day').Value)
        self.bond_amount.append(pd.DataFrame(accounts[2].value, columns=col).set_index('Day').Value)

        # account investments fees
        col = ['Day', 'FeeAmount', 'FeeType']
        self.mining_fees.append(pd.DataFrame(accounts[0].fees, columns=col).set_index('Day').FeeAmount)
        self.index_fees.append(pd.DataFrame(accounts[1].fees, columns=col).set_index('Day').FeeAmount)
        self.bond_fees.append(pd.DataFrame(accounts[2].fees, columns=col).set_index('Day').FeeAmount)

        # convert stored data to dataframe for access
        col = ['Day', 'Account', 'AmountBought', 'AccountTotal']
        bh = pd.DataFrame(investor.buyhistory, columns=col).set_index('Day')

        col = ['Day', 'Account', 'AmountSold', 'AccountTotal']
        sh = pd.DataFrame(investor.sellhistory, columns=col).set_index('Day')

        # account investments bought
        self.mining_bought.append(bh[bh.Account == 'mining'].AmountBought)
        self.index_bought.append(bh[bh.Account == 'index'].AmountBought)
        self.bond_bought.append(bh[bh.Account == 'bond'].AmountBought)

        # account investments sold
        self.mining_sold.append(sh[sh.Account == 'mining'].AmountSold)
        self.index_sold.append(sh[sh.Account == 'index'].AmountSold)
        self.bond_sold.append(sh[sh.Account == 'bond'].AmountSold)

        # calculate Trend
        self.mining_trend.append(self.AccountTrend(self.mining_market[self.trial]))
        self.index_trend.append(self.AccountTrend(self.index_market[self.trial]))
        self.bond_trend.append(self.AccountTrend(self.bond_market[self.trial]))

        # calculate ROI
        # self.mining_ROI.append(self.ROI(self.mining_amount[self.trial], self.mining_bought[self.trial]))
        # self.index_ROI.append(self.ROI(self.index_amount[self.trial], self.index_bought[self.trial]))
        # self.bond_ROI.append(self.ROI(self.bond_amount[self.trial], self.bond_bought[self.trial]))

        # calculate Net Worth
        self.net_worth.append(self.NetWorth(self.wallet_history[self.trial], self.mining_amount[self.trial],
                                            self.index_amount[self.trial], self.bond_amount[self.trial]))

        self.trial += 1
        print('Logbook Recorded for Trial {0}').format(self.trial)

    def store(self, env, investor, accounts, user):
        while True:
            # stores all data at the last second
            yield env.timeout(RUNTIME-1)
            self.record(investor, accounts, user)

    def AccountTrend(self, account):
        # calculates the cumulative change in market value at each point in present trial
        trend = np.empty((len(account), 2))
        trend[:, 0] = np.arange(1, len(account)+1)
        for i in range(len(account)):
            trend[i, 1] = np.sum(account[:i])
        return pd.DataFrame(trend, columns=['Day', 'Value']).set_index('Day')

    def ROI(self, value, bought):
        # calculates the ROI at each time point in present trial
        # won't work yet because bought & value have different time base...........
        ROI = np.empty((len(value), 2))
        ROI[:, 0] = np.arange(1, len(value)+1)
        for i in range(len(bought)):
            ROI[i, 1] = (value.iloc[i]*bought.iloc[:i].sum()-bought.iloc[:i].sum())/bought.iloc[:i].sum()
        return pd.DataFrame(ROI, columns=['Day', 'Value']).set_index('Day')

    def NetWorth(self, wallet, mining, index, bond):
        # calculates the net worth at each time point in present trial
        nw = np.empty((len(wallet), 2))
        nw[:, 0] = np.arange(1, len(wallet)+1)
        for i in range(len(wallet)):
            nw[i, 1] = wallet.iloc[i]+mining.iloc[i]+index.iloc[i]+bond.iloc[i]
        return pd.DataFrame(nw, columns=['Day', 'Value']).set_index('Day')


def graph(trial):
    # plots some relevant plots for one trial

    # plot wallet & net value over time
    f1, (plot1, plot2) = plt.subplots(2, sharex=True)
    plot1.set_title('Worth over Time')
    plt.xlabel('Time (days)')
    plt.ylabel('Wallet (dollars)')
    plot1.plot(log.wallet_history[trial])
    plot2.plot(log.net_worth[trial])
    f1.savefig('worth.png')
    plt.show()

    # plot comparison of value of all three accounts over time
    f2, (plot1, plot2, plot3) = plt.subplots(3, sharex=True)
    plt.xlabel('Time (days)')
    plt.ylabel('Value (dollars)')
    # plot the value of the investments in the mining account
    plot1.plot(log.mining_amount[trial])
    # plot the value of the investments in the index account
    plot2.plot(log.index_amount[trial])
    # plot the value of the investments in the bond account
    plot3.plot(log.bond_amount[trial])
    plt.title('Investment Account Value over Time')
    f2.savefig('accountvalues.png')
    plt.show()

    # plot comparison of buying and selling of all three accounts over time
    f3, (plot1, plot2) = plt.subplots(2, sharex=True)
    plot1.set_title('Investments Sold')
    plot2.set_title('Investments Bought')
    plt.xlabel('Time (days)')
    plt.ylabel('Investments (dollars)')
    try:
        plot1.plot(log.mining_sold[trial], c='red')
        plot1.plot(log.index_sold[trial], c='green')
        plot1.plot(log.bond_sold[trial], c='blue')
    except ZeroDivisionError:   # i.e. no sales logged
        pass
    try:
        plot2.plot(log.mining_bought[trial], c='red')
        plot2.plot(log.index_bought[trial], c='green')
        plot2.plot(log.bond_bought[trial], c='blue')
    except ZeroDivisionError:   # i.e. no purchases logged
        pass
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
    env.process(log.store(env, Rich, accounts, Jack))

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

    if SAMPLE == 'f':
        log.market_start = np.random.randint(0, len(market.mining_eft)-RUNTIME)
        log.market_stop = log.market_start+RUNTIME
    elif SAMPLE == 'h':
        log.market_start = 0
        log.market_stop = RUNTIME

    # defining the environment
    env = simpy.Environment()

    # trigger startup process
    setup(env, i)

    # execute simulation!
    env.run(until=RUNTIME)
    del env

graph(0)

print '\npeace'
