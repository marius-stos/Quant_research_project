import yfinance as yf
import pandas as pd
import os


save_path = "/Users/mariusstos/quant_research_project/data/SPX.csv"


data = yf.download("^GSPC", start="2010-01-01", end="2019-12-31")


data.to_csv(save_path)

print(f"file save : {save_path}")