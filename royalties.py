import json
from types import SimpleNamespace
from algosdk.future.transaction import PaymentTxn

NO_ROYALTY = 0
CREATOR_ONLY = 1
GROUP = 2
CHAIN = 3

def get_new_royalty_structure_arguments(owner, state, royalty_groups, chain_groups):
    if state == CHAIN:
        args = [state, len(chain_groups)]
        fill = False
        for index, group in enumerate(chain_groups):
            structure = {
                "level": group['level'],
                "address": group['address'],
                "royalty": group['royalty']
            }
            if not fill and not structure['address']:
                structure['address'] = owner
                fill = True
            args.append("c" + str(index))
            args.append(json.dumps(structure))
        return args
    args = [state, len(royalty_groups)]
    if state == CREATOR_ONLY or state == GROUP:
        for index, group in enumerate(royalty_groups):
            structure = {
                "address": group['address'],
                "royalty": group['royalty']
            }
            args.append("r" + str(index))
            args.append(json.dumps(structure))
    return args

def get_chain_from_json(chain_string):
    structure = json.loads(chain_string, object_hook=lambda d: SimpleNamespace(**d))
    return {
        "level": structure.level,
        "address": structure.address,
        "royalty": int(structure.royalty)
    }

def get_royalty_from_json(royalty_string):
    structure = json.loads(royalty_string, object_hook=lambda d: SimpleNamespace(**d))
    return {
        "address": structure.address,
        "royalty": int(structure.royalty)
    }

def get_royalty_transactions(current_state, sender, owner, price, suggested_params):
    royalty_txns = []
    total_royalty = 0
    royalty_groups = []
    if current_state['state'] == CREATOR_ONLY or current_state['state'] == GROUP:
        royalty_groups = current_state['royalty_groups']
    if current_state['state'] == CHAIN:
        royalty_groups = []
        for group in current_state['chain_groups']:
            if group['address']:
                royalty_groups.append(group)
    for r in royalty_groups:
        royalty = int(price) * int(r['royalty']) / 100
        txn = PaymentTxn(sender=sender,
                   sp=suggested_params,
                   receiver=r['address'],
                   amt=int(royalty))
        total_royalty += royalty
        royalty_txns.append(txn)
    txn2 = PaymentTxn(sender=sender,
                      sp=suggested_params,
                      receiver=owner,
                      amt=int(price) - int(total_royalty))
    txns = []
    txns.append(txn2)
    txns = txns + royalty_txns
    return txns