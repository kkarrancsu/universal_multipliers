import pandas as pd

def get_negligible_costs(bandwidth_10gbps_tib_per_yr):
    # Definitions (we can make these configurable later, potentially)
    sealing_costs_tib_per_yr = 1.3

    gas_cost_tib_per_yr = (2250.+108.)/1024.
    gas_cost_without_psd_tib_per_yr = 108./1024.
    bandwidth_1gbps_tib_per_yr=bandwidth_10gbps_tib_per_yr/10.0

    return sealing_costs_tib_per_yr, gas_cost_tib_per_yr, gas_cost_without_psd_tib_per_yr, bandwidth_1gbps_tib_per_yr


def compute_costs(expected_rewards_per_tib, 
                  filp_multiplier=10, rd_multiplier=1, cc_multiplier=1,
                  exchange_rate=4.0, borrowing_cost_pct=0.50,
                  filp_bd_cost_tib_per_yr=8.0, rd_bd_cost_tib_per_yr=3.2,
                  deal_income_tib_per_yr=16.0,
                  data_prep_cost_tib_per_yr=1.0, penalty_tib_per_yr=10.0,
                  power_cost_tib_per_yr=6, 
                  bandwidth_10gbps_tib_per_yr=6, 
                  staff_cost_tib_per_yr=8
                  ):
    erpt = expected_rewards_per_tib
    
    sealing_costs_tib_per_yr, gas_cost_tib_per_yr, gas_cost_without_psd_tib_per_yr, bandwidth_1gbps_tib_per_yr = get_negligible_costs(bandwidth_10gbps_tib_per_yr)
    
    # create a dataframe for each of the miner profiles
    filp_miner = {
        'SP Type': 'FIL+',
        'block_rewards': erpt*exchange_rate*filp_multiplier,
        'deal_income': deal_income_tib_per_yr,
        'pledge_cost': erpt*exchange_rate*filp_multiplier*borrowing_cost_pct,
        'gas_cost': gas_cost_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_10gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': data_prep_cost_tib_per_yr,
        'bd_cost': filp_bd_cost_tib_per_yr,
        'extra_copy_cost': (staff_cost_tib_per_yr+power_cost_tib_per_yr)*0.5,
        'cheating_cost': 0
    }
    rd_miner = {
        'SP Type': 'Regular Deal',
        'block_rewards': erpt*exchange_rate*rd_multiplier,
        'deal_income': deal_income_tib_per_yr,
        'pledge_cost': erpt*exchange_rate*rd_multiplier*borrowing_cost_pct,
        'gas_cost': gas_cost_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_10gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': data_prep_cost_tib_per_yr,
        'bd_cost': rd_bd_cost_tib_per_yr,
        'extra_copy_cost': (staff_cost_tib_per_yr+power_cost_tib_per_yr)*0.5,
        'cheating_cost': 0
    }
    filp_exploit_miner = {
        'SP Type':'V1-ExploitFIL+',
        'block_rewards': erpt*exchange_rate*filp_multiplier,
        'deal_income': 0,
        'pledge_cost': erpt*exchange_rate*filp_multiplier*borrowing_cost_pct,
        'gas_cost': gas_cost_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_1gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': 1,
        'bd_cost': 0,
        'extra_copy_cost': 0,
        'cheating_cost': 0
    }
    filp_exploit_with_retrieval = {
        'SP Type':'V2-ExploitFIL+',
        'block_rewards': erpt*exchange_rate*filp_multiplier,
        'deal_income': 0,
        'pledge_cost': erpt*exchange_rate*filp_multiplier*borrowing_cost_pct,
        'gas_cost': gas_cost_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_10gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': 1,
        'bd_cost': 0,
        'extra_copy_cost': (staff_cost_tib_per_yr*0.5+bandwidth_10gbps_tib_per_yr)*0.5,
        'cheating_cost': 0
    }
    filp_exploit_with_retrieval_and_slash = {
        'SP Type':'V3-ExploitFIL+',
        'block_rewards': erpt*exchange_rate*filp_multiplier,
        'deal_income': 0,
        'pledge_cost': erpt*exchange_rate*filp_multiplier*borrowing_cost_pct,
        'gas_cost': gas_cost_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_10gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': 1,
        'bd_cost': 0,
        'extra_copy_cost': (staff_cost_tib_per_yr*0.5+bandwidth_10gbps_tib_per_yr)*0.5,
        'cheating_cost': penalty_tib_per_yr
    }
    cc_miner = {
        'SP Type':'CC',
        'block_rewards': erpt*exchange_rate*cc_multiplier,
        'deal_income': 0,
        'pledge_cost': erpt*exchange_rate*borrowing_cost_pct*cc_multiplier,
        'gas_cost': gas_cost_without_psd_tib_per_yr,
        'power_cost': power_cost_tib_per_yr,
        'bandwidth_cost': bandwidth_1gbps_tib_per_yr,
        'staff_cost': staff_cost_tib_per_yr,
        'sealing_cost': sealing_costs_tib_per_yr,
        'data_prep_cost': 0,
        'bd_cost': 0,
        'extra_copy_cost': 0,
        'cheating_cost': 0
    }
    df = pd.DataFrame([filp_miner, rd_miner, filp_exploit_miner, filp_exploit_with_retrieval, filp_exploit_with_retrieval_and_slash, cc_miner])
    # add final accounting to the DF
    revenue = df['block_rewards'] + df['deal_income']
    cost = (
        df['pledge_cost'] 
        + df['gas_cost'] 
        + df['power_cost'] 
        + df['bandwidth_cost'] 
        + df['staff_cost'] 
        + df['sealing_cost'] 
        + df['data_prep_cost'] 
        + df['bd_cost'] 
        + df['extra_copy_cost'] 
        + df['cheating_cost']
    )
    df['revenue'] = revenue
    df['cost'] = cost
    df['profit'] = revenue-cost
    
    return df



