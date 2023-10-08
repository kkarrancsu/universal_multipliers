import streamlit as st
from datetime import date, timedelta

import numpy as np
import pandas as pd
import altair as alt

import utils
import costs

st.set_page_config(
    page_title="Fil+ Considerations",
    page_icon="🚀",  # TODO: can update this to the FIL logo
    layout="wide",
)

def run_mechafil():
    historical_data = utils.download_historical_data(start_date, current_date, end_date)
    hist_rbp = np.median(historical_data['hist_rbp'][-30:])
    hist_rr = np.median(historical_data['historical_renewal_rate'][-30:])
    hist_fpr = np.median(historical_data['historical_fpr'][-30:])
    filpfactor2info = {}
    for filp_multiply_factor in [1, 0.8, 0.5]:
        multiplier2info = utils.compute_mechafil_for_multiplier(hist_rbp, hist_rr, hist_fpr*filp_multiply_factor,
                                                                start_date, current_date, end_date)
        filpfactor2info[filp_multiply_factor] = multiplier2info
    return filpfactor2info

def plot(df):
    dff = pd.melt(df, id_vars=['multiplier'], var_name='SP Type', value_name='Profit Delta')
    ch = alt.Chart(dff).mark_bar().encode(
        x=alt.X('multiplier:O', title=None, sort=['StatusQuo', '2.5/2.5/10', '5/5/10', '5/5/20']),
        y='Profit Delta:Q',
        color=alt.Color('multiplier:N', title='Multiplier'),
        column=alt.Column('SP Type:N', title='Profit-Profit[CC]', header=alt.Header(titleFontSize=14)),
    ).properties(
        width=125,
    )
    st.altair_chart(ch.interactive())

def compute_costs():
    rbp_slope = 1.0  # hard-coded, but we can make this configurable later potentially

    filpfactor2info = run_mechafil()
    exchange_rate =  st.session_state['filprice_slider']
    borrowing_cost_pct = st.session_state['borrow_cost_pct'] / 100.0
    filp_bd_cost_tib_per_yr = st.session_state['filp_bizdev_cost']
    rd_bd_cost_tib_per_yr = 0  # a noop for this
    deal_income_tib_per_yr = st.session_state['deal_income']
    data_prep_cost_tib_per_yr = st.session_state['data_prep_cost']
    penalty_tib_per_yr = st.session_state['cheating_penalty']

    power_cost_tib_per_yr = st.session_state['power_cost']
    bw_cost_tib_per_yr = st.session_state['bw_cost']
    staff_cost_tib_per_yr = st.session_state['staff_cost']

    sensitivity = st.session_state['sensitivity_slider']

    filp_decrease = st.session_state['fpr_radio']
    if filp_decrease == '0%':
        filp_multiplier = 1.0
    elif filp_decrease == '20%':
        filp_multiplier = 0.8
    elif filp_decrease == '50%':
        filp_multiplier = 0.5
    multiplier2info = filpfactor2info[filp_multiplier]

    # multiplier2costprofile = {}
    cost_kwargs = dict(
        deal_income_tib_per_yr = deal_income_tib_per_yr,
        base_token_price=exchange_rate, 
        borrowing_cost_pct=borrowing_cost_pct,
        filp_bd_cost_tib_per_yr=filp_bd_cost_tib_per_yr, rd_bd_cost_tib_per_yr=rd_bd_cost_tib_per_yr,
        data_prep_cost_tib_per_yr=data_prep_cost_tib_per_yr, penalty_tib_per_yr=penalty_tib_per_yr,
        power_cost_tib_per_yr=power_cost_tib_per_yr, 
        bandwidth_10gbps_tib_per_yr=bw_cost_tib_per_yr, 
        staff_cost_tib_per_yr=staff_cost_tib_per_yr 
    )
    results_list = []
    for multiplier_str, info in multiplier2info.items():
        sq_return_per_sector = info['status_quo_return_per_sector']
        status_quo_locked = info['status_quo_locked']

        return_per_sector = info['scenario_return_per_sector']
        scenario_locked = info['scenario_locked']

        # get multiplier
        cc_multiplier = info['cc_multiplier']
        rd_multiplier = info['rd_multiplier']
        filp_multiplier = info['filp_multiplier']

        if multiplier_str == 'StatusQuo':
            df = costs.get_sp_profile_profit(
                sq_return_per_sector, status_quo_locked, status_quo_locked, 
                sensitivity=0,
                filp_multiplier=10, rd_multiplier=1, cc_multiplier=1,
                **cost_kwargs
            )
        else:
            df = costs.get_sp_profile_profit(
                return_per_sector, status_quo_locked, scenario_locked, 
                sensitivity=sensitivity,
                filp_multiplier=filp_multiplier, rd_multiplier=rd_multiplier, cc_multiplier=cc_multiplier,
                **cost_kwargs
            )

        # compute relative cost to CC
        filp_variants = ['FIL+', 'V1-ExploitFIL+', 'V2-ExploitFIL+', 'V3-ExploitFIL+']
        results_dict = {}
        results_dict['multiplier'] = multiplier_str
        for filp_variant in filp_variants:
            profit_cc = df[df['SP Type']=='CC']['profit'].values[0]
            profit_filp_variant = df[df['SP Type']==filp_variant]['profit'].values[0]
            profit_delta = profit_filp_variant-profit_cc
            results_dict[filp_variant] = profit_delta
        results_list.append(results_dict)
    
    results_df = pd.DataFrame(results_list)
    plot(results_df)

