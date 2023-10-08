import streamlit as st
import scenario_generator.utils as u
from datetime import date, timedelta

import numpy as np
import pandas as pd

from mechafil.data import get_historical_network_stats, get_sector_expiration_stats, setup_spacescope, get_vested_amount
from mechafil.minting import compute_baseline_power_array, get_cum_capped_rb_power
from mechafil.power import forecast_power_stats, build_full_power_stats_df
from mechafil.vesting import compute_vesting_trajectory_df
from mechafil.minting import compute_minting_trajectory_df, \
    network_time, cum_baseline_reward, compute_baseline_power_array, \
    get_cum_capped_rb_power
from mechafil.supply import forecast_circulating_supply_df

import pystarboard.data as psd

import costs

PUBLIC_AUTH_TOKEN='Bearer ghp_EviOPunZooyAagPPmftIsHfWarumaFOUdBUZ'

@st.cache_data
def download_historical_data(start_date, current_date, end_date):
    psd.setup_spacescope(PUBLIC_AUTH_TOKEN)
    setup_spacescope(PUBLIC_AUTH_TOKEN)

    t_hist_rbp, hist_rbp = u.get_historical_daily_onboarded_power(start_date, current_date)
    t_hist_rr, hist_rr = u.get_historical_renewal_rate(start_date, current_date)
    t_hist_fpr, hist_fpr = u.get_historical_filplus_rate(start_date, current_date)

    fil_stats_df = get_historical_network_stats(start_date,current_date,end_date)
    sector_expiration_stats_offline = get_sector_expiration_stats(start_date, current_date,end_date)
    
    network_baseline = compute_baseline_power_array(start_date, end_date)
    zero_cum_capped_power = get_cum_capped_rb_power(start_date)

    start_vest_amt = get_vested_amount(start_date)

    dict_out = {
        't_rbp': t_hist_rbp,
        'hist_rbp': hist_rbp,
        't_rr': t_hist_rr,
        'historical_renewal_rate': hist_rr,
        't_fpr': t_hist_fpr,
        'historical_fpr': hist_fpr,
        'fil_stats_df': fil_stats_df,
        'sector_expiration_stats_offline': sector_expiration_stats_offline,
        'network_baseline': network_baseline,
        'zero_cum_capped_power': zero_cum_capped_power,
        'start_vest_amt': start_vest_amt
    }
    
    return dict_out

# # temporary
# def download_historical_data(start_date, current_date, end_date):
#     import pickle
#     with open('/Users/kiran/Documents/universal_multipliers/offline_info/download_historical_data.pkl', 'rb') as f:
#         dict_out = pickle.load(f)
#     return dict_out

# add ROI to trajectory
def add_generated_quantities(cil_rbp, duration=365)->pd.DataFrame:
    GIB = 2 ** 30
    SECTOR_SIZE = 32 * GIB

    # add ROI to trajectory df
#     df['day_pledge_per_QAP'] = SECTOR_SIZE * df['day_locked_pledge'] / (df['day_onboarded_power_QAP'] + df['day_renewed_power_QAP'])
    cil_rbp['day_pledge_per_QAP'] = SECTOR_SIZE * (cil_rbp['day_locked_pledge']-cil_rbp['day_renewed_pledge'])/(cil_rbp['day_onboarded_power_QAP'])
    cil_rbp['day_rewards_per_sector'] = SECTOR_SIZE * cil_rbp.day_network_reward / cil_rbp.network_QAP
    cil_rbp['1y_return_per_sector'] = cil_rbp['day_rewards_per_sector'].rolling(365).sum().shift(-365+1).values.flatten()
    cil_rbp['1y_sector_roi'] = cil_rbp['1y_return_per_sector'] / cil_rbp['day_pledge_per_QAP']

    duration_yr = duration/365
    cil_rbp['duration_return_per_sector'] = cil_rbp['day_rewards_per_sector'].rolling(duration).sum().shift(-duration+1).values.flatten()
    cil_rbp['duration_sector_roi'] = cil_rbp['duration_return_per_sector'] / cil_rbp['day_pledge_per_QAP']
    cil_rbp['duration_roi_annualized'] = np.power(cil_rbp['duration_sector_roi'] + 1, 1/duration_yr) - 1
    return cil_rbp

