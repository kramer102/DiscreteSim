# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 15:52:14 2016

@author: kramerPro
"""
# %%
## use pip install quandl

import quandl

# my api key --> hope no-one abuses this
quandl.ApiConfig.api_key = 'zFCX5bmbwZvgGzHu5szi'

# can copy and paste commands after finding what you want on the website
# easy to get date ranges: could mix and overlap 
# help for python commands:
# https://www.quandl.com/tools/python
snp_index = quandl.get("YAHOO/FUND_VFINX", authtoken="zFCX5bmbwZvgGzHu5szi")
gold_eft = quandl.get("YAHOO/FUND_VGPMX", authtoken="zFCX5bmbwZvgGzHu5szi")
total_bond = quandl.get("YAHOO/FUND_VBMFX", authtoken="zFCX5bmbwZvgGzHu5szi")

# %%