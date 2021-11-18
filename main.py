from defilib.APIClients.EtherscanClient import EtherscanClient
import telegram
from telegram import Bot
from datetime import datetime, timedelta
from texttable import Texttable
import time
import json


class Contract:
    def __init__(self, address: str, name: str):
        self.address = address
        self.name = name


def get_transactions_since_ts(address: str, ts: int = 0, limit=20) -> list:
    """
    Gets all transactions for specified address since timestamp specified as ts and returns them in descending order
    :param address: Address
    :param ts: Start timestamp
    :param limit: max amount of transactions returned

    :return: list of dictionaries
    """
    eth_api = EtherscanClient()
    transactions = eth_api.get_transactions_by_address(address, sort='desc', limit=limit)
    last_transaction_index = 0
    for transaction in transactions:
        if int(transaction['timeStamp']) <= ts:
            break
        last_transaction_index += 1
    else:
        print('more data')
    return transactions[:last_transaction_index]


def send_tg_data(data: str):
    tg_bot = Bot(token='2135710412:AAFgSYnf9Zif1oGFObFY3Q-H45I96jbgsyA')
    tg_bot.sendMessage(chat_id='@contract_alerts', text=data, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)


def alert_contract_transactions_since_ts(contract: Contract, ts: int = 0) -> int:
    """
    Function gets latest transactions of a contract since timestamp specified as ts and
    sends message about those transactions to the telegram channel.
    :param contract: contract we want to keep track of
    :param ts: start timestamp
    :return: timestamp of last transaction we could get for specified contract
    """
    transactions = list(reversed(get_transactions_since_ts(contract.address, ts)))
    if not transactions:
        print(f'No new data ')
        return False
    columns = ['datetime', 'hash']
    data = []
    for transaction in transactions:
        transaction['datetime'] = datetime.fromtimestamp(int(transaction['timeStamp'])).strftime('%d\.%m\.%Y %H:%M')
        transaction['hash'] = f'[{transaction["hash"][:5]}\.\.{transaction["hash"][-3:]}]' \
                              f'(https://etherscan.io/tx/{transaction["hash"]})'
        data.append([transaction[column] for column in columns])
    table = Texttable()
    table.set_deco(Texttable.HEADER)
    table.set_max_width(max_width=0)
    table.add_rows(data, header=False)
    columns_str = '{:<26}{:<14}'.format(*columns)
    message_str = f'*{contract.name}*\n' \
                  f'{columns_str}\n' \
                  f'{table.draw()}'
    print(message_str)
    send_tg_data(data=message_str)
    return int(transactions[-1]['timeStamp'])


def save_last_ts(last_ts_data: dict):
    """
    Save dictionary with information about last transactions timestamp to a file
    :param last_ts_data:
    :return:
    """
    with open('last_ts.json', 'w') as fp:
        json.dump(last_ts_data, fp)


def initialize_last_ts_data() -> dict:
    """
    Initializes last timestamps for contracts from a saved file
    :return: dictionary with contract address as key and
    last timestamp of transaction we got from this contract as value
    """
    try:
        with open('last_ts.json', 'r') as fp:
            return json.load(fp)
    except FileNotFoundError:
        return {}


def alert_transactions_for_contracts(contracts_list: list, refresh_rate_sec: int = 60):
    """
    Alert new transactions for specified contracts to the telegram channel
    :param contracts_list: list of contracts to keep track of
    :param refresh_rate_sec: Refresh rate in seconds
    :return:
    """
    last_ts_dict = initialize_last_ts_data()
    while True:
        for contract in contracts_list:
            if contract.address in last_ts_dict:
                last_transaction_ts = last_ts_dict[contract.address]
            else:
                last_transaction_ts = int((datetime.now() - timedelta(days=10)).timestamp())

            tx_ts = alert_contract_transactions_since_ts(contract=contract, ts=last_transaction_ts)
            last_transaction_ts = tx_ts if tx_ts else last_transaction_ts
            last_ts_dict[contract.address] = last_transaction_ts
            save_last_ts(last_ts_dict)

        time.sleep(refresh_rate_sec)


if __name__ == '__main__':
    wild_credit_deployer = Contract(address='0xd7b3b50977a5947774bFC46B760c0871e4018e97', name='Wild Credit Deployer')
    uniswap_token = Contract(address='0x1f9840a85d5af5bf1d1762f925bdaddc4201f984', name='Uniswap Token')
    deployer_contracts = [wild_credit_deployer, uniswap_token]
    alert_transactions_for_contracts(deployer_contracts)
