# DiscreteSim
Location for models made during Spring 2016 Discrete Sim class
## Introduction
### Problem Definition and Purpose
The major question addressed in this work is the following: will a relatively simple retirement investment strategy really work given the uncertainty of markets and life events? 

While it may be easy to check if someone would have been a winner through backtesting of the market, long term individual success is dependent on more than just market forces. This work aims to study from a policy development standpoint the rate of success for individuals saving for retirement. Some policy makers have pushed for an individual savings plan instead of social security. This would put individuals in charge of their own money, but of the people who begin saving for retirement young, how many actually end up with enough money to retire? 
Experimental Design

### Problem 1 (simplest)
Given a chance (~25%) of financial disaster every 5 years and historical market data, what percent of retirement savings investors will have a positive outcome (ROI > 3%) vs a simple savings account.

### Experiment 1:
Run 10,000 trials with a runtime of 20 years. Find summary statistics on total ROI (min, max, mean, median), Plot data for the min, max, and median ROI trial. Find %trials where ROI > 3%.
Use to make a determination of whether people should save in something like a savings account or invest in funds

### Problem 2:
Given the conditions in Problem 1, the user behavior is modified to have a low probability of starting to save again after a disaster. If we were a governmental or nonprofit organization looking to have the option to opt-out of Social security for upper middle class earners, what are more realistic probabilities people would reliably save and how often would it be better than savings. I.e. what percentage of trials > forced savings(social security)  social security ROI( bad for high earners(our assumption), good for low earners) (-$118,000 need to turn into percentage). All of this considering that it is much better to have lost a little money and still have money than to have nothing.

### Experiment 2:
Same as 1, but after a major financial disaster, there is only a 5% chance the person will invest in the next time period. Success is any outcome where the ROI>social security 
### Summary of Preliminary Results
The results found so far suggest that an individual working for minimum wage over the course of 25 years is very unlikely to be able to attain a positive ROI.
