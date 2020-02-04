import streamlit as st
import pandas as pd
import numpy as np

from src.methods import evaluate_model
from src.agent import RLAgent

from src.utils import load_data, add_technical_features, show_evaluation_result, normalize
import plotly.express as px
import plotly.graph_objects as go

model_name = 'ddqn_1580836510_10'
test_stock = 'data/GOOG.csv'
window_size = 10
verbose = True


import keras.backend.tensorflow_backend as tb
tb._SYMBOLIC_SCOPE.value = True

def transaction_costs(commission, impact, trade):
  return (impact * abs(trade)) + commission

def create_trades(shares, symbol, prices, commission, impact):
  trades = pd.DataFrame(index = prices.index)
  trades[symbol] = shares
  trades['Cash'] = np.zeros(trades.shape[0])

  transaction = (shares) * -prices
  transaction_cost = transaction_costs(commission, impact, transaction)
  value = transaction - transaction_cost

  trades[symbol] = shares
  trades['Cash'] += value
  return trades[[symbol, 'Cash']]

def holdings_df(trades, start_val):
	holdings = trades.copy()
	holdings['Cash'][0] += start_val
	return holdings.cumsum()

def values_df(prices, holdings):
	holdingsAdj = holdings.drop('Cash', axis = 1)

	vals = prices * holdingsAdj
	vals['Cash'] = holdings[['Cash']]
	return vals.sum(axis = 1)

def compute_portvals(prices, trades, start_val = 100_000):
  holdings = holdings_df(trades, start_val)
  port_vals = values_df(prices, holdings)
  return port_vals

def get_portfolio_stats(port_val, daily_rf = 0, samples_per_year = 252):
  cum_return = (port_val[-1] / port_val[0]) - 1
  daily_returns = (port_val /port_val.shift(1)) - 1
  daily_returns.iloc[0] = 0
  daily_returns = daily_returns[1:]

  avg_daily_returns = daily_returns.mean()
  std_daily_returns = daily_returns.std()

  K = np.sqrt(samples_per_year)
  sharpe_ratio = K * (avg_daily_returns - daily_rf) / std_daily_returns
  return cum_return, avg_daily_returns, std_daily_returns, sharpe_ratio


def plot_trades(data, trades, symbol):
  buy_x = trades.index[trades[symbol] > 0]
  buy_y = data.price[trades[symbol] > 0]

  sell_x = trades.index[trades[symbol] < 0]
  sell_y = data.price[trades[symbol] < 0]

  fig = px.line(data, x=data.index, y='price')
  fig.add_trace(go.Scatter(
    x=buy_x,
    y=buy_y,
    mode="markers",
    marker = dict(size = 10, symbol = 5, color = 'green'),
    name="Buy",
  ))
  fig.add_trace(go.Scatter(
    x=sell_x,
    y=sell_y,
    mode="markers",
    marker = dict(size = 10, symbol = 6, color = 'red'),
    name="Sell",
  ))
  return fig

def plot_return(vals, symbol):
  fig = px.line(vals, x=vals.index, y=symbol)
  return fig


'''
TODO:
1. Push csv files to S3
2. Push models to S3
3. Plot in Plotly -> Streamlit

'''

@st.cache
def load_data_(symbol, window_size):
  data_ = add_technical_features(load_data(f'data/{symbol}.csv'), window = window_size).sort_values(by=['Date'], ascending=True)
  return data_

@st.cache
def filter_data_by_date(data, start_date, end_date):
  date_range = pd.date_range(start = start_date, end = end_date)
  return data.loc[date_range].dropna()

def load_model(state_size, model_name):
  return RLAgent(state_size = window_size, pretrained = True, model_name = model_name)

def evaluate(agent, test_data, window_size, verbose = True):
  result, history, shares = evaluate_model(agent, test_data, window_size, verbose)
  return result, history, shares

def sidebar(index):
  start_date = st.sidebar.date_input('Start', index[0])
  end_date = st.sidebar.date_input('End', index[-1])
  window_size = st.sidebar.slider('Window Size', 1, 30, 10)
  return start_date, end_date, window_size


# Streamlit App

st.title('Run Model')
st.markdown('Subheading Here')

symbols = ['AAPL', 'AMZN', 'CRM', 'FB', 'GOOG', 'JNJ', 'JPM', 'MSFT', 'NFLX', 'SPY', 'V']
symbol = st.sidebar.selectbox('Stock Symbol:', symbols)

index = load_data_(symbol, window_size).index
start_date, end_date, window_size = sidebar(index)
submit = st.sidebar.button('Run')


if submit:
  model_name = 'GOOG'
  data = load_data_(symbol, window_size)
  filtered_data = filter_data_by_date(data, start_date, end_date)
  st.write(filtered_data)

  agent = load_model(filtered_data.shape[1], model_name = model_name)
  result, history, shares = evaluate(agent, filtered_data, window_size = window_size, verbose = False)

  trades = create_trades(shares, symbol, filtered_data.price, 0, 0)
  holdings = holdings_df(trades, start_val = 100_000)
  vals = pd.DataFrame(data = values_df(filtered_data.price, holdings)).rename(columns = {0: symbol})
  st.write(vals)
  fig = plot_trades(filtered_data, trades, symbol)
  st.plotly_chart(fig)
  fig = plot_return(vals, symbol)
  st.plotly_chart(fig)


  # st.write(filtered_data)
  # trades = st.checkbox('Show Trades')




# model_name = 'model_double-dqn_GOOG_50'
#
#
# verbose = True

# test_stock = 'data/GOOG_2019.csv'
# test_data = get_stock_data(test_stock)
# window_size = 10
# agent = load_model(state_size = window_size, model_name = 'model_double-dqn_GOOG_50' )
# result, history, shares = evaluate(agent, test_data, window_size = window_size)
# chart = visualize(df, history)
# st.altair_chart(chart)

#