def clip_all_powers(df_in):
    """
    'onboarded_power', 'cum_onboarded_power',
    'expire_scheduled_power', 'cum_expire_scheduled_power', 'renewed_power',
    'cum_renewed_power', 'total_power', 'power_type', 'total_qa_power_eib'
    """
    df_out = df_in.copy()
    for c in df_out.columns:
        if 'power' in c and c != 'power_type':
#             df_out[c] = df_out[c].clip(lower=1e-4)
            df_out[c] = df_out[c].clip(lower=0)
    return df_out



def run_mechafil(
    rb_onboard_power_pred_IN, 
    renewal_rate_vec_pred_IN, 
    fil_plus_rate_pred_IN,
    duration=365, 
    cc_multiplier_fn = None,
    cc_multiplier_fn_kwargs = None,
    filp_multiplier_fn = None,
    filp_multiplier_fn_kwargs = None,
    qap_mode='basic', 
    intervention_config={},
    forecast_length=365*2,
    start_date=None,
    current_date=None,
    end_date=None,
):
    # get historical data
    historical_data_dict = download_historical_data(start_date=start_date, current_date=current_date, end_date=end_date)
    fpr_hist_info=(historical_data_dict['t_fpr'], historical_data_dict['historical_fpr'])
    fil_stats_df = historical_data_dict['fil_stats_df']
    sector_expiration_stats = historical_data_dict['sector_expiration_stats_offline']
    historical_renewal_rate = historical_data_dict['historical_renewal_rate']
    network_baseline = historical_data_dict['network_baseline']
    zero_cum_capped_power = historical_data_dict['zero_cum_capped_power']
    
    # api for power-forecasting and circ-supply are slightly different
    renewal_rate_vec_IN = np.concatenate([historical_renewal_rate, renewal_rate_vec_pred_IN])    

    res = sector_expiration_stats
    rb_known_scheduled_expire_vec = res[0]
    qa_known_scheduled_expire_vec = res[1]
    known_scheduled_pledge_release_full_vec = res[2]
    
    current_day_stats = fil_stats_df.iloc[-1]
    
    rb_power_zero = current_day_stats["total_raw_power_eib"] * 1024.0
    qa_power_zero = current_day_stats["total_qa_power_eib"] * 1024.0

    rb_power_df, qa_power_df = forecast_power_stats(
        rb_power_zero,
        qa_power_zero,
        rb_onboard_power_pred_IN,
        rb_known_scheduled_expire_vec,
        qa_known_scheduled_expire_vec,
        renewal_rate_vec_IN[-int(forecast_length):],
        fil_plus_rate_pred_IN,
        duration,
        forecast_length,
        fil_plus_m = 10,
        cc_multiplier_fn = cc_multiplier_fn,
        cc_multiplier_fn_kwargs = cc_multiplier_fn_kwargs,
        filp_multiplier_fn = filp_multiplier_fn,
        filp_multiplier_fn_kwargs = filp_multiplier_fn_kwargs,
        qap_method=qap_mode,
        intervention_config=intervention_config,
        fpr_hist_info=fpr_hist_info
    )

    ########## BUG FIX
    rb_power_df = clip_all_powers(rb_power_df)
    qa_power_df = clip_all_powers(qa_power_df)
    ##########
    rb_power_df["total_raw_power_eib"] = rb_power_df["total_power"]/1024.0
    qa_power_df["total_qa_power_eib"] = qa_power_df["total_power"]/1024.0
        
    power_df = build_full_power_stats_df(
        fil_stats_df,
        rb_power_df,
        qa_power_df,
        start_date,
        current_date,
        end_date,
    )
    
    rb_total_power_eib = power_df["total_raw_power_eib"].values
    qa_total_power_eib = power_df["total_qa_power_eib"].values
    qa_day_onboarded_power_pib = power_df["day_onboarded_qa_power_pib"].values
    qa_day_renewed_power_pib = power_df["day_renewed_qa_power_pib"].values

    vest_df = compute_vesting_trajectory_df(start_date, end_date, start_vest_amt=historical_data_dict['start_vest_amt'])
    
    mint_df_rbpbase = compute_minting_trajectory_df(
        start_date,
        end_date,
        rb_total_power_eib,
        qa_total_power_eib,
        qa_day_onboarded_power_pib,
        qa_day_renewed_power_pib,
        minting_base = 'rbp',
        baseline_power_array = network_baseline,
        zero_cum_capped_power = zero_cum_capped_power
    )
    
    start_day_stats = fil_stats_df.iloc[0]
    circ_supply_zero = start_day_stats["circulating_fil"]
    locked_fil_zero = start_day_stats["locked_fil"]
    burnt_fil_zero = start_day_stats["burnt_fil"]
    daily_burnt_fil = fil_stats_df["burnt_fil"].diff().mean()
    burnt_fil_vec = fil_stats_df["burnt_fil"].values

    cil_df_rbp = forecast_circulating_supply_df(
        start_date,
        current_date,
        end_date,
        circ_supply_zero,
        locked_fil_zero,
        daily_burnt_fil,
        duration,
        renewal_rate_vec_IN,
        burnt_fil_vec,
        vest_df,
        mint_df_rbpbase,
        known_scheduled_pledge_release_full_vec,
        fil_plus_rate=fil_plus_rate_pred_IN,
        intervention_config=intervention_config,
        fpr_hist_info=fpr_hist_info,
    )
    
    rbp_roi = add_generated_quantities(cil_df_rbp, duration=duration)
    return rbp_roi

