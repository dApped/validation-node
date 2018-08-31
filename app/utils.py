import config
import time

from web3 import HTTPProvider, Web3

import common

provider = config.ETH_RPC_PROVIDER
web3 = Web3(HTTPProvider(provider))


def contract_constructor_abi(join_after_x_min=15, close_join_after_x_min=15):
    ttj_start = int(time.time()) + join_after_x_min*60
    print(ttj_start)
    ttj_end = ttj_start + close_join_after_x_min*60
    print(ttj_end)

    abi_encoded = common.pad_hex(web3.toHex(ttj_start), 32) +\
            common.pad_hex(web3.toHex(ttj_end), 32)

    return abi_encoded