def get_sp_profile_profit(
    return_per_sector, status_quo_locked, scenario_locked, 
    deal_income_tib_per_yr = 30,
    base_token_price=4, sensitivity=0.5,
    filp_multiplier=10, rd_multiplier=1, cc_multiplier=1,
    borrowing_cost_pct=0.50,
    filp_bd_cost_tib_per_yr=8.0, rd_bd_cost_tib_per_yr=3.2,
    data_prep_cost_tib_per_yr=1.0, penalty_tib_per_yr=10.0,
    power_cost_tib_per_yr=6, 
    bandwidth_10gbps_tib_per_yr=6, 
    staff_cost_tib_per_yr=8
):
    GIB = 2 ** 30
    SECTOR_SIZE = 32 * GIB

    scale = (1024**4)/SECTOR_SIZE  # convert to PiBs
    locked_ratio = scenario_locked / status_quo_locked
    expected_return_per_tib = return_per_sector * scale
    exchange_rate = base_token_price * (1 + locked_ratio * sensitivity)
    profit_df = compute_costs(
        expected_return_per_tib,
        filp_multiplier=filp_multiplier, 
        rd_multiplier=rd_multiplier, 
        cc_multiplier=cc_multiplier,
        deal_income_tib_per_yr = deal_income_tib_per_yr,
        exchange_rate=exchange_rate, 
        borrowing_cost_pct=borrowing_cost_pct,
        filp_bd_cost_tib_per_yr=filp_bd_cost_tib_per_yr, 
        rd_bd_cost_tib_per_yr=rd_bd_cost_tib_per_yr,
        data_prep_cost_tib_per_yr=data_prep_cost_tib_per_yr, 
        penalty_tib_per_yr=penalty_tib_per_yr,
        power_cost_tib_per_yr=power_cost_tib_per_yr, 
        bandwidth_10gbps_tib_per_yr=bandwidth_10gbps_tib_per_yr, 
        staff_cost_tib_per_yr=staff_cost_tib_per_yr
    )
    
    return profit_df
    # return df.groupby('SP Type')