# note that the input is *ADDITIONAL* multiplier on top of the 1x/10x - which is the current protocol
def const_2_5(): return 2.5
def const_5(): return 5
def const_1(): return 1
def const_2(): return 2

def name2simkwargs(name, current_date):
    intervention_date = current_date + timedelta(days=90)
    intervention_offset = 90
    num_days_shock_behavior = 360
    avg_sector_duration = 360
    cc_reonboard_time_days = 1
    cc_reonboard_delay_days = 1  #noop for all sector variants

    qap_mode = 'tunable'

    if name == 'StatusQuo':
        return {
            'duration': avg_sector_duration, 
            'cc_multiplier_fn': const_1,  # ==> RBP = 1x
            'cc_multiplier_fn_kwargs': {},
            'filp_multiplier_fn': const_1,  # ==> QAP ==> 10x
            'filp_multiplier_fn_kwargs': {},
            'qap_mode':qap_mode,
            'intervention_config': {
                'type': 'noop',
                'num_days_shock_behavior': num_days_shock_behavior,
                'intervention_date': intervention_date,
                'cc_reonboard_time_days': cc_reonboard_time_days,
                'cc_reonboard_delay_days': cc_reonboard_delay_days,
                'simulation_start_date': current_date + timedelta(days=1),
                'update_onboard_power_multiplier_before_intervention': False,
                'update_onboard_power_multiplier_after_intervention': False,
                'update_renew_power_multiplier_before_intervention': False,
                'update_renew_power_multiplier_after_intervention': False
            }
        }
    elif name == '2.5/2.5/10':
        return {
                'duration': avg_sector_duration, 
                'cc_multiplier_fn': const_2_5,    # Implies CC/RD = 2.5x
                'cc_multiplier_fn_kwargs': {},
                'filp_multiplier_fn': const_1,  # implies FILP = 10x
                'filp_multiplier_fn_kwargs': {},
                'qap_mode':qap_mode,
                'intervention_config': {
                    'type': 'noop',
                    'num_days_shock_behavior': num_days_shock_behavior,
                    'intervention_date': intervention_date,
                    'cc_reonboard_time_days': cc_reonboard_time_days,
                    'cc_reonboard_delay_days': cc_reonboard_delay_days,
                    'simulation_start_date': current_date + timedelta(days=1),
                    'update_onboard_power_multiplier_before_intervention': False,
                    'update_onboard_power_multiplier_after_intervention': True,
                    'update_renew_power_multiplier_before_intervention': False,
                    'update_renew_power_multiplier_after_intervention': True
              }
          }
    elif name == '5/5/10':
        return {
                'duration': avg_sector_duration, 
                'cc_multiplier_fn': const_5,    # Implies CC/RD = 5x
                'cc_multiplier_fn_kwargs': {},
                'filp_multiplier_fn': const_1,  # implies FILP = 10x
                'filp_multiplier_fn_kwargs': {},
                'qap_mode':qap_mode,
                'intervention_config': {
                    'type': 'noop',
                    'num_days_shock_behavior': num_days_shock_behavior,
                    'intervention_date': intervention_date,
                    'cc_reonboard_time_days': cc_reonboard_time_days,
                    'cc_reonboard_delay_days': cc_reonboard_delay_days,
                    'simulation_start_date': current_date + timedelta(days=1),
                    'update_onboard_power_multiplier_before_intervention': False,
                    'update_onboard_power_multiplier_after_intervention': True,
                    'update_renew_power_multiplier_before_intervention': False,
                    'update_renew_power_multiplier_after_intervention': True
              }
          }
    elif name == '5/5/20':
        return {
                'duration': avg_sector_duration, 
                'cc_multiplier_fn': const_5,    # Implies CC/RD = 5x
                'cc_multiplier_fn_kwargs': {},
                'filp_multiplier_fn': const_2,  # implies FILP = 20x
                'filp_multiplier_fn_kwargs': {},
                'qap_mode':qap_mode,
                'intervention_config': {
                    'type': 'noop',
                    'num_days_shock_behavior': num_days_shock_behavior,
                    'intervention_date': intervention_date,
                    'cc_reonboard_time_days': cc_reonboard_time_days,
                    'cc_reonboard_delay_days': cc_reonboard_delay_days,
                    'simulation_start_date': current_date + timedelta(days=1),
                    'update_onboard_power_multiplier_before_intervention': False,
                    'update_onboard_power_multiplier_after_intervention': True,
                    'update_renew_power_multiplier_before_intervention': False,
                    'update_renew_power_multiplier_after_intervention': True
              }
          }


