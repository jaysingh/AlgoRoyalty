import base64
import json

from algosdk.v2client import algod, indexer
from algosdk import mnemonic, account, logic
from algosdk.future.transaction import AssetConfigTxn, ApplicationCreateTxn, OnComplete, LogicSig
from pyteal import compileTeal, Mode
import hashlib
from algosdk.encoding import decode_address, encode_address

import smart_contracts
from royalties import get_royalty_from_json, CHAIN, get_chain_from_json


def get_indexer_client():
    indexer_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    indexer_address = "http://localhost:8980"
    indexer_client = indexer.IndexerClient(indexer_token, indexer_address)
    return indexer_client

def get_algod_client():
    algod_token = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    algod_address = "http://localhost:4001"
    algod_client = algod.AlgodClient(algod_token, algod_address)
    return algod_client

def wait_for_confirmation(client, transaction_id, timeout):
  start_round = client.status()["last-round"] + 1
  current_round = start_round

  while current_round < start_round + timeout:
      try:
          pending_txn = client.pending_transaction_info(transaction_id)
      except Exception:
          return
      if pending_txn.get("confirmed-round", 0) > 0:
          return pending_txn
      elif pending_txn["pool-error"]:
          raise Exception(
              'pool error: {}'.format(pending_txn["pool-error"]))
      client.status_after_block(current_round)
      current_round += 1
  raise Exception(
      'pending tx not found in timeout rounds, timeout value = : {}'.format(timeout))

def get_private_key_from_mnemonic(mn):
    private_key = mnemonic.to_private_key(mn)
    return private_key

def create_non_fungible_token(public_key, signin_key, nft_metadata):
    algod_client = get_algod_client()
    params = algod_client.suggested_params()

    metadataStr = json.dumps(nft_metadata)

    hash = hashlib.new("sha512_256")
    hash.update(b"arc0003/amj")
    hash.update(metadataStr.encode("utf-8"))
    json_metadata_hash = hash.digest()

    txn = AssetConfigTxn(
        sender=public_key,
        sp=params,
        total=1,
        default_frozen=False,
        unit_name=nft_metadata['unit_name'],
        asset_name=nft_metadata['name'],
        manager=public_key,
        reserve=public_key,
        freeze=public_key,
        clawback=public_key,
        strict_empty_address_check=False,
        url=nft_metadata['url'],
        metadata_hash=json_metadata_hash,
        decimals=0)

    stxn = txn.sign(signin_key)
    txid = algod_client.send_transaction(stxn)
    wait_for_confirmation(algod_client, txid, 4)
    ptx = algod_client.pending_transaction_info(txid)
    return ptx["asset-index"], txid

def create_application(passphrase, asset_id):
    signin_key = get_private_key_from_mnemonic(passphrase)
    public_key = account.address_from_private_key(signin_key)

    approval_program_compiled = compileTeal(smart_contracts.approval_program(),
                                            mode=Mode.Application,
                                            version=5)

    clear_program_compiled = compileTeal(smart_contracts.clear_program(),
                                         mode=Mode.Application,
                                         version=5)

    algod_client = get_algod_client()

    approval_program = smart_contracts.compile_teal_program(algod_client, approval_program_compiled)
    clear_program = smart_contracts.compile_teal_program(algod_client, clear_program_compiled)

    app_args = [
        decode_address(public_key),
        public_key
    ]

    params = algod_client.suggested_params()

    txn = ApplicationCreateTxn(sender=public_key,
                               sp=params,
                               on_complete=OnComplete.NoOpOC.real,
                               approval_program=approval_program,
                               clear_program=clear_program,
                               global_schema=smart_contracts.global_schema(),
                               local_schema=smart_contracts.local_schema(),
                               app_args=app_args,
                               foreign_assets=[asset_id])

    stxn = txn.sign(signin_key)
    txid = algod_client.send_transaction(stxn)
    wait_for_confirmation(algod_client, txid, 4)
    transaction_response = algod_client.pending_transaction_info(txid)
    app_id = transaction_response['application-index']
    return app_id

def get_string_value_from_global_state(application, key):
    encoded_key = base64.b64encode(bytes(key, "utf-8")).decode("utf-8")
    for state in application['params']['global-state']:
        if state['key'] == encoded_key:
            if state['value']['type'] == 1:
                return base64.b64decode(state['value']['bytes']).decode("utf-8")
            return str(state['value']['uint'])
    return ""

def get_assets_from_applications(applications):
    assets = []
    for application in applications:
        asset = {
            'app_id': application['id'],
            'state': get_string_value_from_global_state(application, "state"),
            'asset_id': get_string_value_from_global_state(application, "asset_id"),
            'price': get_string_value_from_global_state(application, "price"),
            'owner_str': get_string_value_from_global_state(application, "owner_str"),
            'creator_str': get_string_value_from_global_state(application, "creator_str"),
        }
        rc = get_string_value_from_global_state(application, "rc")
        rs = get_string_value_from_global_state(application, "rs")
        if rc and rs:
            royalty_groups = []
            chain_groups = []
            for index in range(int(rc)):
                if int(rs) == CHAIN:
                    royalty = get_string_value_from_global_state(application, "c" + str(index))
                    chain_groups.append(get_chain_from_json(royalty))
                else:
                    royalty = get_string_value_from_global_state(application, "r" + str(index))
                    royalty_groups.append(get_royalty_from_json(royalty))
            asset['royalty'] = {
                'state': int(rs),
                'royalty_groups': royalty_groups,
                'chain_groups': chain_groups
            }
        result = get_algod_client().asset_info(asset_id=int(asset['asset_id']))
        asset['assetinfo'] = result
        assets.append(asset)
    return assets

def _get_escrow_program(asset_id, application_id):
    escrow_program_compiled = compileTeal(smart_contracts.escrow_address_program(asset_id, application_id),
                                          mode=Mode.Signature,
                                          version=5)
    algod_client = get_algod_client()

    escrow_program = smart_contracts.compile_teal_program(algod_client, escrow_program_compiled)
    return escrow_program

def get_escrow_address(asset_id, application_id):
    escrow_fund_address = logic.address(_get_escrow_program(asset_id, application_id))
    return escrow_fund_address

def get_escrow_signature(asset_id, application_id):
    asa_transfer_txn_logic_signature = LogicSig(_get_escrow_program(asset_id, application_id))
    return asa_transfer_txn_logic_signature