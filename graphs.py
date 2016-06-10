wh = []
for i in range(NUMTRIALS):
    wh.append(pd.DataFrame(log.wallethistory[i]).set_index(0))
    plt.plot(wh[i])
plt.show()

# plot comparison of value of all three accounts over time
index_val = []
mining_val = []
bond_val = []
f2, (plot1, plot2, plot3) = plt.subplots(3, sharex=True)
for i in range(NUMTRIALS):

    index_val.append(pd.DataFrame(log.valuehistory[0][i]).set_index(0))
    plot1.plot(index_val[i].ix[:, 2])

    # set of
    mining_val.append(pd.DataFrame(log.valuehistory[1][i]).set_index(0))
    plot2.plot(mining_val[i].ix[:, 2])

    # set of
    bond_val.append(pd.DataFrame(log.valuehistory[2][i]).set_index(0))
    plot3.plot(bond_val[i].ix[:, 2])
f2.show()

sh = []
bh = []
# plot comparison of buying and selling of all three accounts over time
f3, (plot1, plot2) = plt.subplots(2, sharex=True)
for i in range(NUMTRIALS):
    sh.append(pd.DataFrame(log.wallethistory[i]).set_index(0))
    plot1.plot(wh[i])

    bh.append(pd.DataFrame(log.buyhistory[i]).set_index(0))
    plot2.plot(bh[i])

f3.show()