@st.cache_data
def compute_mechafil_for_multiplier(rbp, rr, fpr, start_date, current_date, end_date):
    multipliers = ['StatusQuo', '2.5/2.5/10', '5/5/10', '5/5/20']
    multiplier_values = [(1,10), (2.5, 10), (5, 10), (5, 20)]
    multiplier2info = {}

    # TODO: have the FIL+ sensitivity parameter also
    forecast_length_days = (end_date-current_date).days
    rbp_vec = np.ones(forecast_length_days)*rbp
    rr_vec = np.ones(forecast_length_days)*rr
    fpr_vec = np.ones(forecast_length_days)*fpr

    with st.spinner("Running Digital Twin..."):
        # run status-quo simulation
        sim_kwargs = name2simkwargs('StatusQuo', current_date)
        status_quo_df = run_mechafil(
            rbp_vec, 
            rr_vec, 
            fpr_vec,
            duration=sim_kwargs['duration'], 
            cc_multiplier_fn = sim_kwargs['cc_multiplier_fn'],
            cc_multiplier_fn_kwargs = sim_kwargs['cc_multiplier_fn_kwargs'],
            filp_multiplier_fn = sim_kwargs['filp_multiplier_fn'],
            filp_multiplier_fn_kwargs = sim_kwargs['filp_multiplier_fn_kwargs'],
            qap_mode=sim_kwargs['qap_mode'], 
            intervention_config=sim_kwargs['intervention_config'],
            forecast_length=forecast_length_days,
            start_date=start_date,
            current_date=current_date,
            end_date=end_date,
        )

        for ii, multiplier in enumerate(multipliers):
            sim_kwargs = name2simkwargs(multiplier, current_date)
            scenario_df = run_mechafil(
                rbp_vec, 
                rr_vec, 
                fpr_vec,
                duration=sim_kwargs['duration'], 
                cc_multiplier_fn = sim_kwargs['cc_multiplier_fn'],
                cc_multiplier_fn_kwargs = sim_kwargs['cc_multiplier_fn_kwargs'],
                filp_multiplier_fn = sim_kwargs['filp_multiplier_fn'],
                filp_multiplier_fn_kwargs = sim_kwargs['filp_multiplier_fn_kwargs'],
                qap_mode=sim_kwargs['qap_mode'], 
                intervention_config=sim_kwargs['intervention_config'],
                forecast_length=forecast_length_days,
                start_date=start_date,
                current_date=current_date,
                end_date=end_date,
            )
            offset = (current_date-start_date).days
            multiplier_value = multiplier_values[ii]
            info_dict = {
                'status_quo_locked': status_quo_df['network_locked'][offset],
                'status_quo_return_per_sector': status_quo_df['1y_return_per_sector'][offset],
                
                'scenario_return_per_sector': scenario_df['1y_return_per_sector'][offset],
                'scenario_locked': scenario_df['network_locked'][offset],

                'cc_multiplier': multiplier_value[0],
                'rd_multiplier': multiplier_value[0],
                'filp_multiplier': multiplier_value[1],
            }
            multiplier2info[multiplier] = info_dict

    return multiplier2info
