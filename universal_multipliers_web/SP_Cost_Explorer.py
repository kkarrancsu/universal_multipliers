import streamlit as st

st.set_page_config(
    page_title="Introduction",
    page_icon="👋",
    layout="wide",
)

st.markdown("[![CryptoEconLab](./app/static/cover.png)](https://cryptoeconlab.io)")

st.sidebar.success("Select a Page above.")

st.markdown(
    """
    ### Universal Multipliers
This application explores the effect of universal multipliers on the Filecoin economy. Specifically, the calculator computes the difference in `FiatROI` between CC miners and variants of Fil+ miners.
`FiatROI = NetIncome[Fil+ Variant] - NetIncome[CC]`. From an incentives perspective, this metric captures the difference in the profitability of Fil+ miners and CC miners. If the difference in profitability 
is reduced from the StatusQuo multiplier schedule (i.e. Fil+ = 10, CC = 1, RD = 1), then there is a reduced incentive to onboard Fil+ data, and consequently a reduced incentive
to employ mechansisms that exploit Fil+.

For more details, please refer to the associated [report]() and [Medium blog post]().

### Cost Computation
In the charts for both calculators, `net_income = revenue - costs`. The following table outlines all of the revenue and cost sources.  While most cost sources are adjustable via slider bar widgets, some are fixed due to their negligible impact on the overall cost.

Note that all revenue and costs are in units of $/TiB/Yr. 

|Revenue ($/TiB/Yr) |Fixed Costs ($/TiB/Yr)| Adjustable Costs ($/TiB/Yr)
|--|--|--|
|Block Rewards  |Sealing ($1.30) | Power Cost
|Deal Revenue  | Gas Cost w/ PSD ($2.30) | Bandwidth Cost
| | Gas Cost w/out PSD ($0.10) | Staff Cost
| | | Pledge (% of Block Rewards)
| | | Data Prep
| | | FIL+ BizDev
| | | Storing Extra Copy


### How to use this app

**👈 Select an App from the sidebar** to get started

### Want to learn more?
- Check out [CryptoEconLab](https://cryptoeconlab.io)

- Engage with us on [X](https://x.com/cryptoeconlab)

- Read more of our research on [Medium](https://medium.com/cryptoeconlab) and [HackMD](https://hackmd.io/@cryptoecon/almanac/)

### Disclaimer
CryptoEconLab designed this application for informational purposes only. CryptoEconLab does not provide legal, tax, financial or investment advice. No party should act in reliance upon, or with the expectation of, any such advice.
"""
)