current_date = date.today() - timedelta(days=3)
mo_start = min(current_date.month - 1 % 12, 1)
start_date = date(current_date.year, mo_start, 1)
# # temporary
# current_date = date(2023, 9, 30) 
# start_date = date(2023, 9, 1)  # reduce locking bias by starting simulation close to current date

forecast_length_days=365*3
end_date = current_date + timedelta(days=forecast_length_days)
compute_costs_kwargs = {}

with st.sidebar:
    st.slider(
        "FIL Exchange Rate ($/FIL)", 
        min_value=3., max_value=50., value=4.0, step=.1, format='%0.02f', key="filprice_slider",
        on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
    )
    st.slider("Sensitivity", min_value=0.0, max_value=5.0, value=0.25, step=.01, key="sensitivity_slider",
              on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
    )
    st.radio("FIL+ Onboarding Percentage Decrease", ['0%', '20%', '50%'], key="fpr_radio", index=0,
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
    )
    
    with st.expander("Revenue Settings", expanded=False):
        st.slider(
            'Deal Income ($/TiB/Yr)', 
            min_value=0.0, max_value=100.0, value=16.0, step=1.0, format='%0.02f', key="deal_income",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
    with st.expander("Cost Settings", expanded=False):
        st.slider(
            'Borrowing Costs (Pct. of Pledge)', 
            min_value=0.0, max_value=100.0, value=50.0, step=1.00, format='%0.02f', key="borrow_cost_pct",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'FIL+ Biz Dev Cost ($/TiB/Yr)', 
            min_value=1.0, max_value=50.0, value=8.0, step=1.0, format='%0.02f', key="filp_bizdev_cost",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'Data Prep Cost ($/TiB/Yr)', 
            min_value=0.0, max_value=50.0, value=1.0, step=1.0, format='%0.02f', key="data_prep_cost",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'FIL+ Slashing Penalty ($/TiB/Yr)', 
            min_value=0.0, max_value=50.0, value=10.0, step=1.0, format='%0.02f', key="cheating_penalty",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'Power+COLO Cost ($/TiB/Yr)', 
            min_value=0.0, max_value=50.0, value=6.0, step=1.0, format='%0.02f', key="power_cost",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'Bandwidth [10GBPS] Cost ($/TiB/Yr)', 
            min_value=0.0, max_value=50.0, value=6.0, step=1.0, format='%0.02f', key="bw_cost",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
        st.slider(
            'Staff Cost ($/TiB/Yr)', 
            min_value=0.0, max_value=50.0, value=8.0, step=1.0, format='%0.02f', key="staff_cost",
            on_change=compute_costs, kwargs=compute_costs_kwargs, disabled=False, label_visibility="visible"
        )
    
    st.button("Compute!", on_click=compute_costs, kwargs=compute_costs_kwargs, key="forecast_button")
